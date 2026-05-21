import os
from dataclasses import dataclass
from typing import Callable, List, Tuple

import numpy as np
from PIL import Image


SUPPORTED_FRAME_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp")


@dataclass
class VideoInfo:
    path: str
    fps: float
    width: int
    height: int
    frame_count: int


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise ValueError("Video file support requires opencv-python. Install it with: pip install opencv-python") from exc
    return cv2


def _bgr_array_to_pil(frame: np.ndarray) -> Image.Image:
    height, width, _ = frame.shape
    rgb = np.zeros((height, width, 3), dtype=np.uint8)

    # OpenCV reads container frames as BGR. This loop only changes channel order;
    # all visual processing still happens in the manual image algorithms.
    for y in range(height):
        for x in range(width):
            blue, green, red = frame[y, x]
            rgb[y, x] = [red, green, blue]

    return Image.fromarray(rgb, "RGB")


def _pil_to_bgr_array(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"), dtype=np.uint8)
    height, width, _ = rgb.shape
    bgr = np.zeros((height, width, 3), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            red, green, blue = rgb[y, x]
            bgr[y, x] = [blue, green, red]

    return bgr


def load_video_info(video_path: str) -> VideoInfo:
    if not os.path.exists(video_path):
        raise ValueError("The selected video file does not exist.")

    cv2 = _import_cv2()
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")

    success, _ = capture.read()
    if not success:
        capture.release()
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")
    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    fps = capture.get(cv2.CAP_PROP_FPS) or 0
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()

    return VideoInfo(video_path, fps, width, height, frame_count)


def read_first_video_frame(video_path: str) -> Image.Image:
    if not os.path.exists(video_path):
        raise ValueError("The selected video file does not exist.")

    cv2 = _import_cv2()
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")

    success, frame = capture.read()
    capture.release()
    if not success:
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")

    return _bgr_array_to_pil(frame)


def preview_processed_video_frame(video_path: str, operation: Callable[[Image.Image], Image.Image]) -> Tuple[Image.Image, Image.Image]:
    original = read_first_video_frame(video_path)
    processed = operation(original)
    return original, processed


def create_video_writer(output_path: str, fps: float, width: int, height: int):
    cv2 = _import_cv2()
    extension = os.path.splitext(output_path)[1].lower()
    fps = fps or 24

    if extension == ".mp4":
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            fps,
            (width, height),
        )
        if writer.isOpened():
            return writer
        raise ValueError("MP4 export failed on this system. Please save as AVI instead.")

    for codec in ["MJPG", "XVID"]:
        writer = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*codec),
            fps,
            (width, height),
        )
        if writer.isOpened():
            return writer

    raise ValueError("Could not create the output AVI file. Please try a different output path.")


def process_video_file(video_path: str, output_path: str, operation: Callable[[Image.Image], Image.Image]) -> int:
    if not os.path.exists(video_path):
        raise ValueError("The selected video file does not exist.")

    cv2 = _import_cv2()
    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")

    fps = capture.get(cv2.CAP_PROP_FPS) or 24
    success, first_frame = capture.read()
    if not success:
        capture.release()
        raise ValueError("Could not read this video. Please try a standard MP4 or AVI file.")

    first_original = _bgr_array_to_pil(first_frame)
    first_processed = operation(first_original)
    output_width, output_height = first_processed.size

    try:
        writer = create_video_writer(output_path, fps, output_width, output_height)
    except ValueError:
        capture.release()
        raise

    # Video is processed frame by frame by reusing the manual image operations.
    writer.write(_pil_to_bgr_array(first_processed))
    processed_count = 1

    while True:
        success, frame = capture.read()
        if not success:
            break
        original = _bgr_array_to_pil(frame)
        processed = operation(original)
        if processed.size != (output_width, output_height):
            capture.release()
            writer.release()
            raise ValueError("Processed frames must all have the same size for video export.")
        writer.write(_pil_to_bgr_array(processed))
        processed_count += 1

    capture.release()
    writer.release()
    return processed_count


def list_frame_files(folder_path: str) -> List[str]:
    files = []
    for name in os.listdir(folder_path):
        if name.lower().endswith(SUPPORTED_FRAME_EXTENSIONS):
            files.append(os.path.join(folder_path, name))
    files.sort()
    return files


def process_frame_folder(
    input_folder: str,
    output_folder: str,
    operation: Callable[[Image.Image], Image.Image],
) -> int:
    frame_files = list_frame_files(input_folder)
    if not frame_files:
        raise ValueError("No image frames found in the selected folder.")

    os.makedirs(output_folder, exist_ok=True)

    for index, frame_path in enumerate(frame_files):
        with Image.open(frame_path) as image:
            processed = operation(image)
            original_name = os.path.basename(frame_path)
            output_name = f"processed_{index:04d}_{original_name}"
            processed.save(os.path.join(output_folder, output_name))

    return len(frame_files)


def preview_processed_frame(input_folder: str, operation: Callable[[Image.Image], Image.Image]):
    frame_files = list_frame_files(input_folder)
    if not frame_files:
        raise ValueError("No image frames found in the selected folder.")

    original = Image.open(frame_files[0]).convert("RGB")
    processed = operation(original)
    return original, processed
