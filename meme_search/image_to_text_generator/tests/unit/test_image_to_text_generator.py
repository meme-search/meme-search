import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "app"))

import weakref
import image_to_text_generator
from image_to_text_generator import (
    download_model,
    image_to_text,
    validate_image,
    release_model,
    release_idle_model,
    parse_idle_timeout,
)
from model_init import TestImageToText as DummyModel
from errors import PermanentError, TransientError, MAX_IMAGE_SIZE_BYTES


@pytest.fixture(autouse=True)
def reset_model_cache():
    # The loaded model is cached at module level, so every test starts and ends without one.
    release_model()
    yield
    release_model()


class TestDownloadModel:
    """Test suite for download_model function"""

    @patch('image_to_text_generator.model_selector')
    def test_download_model_success_test_model(self, mock_model_selector):
        """Test successful model download for test model"""
        # Setup
        mock_model = MagicMock()
        mock_model.download.return_value = None
        mock_model_selector.return_value = mock_model

        # Execute
        result = download_model("test")

        # Assert
        assert result == mock_model
        mock_model_selector.assert_called_once_with("test")
        mock_model.download.assert_called_once()

    @patch('image_to_text_generator.model_selector')
    def test_download_model_success_florence_2_base(self, mock_model_selector):
        """Test successful model download for Florence-2-base"""
        # Setup
        mock_model = MagicMock()
        mock_model.download.return_value = None
        mock_model_selector.return_value = mock_model

        # Execute
        result = download_model("Florence-2-base")

        # Assert
        assert result == mock_model
        mock_model_selector.assert_called_once_with("Florence-2-base")
        mock_model.download.assert_called_once()

    @patch('image_to_text_generator.model_selector')
    def test_download_model_invalid_model_raises_transient_error(self, mock_model_selector):
        """Test download_model raises TransientError for invalid model"""
        # Setup - model_selector raises ValueError, but download_model wraps all exceptions
        mock_model_selector.side_effect = ValueError("model_name invalid-model not found")

        # Execute & Assert - all exceptions are wrapped in TransientError
        with pytest.raises(TransientError, match="Model download failed"):
            download_model("invalid-model")

    @patch('image_to_text_generator.model_selector')
    def test_download_model_download_failure_raises_transient_error(self, mock_model_selector):
        """Test download_model raises TransientError when download fails"""
        # Setup
        mock_model = MagicMock()
        mock_model.download.side_effect = Exception("Download failed")
        mock_model_selector.return_value = mock_model

        # Execute & Assert
        with pytest.raises(TransientError, match="Model download failed"):
            download_model("test")


class TestImageToText:
    """Test suite for image_to_text function"""

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_success_with_test_model(self, mock_download_model, mock_sleep, mock_validate):
        """Test successful image to text extraction with test model"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "This is a test description"
        mock_download_model.return_value = mock_model

        # Execute
        result = image_to_text("/path/to/image.jpg", "test")

        # Assert
        assert result == "This is a test description"
        mock_validate.assert_called_once_with("/path/to/image.jpg")
        mock_download_model.assert_called_once_with("test")
        mock_model.extract.assert_called_once_with("/path/to/image.jpg")
        # Verify test model sleeps for 5 seconds
        mock_sleep.assert_called_once_with(5)

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_success_with_florence_model(self, mock_download_model, mock_sleep, mock_validate):
        """Test successful image to text extraction with Florence model"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "A detailed image description"
        mock_download_model.return_value = mock_model

        # Execute
        result = image_to_text("/path/to/image.jpg", "Florence-2-base")

        # Assert
        assert result == "A detailed image description"
        mock_download_model.assert_called_once_with("Florence-2-base")
        mock_model.extract.assert_called_once_with("/path/to/image.jpg")
        # Florence model should NOT sleep
        mock_sleep.assert_not_called()

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_success_with_moondream(self, mock_download_model, mock_sleep, mock_validate):
        """Test successful image to text extraction with Moondream"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "Moondream caption"
        mock_download_model.return_value = mock_model

        # Execute
        result = image_to_text("/app/memes/test.jpg", "moondream2")

        # Assert
        assert result == "Moondream caption"
        mock_download_model.assert_called_once_with("moondream2")
        mock_model.extract.assert_called_once_with("/app/memes/test.jpg")
        mock_sleep.assert_not_called()

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_download_failure(self, mock_download_model, mock_validate):
        """Test image_to_text when model download fails"""
        # Setup
        mock_download_model.side_effect = TransientError("Model download failed")

        # Execute & Assert
        with pytest.raises(TransientError, match="Model download failed"):
            image_to_text("/path/to/image.jpg", "Florence-2-base")

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_extraction_failure(self, mock_download_model, mock_validate):
        """Test image_to_text when extraction fails"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.side_effect = Exception("Image extraction failed")
        mock_download_model.return_value = mock_model

        # Execute & Assert - generic exceptions become TransientError
        with pytest.raises(TransientError, match="Image processing failed"):
            image_to_text("/path/to/image.jpg", "test")

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_with_empty_description(self, mock_download_model, mock_validate):
        """Test image_to_text returns empty string when model returns empty"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = ""
        mock_download_model.return_value = mock_model

        # Execute
        result = image_to_text("/path/to/image.jpg", "Florence-2-base")

        # Assert
        assert result == ""

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_preserves_whitespace(self, mock_download_model, mock_validate):
        """Test image_to_text preserves whitespace in description"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "  Description with spaces  "
        mock_download_model.return_value = mock_model

        # Execute
        result = image_to_text("/path/to/image.jpg", "test")

        # Assert - should preserve whatever the model returns
        assert result == "  Description with spaces  "

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_with_different_image_paths(self, mock_download_model, mock_sleep, mock_validate):
        """Test image_to_text with various image paths"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "Test description"
        mock_download_model.return_value = mock_model

        # Test different path formats
        paths = [
            "/app/public/memes/image1.jpg",
            "/full/path/to/image.png",
            "relative/path/image.gif",
            "/path/with spaces/image.jpg"
        ]

        for path in paths:
            mock_model.extract.reset_mock()
            mock_validate.reset_mock()

            # Execute
            result = image_to_text(path, "test")

            # Assert
            assert result == "Test description"
            mock_model.extract.assert_called_once_with(path)

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_test_model_sleep_duration(self, mock_download_model, mock_sleep, mock_validate):
        """Test that test model sleeps for exactly 5 seconds"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "Test"
        mock_download_model.return_value = mock_model

        # Execute
        image_to_text("/path/to/image.jpg", "test")

        # Assert - verify sleep called with 5 seconds exactly
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == 5

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.download_model')
    def test_image_to_text_with_all_available_models(self, mock_download_model, mock_validate):
        """Test image_to_text with all available model names"""
        # Setup
        mock_model = MagicMock()
        mock_model.extract.return_value = "Description"
        mock_download_model.return_value = mock_model

        models = [
            "test",
            "Florence-2-base",
            "Florence-2-large",
            "SmolVLM-256M-Instruct",
            "SmolVLM-500M-Instruct",
            "moondream2"
        ]

        for model_name in models:
            mock_download_model.reset_mock()
            mock_model.extract.reset_mock()
            mock_validate.reset_mock()

            # Execute
            result = image_to_text("/test.jpg", model_name)

            # Assert
            assert result == "Description"
            mock_download_model.assert_called_once_with(model_name)
            mock_model.extract.assert_called_once()


class TestValidateImage:
    """Test suite for validate_image function"""

    def test_validate_image_file_not_found(self):
        """Test validate_image raises PermanentError for missing file"""
        with pytest.raises(PermanentError, match="Image file not found"):
            validate_image("/nonexistent/path/image.jpg")

    def test_validate_image_file_too_large(self):
        """Test validate_image raises PermanentError for oversized file"""
        # Create a temp file larger than MAX_IMAGE_SIZE_BYTES
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            # Write data larger than 10MB
            f.write(b"x" * (MAX_IMAGE_SIZE_BYTES + 1))
            temp_path = f.name

        try:
            with pytest.raises(PermanentError, match="Image file too large"):
                validate_image(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_image_corrupt_file(self):
        """Test validate_image raises PermanentError for corrupt image"""
        # Create a temp file with invalid image data
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"this is not a valid image")
            temp_path = f.name

        try:
            with pytest.raises(PermanentError, match="Invalid or corrupt image file"):
                validate_image(temp_path)
        finally:
            os.unlink(temp_path)

    def test_validate_image_valid_image(self):
        """Test validate_image passes for valid image"""
        from PIL import Image

        # Create a valid image using PIL
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            temp_path = f.name

        try:
            # Create and save a 1x1 red pixel image
            img = Image.new('RGB', (1, 1), color='red')
            img.save(temp_path, 'PNG')

            # Should not raise any exception
            validate_image(temp_path)
        finally:
            os.unlink(temp_path)

    def test_image_to_text_raises_permanent_error_for_missing_file(self):
        """Test image_to_text raises PermanentError when file doesn't exist"""
        with pytest.raises(PermanentError, match="Image file not found"):
            image_to_text("/nonexistent/image.jpg", "test")


class TestModelCache:
    """The loaded model is reused across jobs instead of being reloaded per image"""

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.model_selector')
    def test_same_model_is_constructed_once(self, mock_model_selector, mock_sleep, mock_validate):
        mock_model_selector.side_effect = lambda name: DummyModel()

        first = image_to_text("/memes/a.jpg", "test")
        second = image_to_text("/memes/b.jpg", "test")

        assert first == "Test description for a"
        assert second == "Test description for b"
        mock_model_selector.assert_called_once_with("test")

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.model_selector')
    def test_switching_model_releases_previous_before_loading(self, mock_model_selector, mock_sleep, mock_validate):
        refs = []
        alive_at_construction = []

        def build(name):
            alive_at_construction.append([ref() is not None for ref in refs])
            model = DummyModel()
            refs.append(weakref.ref(model))
            return model

        mock_model_selector.side_effect = build

        image_to_text("/memes/a.jpg", "test")
        image_to_text("/memes/b.jpg", "Florence-2-base")

        assert [c.args[0] for c in mock_model_selector.call_args_list] == ["test", "Florence-2-base"]
        # The first model must already be gone when the second one is built, so two never coexist.
        assert alive_at_construction == [[], [False]]
        assert refs[1]() is not None

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.model_selector')
    def test_release_empties_cuda_cache_when_available(self, mock_model_selector, mock_sleep, mock_validate):
        mock_model_selector.side_effect = lambda name: DummyModel()
        image_to_text("/memes/a.jpg", "test")

        with patch('image_to_text_generator.torch.cuda.is_available', return_value=True), \
                patch('image_to_text_generator.torch.cuda.empty_cache') as mock_empty_cache:
            release_model()

        mock_empty_cache.assert_called_once()

    @patch('image_to_text_generator.validate_image')
    @patch('image_to_text_generator.time.sleep')
    @patch('image_to_text_generator.model_selector')
    def test_failed_load_is_not_cached(self, mock_model_selector, mock_sleep, mock_validate):
        mock_model_selector.side_effect = [Exception("hub down"), DummyModel()]

        with pytest.raises(TransientError, match="Model download failed"):
            image_to_text("/memes/a.jpg", "test")
        assert image_to_text("/memes/a.jpg", "test") == "Test description for a"
        assert mock_model_selector.call_count == 2


class TestIdleRelease:
    """MODEL_IDLE_TIMEOUT releases a model nobody has used for a while"""

    def load_dummy(self):
        with patch('image_to_text_generator.validate_image'), \
                patch('image_to_text_generator.time.sleep'), \
                patch('image_to_text_generator.model_selector', side_effect=lambda name: DummyModel()) as mock_model_selector:
            image_to_text("/memes/a.jpg", "test")
        return mock_model_selector

    def test_idle_timeout_releases_cached_model(self, monkeypatch):
        monkeypatch.setattr(image_to_text_generator, "MODEL_IDLE_TIMEOUT", 300)
        self.load_dummy()
        now = image_to_text_generator.time.monotonic()

        assert release_idle_model(now=now + 299) is False
        assert release_idle_model(now=now + 301) is True
        # Released, so the next job has to load it again.
        assert self.load_dummy().call_count == 1

    def test_zero_timeout_never_releases(self, monkeypatch):
        monkeypatch.setattr(image_to_text_generator, "MODEL_IDLE_TIMEOUT", 0)
        self.load_dummy()
        now = image_to_text_generator.time.monotonic()

        assert release_idle_model(now=now + 10 ** 9) is False
        with patch('image_to_text_generator.model_selector') as mock_model_selector:
            with patch('image_to_text_generator.validate_image'), patch('image_to_text_generator.time.sleep'):
                image_to_text("/memes/b.jpg", "test")
        mock_model_selector.assert_not_called()

    def test_nothing_to_release_without_a_model(self, monkeypatch):
        monkeypatch.setattr(image_to_text_generator, "MODEL_IDLE_TIMEOUT", 1)
        assert release_idle_model(now=image_to_text_generator.time.monotonic() + 10) is False

    @pytest.mark.parametrize("raw, expected", [
        (None, 300),
        ("", 300),
        ("60", 60),
        ("0", 0),
        ("-5", 0),
        ("soon", 300),
    ])
    def test_parse_idle_timeout(self, raw, expected):
        assert parse_idle_timeout(raw) == expected
