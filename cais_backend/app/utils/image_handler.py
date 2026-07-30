"""
Image Handler - Image Processing Utilities

This module provides utilities for image processing.
"""

import os
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Tuple, Dict, Any


class ImageHandler:
    """
    Image handler for image processing.
    """

    @staticmethod
    def resize_image(
        image_path: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Resize an image.
        """
        img = Image.open(image_path)

        if width and height:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        elif width:
            ratio = width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((width, new_height), Image.Resampling.LANCZOS)
        elif height:
            ratio = height / img.height
            new_width = int(img.width * ratio)
            img = img.resize((new_width, height), Image.Resampling.LANCZOS)

        if output_path is None:
            output_path = image_path

        img.save(output_path)
        return output_path

    @staticmethod
    def crop_image(
        image_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Crop an image.
        """
        img = Image.open(image_path)
        cropped = img.crop((x, y, x + width, y + height))

        if output_path is None:
            output_path = image_path

        cropped.save(output_path)
        return output_path

    @staticmethod
    def draw_rectangle(
        image_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
        color: str = "red",
        thickness: int = 3,
        output_path: Optional[str] = None
    ) -> str:
        """
        Draw a rectangle on an image.
        """
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        draw.rectangle(
            [(x, y), (x + width, y + height)],
            outline=color,
            width=thickness
        )

        if output_path is None:
            output_path = image_path

        img.save(output_path)
        return output_path

    @staticmethod
    def draw_text(
        image_path: str,
        text: str,
        x: int,
        y: int,
        color: str = "red",
        size: int = 16,
        output_path: Optional[str] = None
    ) -> str:
        """
        Draw text on an image.
        """
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", size)
        except:
            font = ImageFont.load_default()

        draw.text((x, y), text, fill=color, font=font)

        if output_path is None:
            output_path = image_path

        img.save(output_path)
        return output_path

    @staticmethod
    def add_padding(
        image_path: str,
        padding: int,
        output_path: Optional[str] = None
    ) -> str:
        """
        Add padding to an image.
        """
        img = Image.open(image_path)
        new_width = img.width + padding * 2
        new_height = img.height + padding * 2

        new_img = Image.new("RGB", (new_width, new_height), "white")
        new_img.paste(img, (padding, padding))

        if output_path is None:
            output_path = image_path

        new_img.save(output_path)
        return output_path

    @staticmethod
    def get_image_info(image_path: str) -> Dict[str, Any]:
        """
        Get image information.
        """
        img = Image.open(image_path)
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "size": os.path.getsize(image_path),
        }

    @staticmethod
    def convert_format(
        image_path: str,
        output_format: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert image format.
        """
        img = Image.open(image_path)

        if output_path is None:
            base = os.path.splitext(image_path)[0]
            output_path = f"{base}.{output_format.lower()}"

        img.save(output_path, format=output_format.upper())
        return output_path
