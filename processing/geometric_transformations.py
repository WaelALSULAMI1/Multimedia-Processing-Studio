import numpy as np
from PIL import Image

from processing.image_processing import pil_to_rgb_array, rgb_array_to_pil


def rotate_90(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, channels = pixels.shape
    result = np.zeros((width, height, channels), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            result[x, height - y - 1] = pixels[y, x]

    return rgb_array_to_pil(result)


def rotate_180(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            result[height - y - 1, width - x - 1] = pixels[y, x]

    return rgb_array_to_pil(result)


def rotate_270(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, channels = pixels.shape
    result = np.zeros((width, height, channels), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            result[width - x - 1, y] = pixels[y, x]

    return rgb_array_to_pil(result)


def horizontal_reflection(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            result[y, width - 1 - x] = pixels[y, x]

    return rgb_array_to_pil(result)


def vertical_reflection(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            result[height - 1 - y, x] = pixels[y, x]

    return rgb_array_to_pil(result)


def nearest_neighbor_scale(image: Image.Image, scale_factor: float = 1.5) -> Image.Image:
    if scale_factor <= 0:
        raise ValueError("Scale factor must be greater than zero.")

    pixels = pil_to_rgb_array(image)
    old_height, old_width, channels = pixels.shape
    new_width = max(1, int(old_width * scale_factor))
    new_height = max(1, int(old_height * scale_factor))
    result = np.zeros((new_height, new_width, channels), dtype=np.uint8)

    # Nearest-neighbor scaling copies the closest original pixel into each new pixel.
    for new_y in range(new_height):
        for new_x in range(new_width):
            old_x = min(old_width - 1, int(new_x / scale_factor))
            old_y = min(old_height - 1, int(new_y / scale_factor))
            result[new_y, new_x] = pixels[old_y, old_x]

    return rgb_array_to_pil(result)


def crop(image: Image.Image, left: int, top: int, right: int, bottom: int) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, channels = pixels.shape

    if not (0 <= left < right <= width):
        raise ValueError(f"Crop must satisfy 0 <= left < right <= image width ({width}).")
    if not (0 <= top < bottom <= height):
        raise ValueError(f"Crop must satisfy 0 <= top < bottom <= image height ({height}).")

    new_width = right - left
    new_height = bottom - top
    result = np.zeros((new_height, new_width, channels), dtype=np.uint8)

    for y in range(new_height):
        for x in range(new_width):
            result[y, x] = pixels[top + y, left + x]

    return rgb_array_to_pil(result)


def center_crop(image: Image.Image) -> Image.Image:
    width, height = image.size
    left = width // 4
    top = height // 4
    right = width - left
    bottom = height - top
    return crop(image, left, top, right, bottom)


GEOMETRIC_OPERATIONS = {
    "Rotate 90": rotate_90,
    "Rotate 180": rotate_180,
    "Rotate 270": rotate_270,
    "Horizontal Reflection": horizontal_reflection,
    "Vertical Reflection": vertical_reflection,
    "Scale": nearest_neighbor_scale,
    "Center Crop": center_crop,
    "Custom Crop": center_crop,
}
