import math

import numpy as np
from PIL import Image


def clamp(value: float, minimum: int = 0, maximum: int = 255) -> int:
    """Keep a pixel value inside the valid 8-bit range."""
    return max(minimum, min(maximum, int(round(value))))


def pil_to_rgb_array(image: Image.Image) -> np.ndarray:
    return np.array(image.convert("RGB"), dtype=np.uint8)


def rgb_array_to_pil(array: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(array, 0, 255).astype(np.uint8), "RGB")


def brightness_factor_from_slider(slider_value: float) -> float:
    if slider_value >= 0:
        return 1.0 + slider_value / 100.0
    return 1.0 + slider_value / 200.0


def adjust_brightness(image: Image.Image, slider_value: float = 0) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)
    factor = brightness_factor_from_slider(slider_value)

    # Slide-style brightness: manually scale each RGB channel by the selected factor.
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            result[y, x] = [
                clamp(int(r) * factor),
                clamp(int(g) * factor),
                clamp(int(b) * factor),
            ]

    return rgb_array_to_pil(result)


def adjust_contrast(image: Image.Image, factor: float = 1.4) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.zeros_like(pixels)

    # Contrast is stretched manually around the middle gray value 128.
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            result[y, x] = [
                clamp(128 + factor * (int(r) - 128)),
                clamp(128 + factor * (int(g) - 128)),
                clamp(128 + factor * (int(b) - 128)),
            ]

    return rgb_array_to_pil(result)


def _weighted_gray_value(r: int, g: int, b: int) -> int:
    return clamp(0.299 * r + 0.587 * g + 0.114 * b)


def histogram_equalization(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    gray = np.zeros((height, width), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            gray[y, x] = _weighted_gray_value(r, g, b)

    histogram = [0] * 256
    for y in range(height):
        for x in range(width):
            histogram[int(gray[y, x])] += 1

    cumulative = [0] * 256
    running_total = 0
    for i in range(256):
        running_total += histogram[i]
        cumulative[i] = running_total

    total_pixels = height * width
    first_nonzero = next((value for value in cumulative if value > 0), 0)
    result = np.zeros_like(pixels)

    for y in range(height):
        for x in range(width):
            old_value = int(gray[y, x])
            if total_pixels == first_nonzero:
                new_value = old_value
            else:
                new_value = round(
                    (cumulative[old_value] - first_nonzero)
                    / (total_pixels - first_nonzero)
                    * 255
                )
            result[y, x] = [clamp(new_value), clamp(new_value), clamp(new_value)]

    return rgb_array_to_pil(result)


def average_filter_3x3(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.copy(pixels)

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            sums = [0, 0, 0]
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    r, g, b = pixels[y + ky, x + kx]
                    sums[0] += int(r)
                    sums[1] += int(g)
                    sums[2] += int(b)
            result[y, x] = [clamp(sums[0] / 9), clamp(sums[1] / 9), clamp(sums[2] / 9)]

    return rgb_array_to_pil(result)


def median_filter_3x3(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.copy(pixels)

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            red_values = []
            green_values = []
            blue_values = []
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    r, g, b = pixels[y + ky, x + kx]
                    red_values.append(int(r))
                    green_values.append(int(g))
                    blue_values.append(int(b))
            red_values.sort()
            green_values.sort()
            blue_values.sort()
            result[y, x] = [red_values[4], green_values[4], blue_values[4]]

    return rgb_array_to_pil(result)


def sobel_edge_detection(image: Image.Image) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    gray = np.zeros((height, width), dtype=np.uint8)
    result = np.zeros_like(pixels)

    gx_kernel = [[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]]
    gy_kernel = [[-1, -2, -1], [0, 0, 0], [1, 2, 1]]

    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            gray[y, x] = _weighted_gray_value(r, g, b)

    for y in range(1, height - 1):
        for x in range(1, width - 1):
            gx = 0
            gy = 0
            for ky in range(-1, 2):
                for kx in range(-1, 2):
                    sample = int(gray[y + ky, x + kx])
                    gx += sample * gx_kernel[ky + 1][kx + 1]
                    gy += sample * gy_kernel[ky + 1][kx + 1]
            magnitude = clamp(math.sqrt(gx * gx + gy * gy))
            result[y, x] = [magnitude, magnitude, magnitude]

    return rgb_array_to_pil(result)


def simple_edge_detection(image: Image.Image, threshold: int = 30) -> Image.Image:
    pixels = pil_to_rgb_array(image)
    height, width, _ = pixels.shape
    result = np.full_like(pixels, 255)

    # Slide-style edge detection compares each pixel brightness with its left neighbor.
    for y in range(height):
        for x in range(1, width):
            r, g, b = pixels[y, x]
            left_r, left_g, left_b = pixels[y, x - 1]
            current_brightness = 0.299 * int(r) + 0.587 * int(g) + 0.114 * int(b)
            left_brightness = 0.299 * int(left_r) + 0.587 * int(left_g) + 0.114 * int(left_b)
            difference = abs(current_brightness - left_brightness)
            if difference > threshold:
                result[y, x] = [0, 0, 0]
            else:
                result[y, x] = [255, 255, 255]

    return rgb_array_to_pil(result)


IMAGE_OPERATIONS = {
    "Brightness": adjust_brightness,
    "Contrast": adjust_contrast,
    "Histogram Equalization": histogram_equalization,
    "Average Filter 3x3": average_filter_3x3,
    "Median Filter 3x3": median_filter_3x3,
    "Simple Edge Detection": simple_edge_detection,
    "Sobel Edge Detection": sobel_edge_detection,
}
