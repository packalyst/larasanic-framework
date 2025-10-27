"""
File Validation Rules
Rules for validating uploaded files
"""
from typing import Any, Optional
from larasanic.validation.rules import ValidationRule
import mimetypes
import os


class File(ValidationRule):
    """Field must be a file upload"""

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a Sanic File object
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be a file."


class Image(ValidationRule):
    """Field must be an image file"""

    IMAGE_MIMES = {'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/svg+xml', 'image/webp'}

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Check mime type
        mime_type = value.type if hasattr(value, 'type') else mimetypes.guess_type(value.name)[0]

        if mime_type not in self.IMAGE_MIMES:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        return f"The {field} must be an image."


class Mimes(ValidationRule):
    """
    Field must have one of the specified MIME types

    Usage:
        'document': 'mimes:pdf,doc,docx'
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Get allowed mimes
        allowed_extensions = self.parameters

        # Get file extension
        _, ext = os.path.splitext(value.name)
        ext = ext.lstrip('.').lower()

        if ext not in allowed_extensions:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        extensions = ', '.join(self.parameters)
        return f"The {field} must be a file of type: {extensions}."


class MimeTypes(ValidationRule):
    """
    Field must have one of the specified MIME types (by MIME type, not extension)

    Usage:
        'file': 'mimetypes:application/pdf,image/jpeg'
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Get allowed MIME types
        allowed_mimes = self.parameters

        # Get file MIME type
        mime_type = value.type if hasattr(value, 'type') else mimetypes.guess_type(value.name)[0]

        if mime_type not in allowed_mimes:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        mimes = ', '.join(self.parameters)
        return f"The {field} must be a file of type: {mimes}."


class MaxFileSize(ValidationRule):
    """
    Field file size must not exceed maximum (in kilobytes)

    Usage:
        'file': 'max_file_size:2048'  # 2MB max
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Get max size in KB
        max_size_kb = self.parameters[0]

        # Get file size in KB
        file_size_kb = len(value.body) / 1024

        if file_size_kb > max_size_kb:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        max_kb = self.parameters[0]
        return f"The {field} may not be greater than {max_kb} kilobytes."


class MinFileSize(ValidationRule):
    """
    Field file size must be at least minimum (in kilobytes)

    Usage:
        'file': 'min_file_size:100'  # 100KB min
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Get min size in KB
        min_size_kb = self.parameters[0]

        # Get file size in KB
        file_size_kb = len(value.body) / 1024

        if file_size_kb < min_size_kb:
            return False, self.message(field)

        return True, None

    def message(self, field: str) -> str:
        min_kb = self.parameters[0]
        return f"The {field} must be at least {min_kb} kilobytes."


class Dimensions(ValidationRule):
    """
    Image must meet dimension requirements

    Usage:
        'image': 'dimensions:min_width=100,max_width=1000,min_height=100,max_height=1000'
    """

    async def validate(self, field: str, value: Any, data: dict) -> tuple[bool, Optional[str]]:
        if value is None or value == '':
            return True, None

        # Check if it's a file
        if not hasattr(value, 'name') or not hasattr(value, 'body'):
            return False, f"The {field} must be a file."

        # Parse dimension constraints from parameters
        constraints = {}
        for param in self.parameters:
            if '=' in str(param):
                key, val = str(param).split('=', 1)
                constraints[key] = int(val)

        # Try to get image dimensions
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(value.body))
            width, height = img.size

            # Check constraints
            if 'min_width' in constraints and width < constraints['min_width']:
                return False, f"The {field} width must be at least {constraints['min_width']} pixels."

            if 'max_width' in constraints and width > constraints['max_width']:
                return False, f"The {field} width may not be greater than {constraints['max_width']} pixels."

            if 'min_height' in constraints and height < constraints['min_height']:
                return False, f"The {field} height must be at least {constraints['min_height']} pixels."

            if 'max_height' in constraints and height > constraints['max_height']:
                return False, f"The {field} height may not be greater than {constraints['max_height']} pixels."

            if 'width' in constraints and width != constraints['width']:
                return False, f"The {field} width must be exactly {constraints['width']} pixels."

            if 'height' in constraints and height != constraints['height']:
                return False, f"The {field} height must be exactly {constraints['height']} pixels."

            if 'ratio' in constraints:
                ratio_str = str(constraints['ratio'])
                if '/' in ratio_str:
                    ratio_w, ratio_h = map(int, ratio_str.split('/'))
                    expected_ratio = ratio_w / ratio_h
                    actual_ratio = width / height
                    # Allow 1% tolerance
                    if abs(expected_ratio - actual_ratio) > 0.01:
                        return False, f"The {field} must have an aspect ratio of {ratio_str}."

            return True, None

        except ImportError:
            return False, "PIL (Pillow) is required for image dimension validation. Install with: pip install Pillow"
        except Exception as e:
            return False, f"Could not read image dimensions: {str(e)}"

    def message(self, field: str) -> str:
        return f"The {field} does not meet the dimension requirements."
