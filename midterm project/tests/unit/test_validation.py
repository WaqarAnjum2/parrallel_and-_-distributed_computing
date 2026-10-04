"""
Unit tests for parameter validation.
"""

import pytest

from worker.core.exceptions import InvalidParameterError, FileTooLargeError
from worker.validation.params import (
    validate_bitrate,
    validate_codec,
    validate_filename,
    validate_file_size,
    validate_preset,
    validate_resolution,
    validate_sha256,
)


class TestCodecValidation:
    def test_valid_h264(self) -> None:
        assert validate_codec("h264") == "h264_nvenc"

    def test_valid_hevc(self) -> None:
        assert validate_codec("hevc") == "hevc_nvenc"

    def test_invalid_codec(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_codec("vp9")

    def test_empty_codec(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_codec("")


class TestResolutionValidation:
    def test_valid_1080p(self) -> None:
        assert validate_resolution("1920x1080") == "1920x1080"

    def test_valid_720p(self) -> None:
        assert validate_resolution("1280x720") == "1280x720"

    def test_invalid_resolution(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_resolution("999999x999999")

    def test_negative_resolution(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_resolution("-1x100")


class TestBitrateValidation:
    def test_valid_5m(self) -> None:
        assert validate_bitrate("5M") == "5M"

    def test_invalid_bitrate(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_bitrate("999M")


class TestPresetValidation:
    def test_valid_p4(self) -> None:
        assert validate_preset("p4") == "p4"

    def test_invalid_preset(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_preset("ultrafast")


class TestFilenameValidation:
    def test_valid_filename(self) -> None:
        assert validate_filename("movie.mp4") == "movie.mp4"

    def test_path_traversal_blocked(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_filename("../../etc/passwd")

    def test_backslash_blocked(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_filename("..\\secret.mp4")

    def test_absolute_path_blocked(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_filename("C:\\Users\\video.mp4")

    def test_unsupported_extension(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_filename("malware.exe")


class TestFileSizeValidation:
    def test_valid_size(self) -> None:
        validate_file_size(1024 * 1024, 4096 * 1024 * 1024)  # 1 MB < 4 GB

    def test_too_large(self) -> None:
        with pytest.raises(FileTooLargeError):
            validate_file_size(5 * 1024 * 1024 * 1024, 4096 * 1024 * 1024)

    def test_zero_size(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_file_size(0, 4096 * 1024 * 1024)

    def test_negative_size(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_file_size(-1, 4096 * 1024 * 1024)


class TestSHA256Validation:
    def test_valid_hash(self) -> None:
        valid = "a" * 64
        assert validate_sha256(valid) == valid

    def test_uppercase_normalized(self) -> None:
        upper = "A" * 64
        assert validate_sha256(upper) == "a" * 64

    def test_too_short(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_sha256("abc123")

    def test_too_long(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_sha256("a" * 65)

    def test_non_hex_chars(self) -> None:
        with pytest.raises(InvalidParameterError):
            validate_sha256("g" * 64)
