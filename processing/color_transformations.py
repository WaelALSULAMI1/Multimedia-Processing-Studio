import numpy as np
from PIL import Image

from processing.image_processing import clamp, pil_to_rgb_array, rgb_array_to_pil


def grayscale(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            gray = clamp(0.299 * int(r) + 0.587 * int(g) + 0.114 * int(b))
            result[y, x] = [gray, gray, gray]

    return rgb_array_to_pil(result)


def sepia(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            gray = clamp(0.299 * int(r) + 0.587 * int(g) + 0.114 * int(b))
            red = gray
            green = gray
            blue = gray

            # Slide-style sepia starts with grayscale, then adjusts red/blue by ranges.
            if red < 63:
                red = red * 1.1
                blue = blue * 0.9
            elif red < 192:
                red = red * 1.15
                blue = blue * 0.85
            else:
                red = red * 1.08
                blue = blue * 0.93

            result[y, x] = [clamp(red), clamp(green), clamp(blue)]

    return rgb_array_to_pil(result)


def negative(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            result[y, x] = [255 - int(r), 255 - int(g), 255 - int(b)]

    return rgb_array_to_pil(result)


def posterization(image: Image.Image, levels: int = 4) -> Image.Image:
    levels = max(2, min(16, int(levels)))
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)
    step = 256 / levels

    # Slide-style posterization maps each channel into the center of its range.
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            result[y, x] = [
                clamp(int(int(r) / step) * step + step / 2),
                clamp(int(int(g) / step) * step + step / 2),
                clamp(int(int(b) / step) * step + step / 2),
            ]

    return rgb_array_to_pil(result)


COLOR_OPERATIONS = {
    "Grayscale": grayscale,
    "Sepia": sepia,
    "Negative": negative,
    "Posterization": posterization,
}
