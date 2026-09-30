"""Reusable file-upload validators.

Django's ``ImageField`` verifies that a file is a decodable image via Pillow,
but it does not cap the size or restrict the extension. These validators close
that gap for user-controlled uploads (profile images, payment proofs, QR codes)
so an oversized or mislabeled file cannot be stored.
"""

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

# 5 MB is generous for a profile picture or a screenshot of a payment receipt.
MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024

ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'webp', 'gif']


def validate_upload_size(value):
    """Reject uploads larger than :data:`MAX_UPLOAD_SIZE_BYTES`."""
    size = getattr(value, 'size', None)
    if size is not None and size > MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            _('File is too large (%(size).1f MB). Maximum size is %(max).0f MB.'),
            params={
                'size': size / (1024 * 1024),
                'max': MAX_UPLOAD_SIZE_BYTES / (1024 * 1024),
            },
        )


# Instantiate once so migrations serialize a stable, importable reference.
validate_image_extension = FileExtensionValidator(ALLOWED_IMAGE_EXTENSIONS)

IMAGE_UPLOAD_VALIDATORS = [validate_image_extension, validate_upload_size]
