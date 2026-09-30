"""Tests for utils.validators upload limits."""

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from utils.validators import MAX_UPLOAD_SIZE_BYTES, validate_upload_size


class _FakeFile:
    def __init__(self, size):
        self.size = size


class UploadSizeValidatorTests(SimpleTestCase):
    def test_file_within_limit_is_accepted(self):
        validate_upload_size(_FakeFile(1024))  # should not raise

    def test_file_at_limit_is_accepted(self):
        validate_upload_size(_FakeFile(MAX_UPLOAD_SIZE_BYTES))

    def test_file_over_limit_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_upload_size(_FakeFile(MAX_UPLOAD_SIZE_BYTES + 1))

    def test_object_without_size_is_ignored(self):
        validate_upload_size(object())  # should not raise
