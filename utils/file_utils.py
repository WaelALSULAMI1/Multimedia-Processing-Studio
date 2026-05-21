from PIL import Image, ImageTk


def make_preview_image(image: Image.Image, max_size=(320, 240)) -> ImageTk.PhotoImage:
    preview = image.copy()
    preview.thumbnail(max_size)
    return ImageTk.PhotoImage(preview)


def image_info_text(image: Image.Image) -> str:
    width, height = image.size
    return f"{width} x {height} pixels"

