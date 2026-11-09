import pytest
import sqlite3
import threading
import time
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

from jobs import proccess_job, process_jobs, handle_job_failure, increment_retry_count
from errors import PermanentError, TransientError, MAX_RETRY_ATTEMPTS


class TestProcessJob:
    """Test suite for proccess_job function"""

    @patch('jobs.image_to_text')
    def test_process_job_success_with_test_model(self, mock_image_to_text):
        """Test successful job processing with mocked image_to_text"""
        # Setup
        mock_image_to_text.return_value = "A funny meme with text"

        input_job_details = {
            "image_core_id": 42,
            "image_path": "/app/public/memes/test.jpg",
            "model": "test"
        }

        # Execute
        result = proccess_job(input_job_details)

        # Assert
        assert result == {
            "image_core_id": 42,
            "description": "A funny meme with text"
        }
        mock_image_to_text.assert_called_once_with("/app/public/memes/test.jpg", "test")

    @patch('jobs.image_to_text')
    def test_process_job_returns_correct_output_format(self, mock_image_to_text):
        """Test that process_job returns correctly formatted output"""
        # Setup
        mock_image_to_text.return_value = "Description text"

        input_job_details = {
            "image_core_id": 123,
            "image_path": "/path/to/image.jpg",
            "model": "test"
        }

        # Execute
        result = proccess_job(input_job_details)

        # Assert
        assert "image_core_id" in result
        assert "description" in result
        assert result["image_core_id"] == 123
        assert isinstance(result["description"], str)

    @patch('jobs.image_to_text')
    def test_process_job_raises_on_image_to_text_failure(self, mock_image_to_text):
        """Test that exceptions from image_to_text are propagated"""
        # Setup
        mock_image_to_text.side_effect = Exception("Model inference failed")

        input_job_details = {
            "image_core_id": 42,
            "image_path": "/app/public/memes/test.jpg",
            "model": "test"
        }

        # Execute & Assert
        with pytest.raises(Exception, match="Model inference failed"):
            proccess_job(input_job_details)


class TestProcessJobs:
    """Test suite for process_jobs worker function"""

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_processes_single_job(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker processes a single job and exits loop"""
        # Setup mock database with one job, then empty
        mock_conn = Mock()
        mock_cursor = Mock()

        # First call returns a job (with retry_count=0), second and third calls return None (empty queue)
        mock_cursor.fetchone.side_effect = [
            (1, 42, "test.jpg", "test", 0),  # First iteration: job found (id, image_core_id, path, model, retry_count)
            None,  # Second iteration: no job
            None   # Third iteration: error recovery loop
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock proccess_job output
        mock_proccess_job.return_value = {
            "image_core_id": 42,
            "description": "Test description"
        }

        # Make sleep raise exception to break infinite loop after second iteration
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert
        assert mock_cursor.fetchone.call_count == 3  # First: job, Second & Third: empty queue
        mock_proccess_job.assert_called_once()
        mock_desc_sender.assert_called_once_with(
            {"image_core_id": 42, "description": "Test description"},
            "http://localhost:3000/"
        )
        # Verify status sent twice: in_queue (status=2) and done (status=3)
        assert mock_status_sender.call_count == 2
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (1,))
        mock_conn.commit.assert_called()

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_processes_multiple_jobs_sequential(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker processes multiple jobs in FIFO order"""
        # Setup mock database with two jobs, then empty
        mock_conn = Mock()
        mock_cursor = Mock()

        # Three calls: two jobs, then empty (with retry_count=0)
        mock_cursor.fetchone.side_effect = [
            (1, 10, "image1.jpg", "test", 0),
            (2, 20, "image2.jpg", "test", 0),
            None  # Empty queue
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Mock proccess_job to return different descriptions
        mock_proccess_job.side_effect = [
            {"image_core_id": 10, "description": "First image"},
            {"image_core_id": 20, "description": "Second image"}
        ]

        # Break loop after processing
        mock_sleep.side_effect = [None, None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert
        assert mock_proccess_job.call_count == 2
        assert mock_desc_sender.call_count == 2
        # Verify DELETE called for both jobs
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (1,))
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (2,))

    @patch('jobs.release_idle_model')
    @patch('jobs.sqlite3.connect')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_releases_idle_model_when_queue_is_empty(self, mock_sleep, mock_connect, mock_release_idle_model):
        """Test the idle wake-up gives the cached model a chance to be released"""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        mock_sleep.side_effect = [KeyboardInterrupt()]

        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        mock_release_idle_model.assert_called_once_with()

    @patch('jobs.sqlite3.connect')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_handles_empty_queue(self, mock_sleep, mock_connect):
        """Test worker sleeps and continues when queue is empty"""
        # Setup mock database with no jobs
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Break loop after first sleep
        mock_sleep.side_effect = [KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert
        mock_cursor.fetchone.assert_called_once()
        mock_sleep.assert_called_once_with(5)
        # Connection should be closed
        mock_conn.close.assert_called()

    @patch('jobs.sqlite3.connect')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_handles_database_connection_failure(
        self, mock_sleep, mock_connect
    ):
        """Test worker handles database connection failures gracefully"""
        # Setup mock to raise exception on connect
        mock_connect.side_effect = [
            sqlite3.OperationalError("database is locked"),
            KeyboardInterrupt()  # Exit on second iteration
        ]

        mock_sleep.side_effect = [None]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - worker should sleep and continue after error
        mock_sleep.assert_called_with(5)
        assert mock_connect.call_count == 2

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_sends_status_processing(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker sends status updates when processing jobs"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [(1, 42, "test.jpg", "test", 0), None, None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Test"}
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Capture status values at call time (avoid dictionary mutation issues)
        captured_statuses = []
        def capture_status(status_dict, url):
            captured_statuses.append(status_dict["status"])
        mock_status_sender.side_effect = capture_status

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - status_sender should be called twice (processing=2, then done=3)
        assert mock_status_sender.call_count == 2
        # Check that both status values were sent (captured at call time)
        assert captured_statuses == [2, 3], f"Expected statuses [2, 3] (processing → done), got {captured_statuses}"

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_sends_status_done(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker sends status=3 (done) when job completes"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [(1, 42, "test.jpg", "test", 0), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Test"}
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - second status call should be status=3 (done)
        second_call = mock_status_sender.call_args_list[1]
        assert second_call[0][0]["status"] == 3

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_calls_description_sender(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker calls description_sender with job output"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [(1, 42, "test.jpg", "test", 0), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        expected_output = {"image_core_id": 42, "description": "Funny cat meme"}
        mock_proccess_job.return_value = expected_output
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert
        mock_desc_sender.assert_called_once_with(
            expected_output,
            "http://localhost:3000/"
        )

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_jobs_worker_deletes_job_after_processing(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker deletes job from queue after successful processing"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        job_id = 99
        mock_cursor.fetchone.side_effect = [(job_id, 42, "test.jpg", "test", 0), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Test"}
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (job_id,))
        mock_conn.commit.assert_called()

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    @patch('jobs.logging')
    def test_process_jobs_worker_continues_after_exception(
        self, mock_logging, mock_sleep, mock_status_sender,
        mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test worker continues processing after an exception"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()

        # First job raises exception, second job succeeds, then empty (with retry_count)
        mock_cursor.fetchone.side_effect = [
            (1, 10, "bad.jpg", "test", 0),      # First job (will fail)
            (1,),                               # retry_count query returns 1
            (2, 20, "good.jpg", "test", 0),     # Second job (succeeds)
            None                                # Empty queue
        ]

        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # First call raises exception, second succeeds
        mock_proccess_job.side_effect = [
            Exception("Image processing failed"),
            {"image_core_id": 20, "description": "Success"}
        ]

        mock_sleep.side_effect = [None, None, None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - worker should log error and continue
        mock_logging.error.assert_called()
        # Second job should still be processed
        assert mock_proccess_job.call_count == 2

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_job_handles_image_path_production_mode(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test path transformation for production environment"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [(1, 42, "memes/test.jpg", "test", 0), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Test"}
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute with production database path (no "tests" in path)
        try:
            process_jobs("/app/jobs.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - image_path should be prefixed with /app/public/memes/
        call_args = mock_proccess_job.call_args[0][0]
        assert call_args["image_path"] == "/app/public/memes/memes/test.jpg"

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_process_job_handles_image_path_test_mode(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test path transformation for test environment"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [(1, 42, "/full/path/test.jpg", "test", 0), None]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Test"}
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute with test database path ("tests" in path)
        try:
            process_jobs("/tests/test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - image_path should NOT be prefixed (use as-is)
        call_args = mock_proccess_job.call_args[0][0]
        assert call_args["image_path"] == "/full/path/test.jpg"


class TestErrorHandling:
    """Test suite for error handling and retry logic"""

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.failure_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_permanent_error_removes_job_immediately(
        self, mock_sleep, mock_status_sender, mock_failure_sender, mock_proccess_job, mock_connect
    ):
        """Test that PermanentError removes job immediately without retrying"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (1, 42, "missing.jpg", "test", 0),  # Job with retry_count=0
            None  # Empty queue after
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Process job raises PermanentError
        mock_proccess_job.side_effect = PermanentError("Image file not found: missing.jpg")
        mock_sleep.side_effect = [KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - failure_sender should be called with status=5 and error message
        mock_failure_sender.assert_called_once_with(42, "Image file not found: missing.jpg", "http://localhost:3000/")
        # Job should be deleted immediately
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (1,))

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.failure_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_transient_error_increments_retry_count(
        self, mock_sleep, mock_status_sender, mock_failure_sender, mock_proccess_job, mock_connect
    ):
        """Test that TransientError increments retry count and schedules retry"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (1, 42, "test.jpg", "test", 0),  # Job with retry_count=0
            (1,),  # retry_count query returns 1 after increment
            None  # Break loop
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Process job raises TransientError
        mock_proccess_job.side_effect = [TransientError("Model download failed"), KeyboardInterrupt()]
        mock_sleep.side_effect = [None, KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - retry count should be incremented
        mock_cursor.execute.assert_any_call("UPDATE jobs SET retry_count = retry_count + 1 WHERE id = ?", (1,))
        # failure_sender should NOT be called yet (still has retries left)
        mock_failure_sender.assert_not_called()

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.failure_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_max_retries_exceeded_triggers_failure(
        self, mock_sleep, mock_status_sender, mock_failure_sender, mock_proccess_job, mock_connect
    ):
        """Test that exceeding max retries sends failure notification"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (1, 42, "test.jpg", "test", 2),  # Job already at retry_count=2 (one more = max)
            (3,),  # retry_count query returns 3 after increment (>= MAX_RETRY_ATTEMPTS)
            None  # Empty queue
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # Process job raises TransientError
        mock_proccess_job.side_effect = TransientError("Model download failed")
        mock_sleep.side_effect = [KeyboardInterrupt()]

        # Execute
        try:
            process_jobs("test.db", "http://localhost:3000/")
        except KeyboardInterrupt:
            pass

        # Assert - failure_sender should be called because max retries exceeded
        assert mock_failure_sender.called
        # Job should be deleted
        mock_cursor.execute.assert_any_call("DELETE FROM jobs WHERE id = ?", (1,))

    @patch('jobs.sqlite3.connect')
    @patch('jobs.proccess_job')
    @patch('jobs.description_sender')
    @patch('jobs.status_sender')
    @patch('jobs.time.sleep')
    def test_successful_job_does_not_trigger_failure(
        self, mock_sleep, mock_status_sender, mock_desc_sender, mock_proccess_job, mock_connect
    ):
        """Test that successful job processing does not send failure notification"""
        # Setup
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.side_effect = [
            (1, 42, "test.jpg", "test", 0),
            None
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        mock_proccess_job.return_value = {"image_core_id": 42, "description": "Success!"}
        mock_sleep.side_effect = [KeyboardInterrupt()]

        # Execute
        with patch('jobs.failure_sender') as mock_failure_sender:
            try:
                process_jobs("test.db", "http://localhost:3000/")
            except KeyboardInterrupt:
                pass

            # Assert - failure_sender should NOT be called
            mock_failure_sender.assert_not_called()
            # description_sender should be called with success
            mock_desc_sender.assert_called_once()
            # status=3 (done) should be sent
            assert any(call[0][0]["status"] == 3 for call in mock_status_sender.call_args_list)


class TestHelperFunctions:
    """Test suite for helper functions"""

    def test_handle_job_failure_sends_notification_and_deletes(self):
        """Test handle_job_failure sends failure notification and removes job"""
        mock_cursor = Mock()
        mock_conn = Mock()

        with patch('jobs.failure_sender') as mock_failure_sender:
            handle_job_failure(mock_cursor, mock_conn, 1, 42, "Test error", "http://localhost:3000/")

            # Assert
            mock_failure_sender.assert_called_once_with(42, "Test error", "http://localhost:3000/")
            mock_cursor.execute.assert_called_with("DELETE FROM jobs WHERE id = ?", (1,))
            mock_conn.commit.assert_called_once()

    def test_increment_retry_count_updates_and_returns_new_count(self):
        """Test increment_retry_count updates database and returns new count"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_cursor.fetchone.return_value = (3,)  # New retry count

        result = increment_retry_count(mock_cursor, mock_conn, 1)

        # Assert
        assert result == 3
        mock_cursor.execute.assert_any_call("UPDATE jobs SET retry_count = retry_count + 1 WHERE id = ?", (1,))
        mock_cursor.execute.assert_any_call("SELECT retry_count FROM jobs WHERE id = ?", (1,))
        mock_conn.commit.assert_called_once()
