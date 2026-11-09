import time
import sqlite3
import threading
from log_config import logging
from image_to_text_generator import image_to_text, release_idle_model
from senders import description_sender, status_sender, failure_sender
from errors import PermanentError, TransientError, MAX_RETRY_ATTEMPTS, RETRY_DELAYS

# lock
lock = threading.Lock()


def proccess_job(input_job_details: dict) -> dict:
    """Process a single job and return results.

    Raises:
        PermanentError: If image is invalid and should not be retried.
        TransientError: If processing failed but may succeed on retry.
    """
    # process image (may raise PermanentError or TransientError)
    description = image_to_text(input_job_details["image_path"], input_job_details["model"])

    # create return payload
    output_job_details = {
        "image_core_id": input_job_details["image_core_id"],
        "description": description,
    }
    return output_job_details


def handle_job_failure(cursor, conn, job_id: int, image_core_id: int, error_message: str, APP_URL: str) -> None:
    """Handle permanent job failure: notify Rails and remove from queue."""
    logging.error(f"Job {job_id} permanently failed: {error_message}")

    # Notify Rails of failure (status=5 + error message)
    failure_sender(image_core_id, error_message, APP_URL)

    # Remove failed job from queue
    cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    logging.info(f"Removed failed job {job_id} from queue")


def increment_retry_count(cursor, conn, job_id: int) -> int:
    """Increment retry count for a job and return new count."""
    cursor.execute("UPDATE jobs SET retry_count = retry_count + 1 WHERE id = ?", (job_id,))
    conn.commit()
    cursor.execute("SELECT retry_count FROM jobs WHERE id = ?", (job_id,))
    result = cursor.fetchone()
    return result[0] if result else 0


def process_jobs(JOB_DB, APP_URL):
    logging.info("Worker thread started - ready to process jobs")
    while True:
        conn = None
        job = None
        sleep_time = 5  # Default sleep time when no jobs

        try:
            with lock:
                conn = sqlite3.connect(JOB_DB)
                cursor = conn.cursor()

                # Fetch job with retry_count
                cursor.execute("SELECT id, image_core_id, image_path, model, retry_count FROM jobs ORDER BY id LIMIT 1")
                job = cursor.fetchone()

                if job:
                    # unpack job (now includes retry_count)
                    job_id, image_core_id, image_path, model, retry_count = job

                    # pack up data for processing / status update
                    input_job_details = {
                        "image_core_id": image_core_id,
                        "image_path": "/app/public/memes/" + image_path if "tests" not in JOB_DB else image_path,
                        "model": model,
                    }
                    status_job_details = {"image_core_id": image_core_id, "status": 2}

                    # send status update (image out of queue and in process)
                    status_sender(status_job_details, APP_URL)

                    # report that processing has begun
                    logging.info("Processing job: %s (retry_count=%d)", input_job_details, retry_count)

                    try:
                        # process job
                        output_job_details = proccess_job(input_job_details)

                        # send results to main app
                        description_sender(output_job_details, APP_URL)

                        # send status update (image processing complete)
                        status_job_details["status"] = 3
                        status_sender(status_job_details, APP_URL)

                        # log completion
                        logging.info("Finished processing job: %s", input_job_details)

                        # Remove the processed job from the queue
                        cursor.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                        conn.commit()

                    except PermanentError as e:
                        # Permanent failure - don't retry, notify Rails immediately
                        handle_job_failure(cursor, conn, job_id, image_core_id, str(e), APP_URL)

                    except TransientError as e:
                        # Transient failure - may retry
                        new_retry_count = increment_retry_count(cursor, conn, job_id)

                        if new_retry_count >= MAX_RETRY_ATTEMPTS:
                            # Max retries exceeded - treat as permanent failure
                            error_msg = f"Max retries ({MAX_RETRY_ATTEMPTS}) exceeded. Last error: {e}"
                            handle_job_failure(cursor, conn, job_id, image_core_id, error_msg, APP_URL)
                        else:
                            # Will retry - calculate backoff delay
                            delay_index = min(new_retry_count - 1, len(RETRY_DELAYS) - 1)
                            sleep_time = RETRY_DELAYS[delay_index]
                            logging.warning(
                                f"Job {job_id} failed (attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS}), "
                                f"will retry in {sleep_time}s: {e}"
                            )

                    except Exception as e:
                        # Unexpected error - treat as transient
                        new_retry_count = increment_retry_count(cursor, conn, job_id)

                        if new_retry_count >= MAX_RETRY_ATTEMPTS:
                            error_msg = f"Max retries ({MAX_RETRY_ATTEMPTS}) exceeded. Last error: {e}"
                            handle_job_failure(cursor, conn, job_id, image_core_id, error_msg, APP_URL)
                        else:
                            delay_index = min(new_retry_count - 1, len(RETRY_DELAYS) - 1)
                            sleep_time = RETRY_DELAYS[delay_index]
                            logging.warning(
                                f"Job {job_id} unexpected error (attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS}), "
                                f"will retry in {sleep_time}s: {e}"
                            )

                else:
                    # If there are no jobs, wait for a while before checking again
                    logging.info("No jobs in queue. Waiting...")
                    release_idle_model()

                # Always close connection before sleep/continue
                if conn:
                    conn.close()
                    conn = None

            # Sleep outside the lock
            if not job or sleep_time > 5:
                time.sleep(sleep_time)

        except Exception as e:
            logging.error(f"Worker thread error: {e}", exc_info=True)
            # Close connection on error
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            # Sleep before retrying
            time.sleep(5)
