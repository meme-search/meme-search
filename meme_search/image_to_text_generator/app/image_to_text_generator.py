from log_config import logging
import gc
import os
import threading
import time
import torch
from model_init import model_selector
from errors import PermanentError, TransientError, MAX_IMAGE_SIZE_BYTES
from PIL import Image, UnidentifiedImageError


def validate_image(image_path: str) -> None:
    """Validate image file exists, is not too large, and is a valid image.

    Raises:
        PermanentError: If file doesn't exist, is too large, or is corrupt/invalid.
    """
    # Check file exists
    if not os.path.exists(image_path):
        raise PermanentError(f"Image file not found: {image_path}")

    # Check file size
    file_size = os.path.getsize(image_path)
    if file_size > MAX_IMAGE_SIZE_BYTES:
        size_mb = file_size / (1024 * 1024)
        max_mb = MAX_IMAGE_SIZE_BYTES / (1024 * 1024)
        raise PermanentError(f"Image file too large: {size_mb:.1f}MB exceeds {max_mb:.0f}MB limit")

    # Check file is a valid image
    try:
        with Image.open(image_path) as img:
            img.verify()  # Verify it's a valid image without loading full data
    except UnidentifiedImageError:
        raise PermanentError(f"Invalid or corrupt image file: {image_path}")
    except Exception as e:
        raise PermanentError(f"Cannot read image file: {image_path} - {e}")


DEFAULT_MODEL_IDLE_TIMEOUT = 300


def parse_idle_timeout(raw_value) -> int:
    """Parse MODEL_IDLE_TIMEOUT in seconds; 0 (or negative) keeps the model loaded."""
    if raw_value is None or raw_value.strip() == "":
        return DEFAULT_MODEL_IDLE_TIMEOUT
    try:
        return max(0, int(raw_value))
    except ValueError:
        logging.warning(f"WARNING: invalid MODEL_IDLE_TIMEOUT {raw_value!r}, using {DEFAULT_MODEL_IDLE_TIMEOUT}s")
        return DEFAULT_MODEL_IDLE_TIMEOUT


MODEL_IDLE_TIMEOUT = parse_idle_timeout(os.environ.get("MODEL_IDLE_TIMEOUT"))

# Loading weights takes seconds and gigabytes, so one model stays loaded across jobs.
_model_lock = threading.Lock()
_cached_model = None
_cached_model_name = None
_last_used = 0.0


def _release_cached_model_locked() -> None:
    global _cached_model, _cached_model_name
    if _cached_model is None:
        return
    logging.info(f"INFO: releasing model {_cached_model_name}")
    _cached_model = None
    _cached_model_name = None
    # Tensors are freed by the collector; only then can CUDA return its cached blocks.
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def _get_model_locked(model_name: str):
    global _cached_model, _cached_model_name
    if _cached_model is not None and _cached_model_name == model_name:
        return _cached_model
    # Release first so the old and the new model never sit in memory together.
    _release_cached_model_locked()
    current_model = download_model(model_name)
    _cached_model = current_model
    _cached_model_name = model_name
    return current_model


def release_model() -> None:
    """Release the cached model, if any."""
    with _model_lock:
        _release_cached_model_locked()


def release_idle_model(now=None) -> bool:
    """Release the cached model when it was last used more than MODEL_IDLE_TIMEOUT seconds ago.

    Returns True when a model was released.
    """
    with _model_lock:
        if MODEL_IDLE_TIMEOUT <= 0 or _cached_model is None:
            return False
        if now is None:
            now = time.monotonic()
        if now - _last_used <= MODEL_IDLE_TIMEOUT:
            return False
        logging.info(f"INFO: model idle for more than {MODEL_IDLE_TIMEOUT}s")
        _release_cached_model_locked()
        return True


def download_model(model_name: str):
    try:
        current_model = model_selector(model_name)
        current_model.download()
        return current_model
    except Exception as e:
        error_msg = f"ERROR: download_model failed with error: {e}"
        logging.error(error_msg)
        # Model download failures are transient (network issues, HuggingFace outages)
        raise TransientError(f"Model download failed: {e}")


def image_to_text(image_path: str, model_name: str) -> str:
    """Extract text description from an image using the specified model.

    Raises:
        PermanentError: If image is invalid, missing, or too large.
        TransientError: If model download fails or temporary processing error.
    """
    # Validate image before processing (raises PermanentError if invalid)
    validate_image(image_path)

    global _last_used
    try:
        # The lock is held through inference so an idle release or a model switch cannot run mid-extraction.
        with _model_lock:
            try:
                current_model = _get_model_locked(model_name)

                # if model is 'test' pause for 5 seconds to allow testing
                if model_name == "test":
                    time.sleep(5)

                # process
                description = current_model.extract(image_path)
            finally:
                _last_used = time.monotonic()
        logging.info(f"INFO: the description of image {image_path} is: {description}")
        return description
    except (PermanentError, TransientError):
        # Re-raise our custom errors as-is
        raise
    except MemoryError as e:
        # OOM during inference - transient, may succeed on retry with less load
        error_msg = f"ERROR: image_to_text OOM for image {image_path}: {e}"
        logging.error(error_msg)
        raise TransientError(f"Out of memory processing image: {e}")
    except Exception as e:
        # Unexpected errors - treat as transient to allow retry
        error_msg = f"ERROR: image_to_text extraction of image {image_path} failed with error: {e}"
        logging.error(error_msg)
        raise TransientError(f"Image processing failed: {e}")
