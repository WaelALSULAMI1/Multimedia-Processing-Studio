import os
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from processing.audio_processing import (
    AUDIO_OPERATIONS,
    AudioData,
    change_volume,
    cut_audio,
    duration_seconds,
    load_audio_file,
    save_audio_file,
)
from processing.color_transformations import COLOR_OPERATIONS, posterization
from processing.geometric_transformations import (
    GEOMETRIC_OPERATIONS,
    crop,
    nearest_neighbor_scale,
)
from processing.image_processing import (
    IMAGE_OPERATIONS,
    adjust_brightness,
    adjust_contrast,
    brightness_factor_from_slider,
)
from processing.video_processing import (
    load_video_info,
    preview_processed_frame,
    preview_processed_video_frame,
    process_frame_folder,
    process_video_file,
    read_first_video_frame,
)


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


def contrast_factor_from_slider(slider_value: float) -> float:
    if slider_value >= 0:
        return 1.0 + slider_value
    return 1.0 + (slider_value * 0.9)


class SliderControl(ctk.CTkFrame):
    def __init__(self, master, label, from_, to, default, steps, formatter):
        super().__init__(master)
        self.formatter = formatter
        self.label = ctk.CTkLabel(self, text="")
        self.label.pack(side="left", padx=(10, 8), pady=8)
        self.slider = ctk.CTkSlider(
            self,
            from_=from_,
            to=to,
            number_of_steps=steps,
            command=self._on_change,
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        self.name = label
        self.slider.set(default)
        self._on_change(default)

    def _on_change(self, value):
        self.label.configure(text=f"{self.name}: {self.formatter(float(value))}")

    def get(self) -> float:
        return float(self.slider.get())


class BaseImageTab(ctk.CTkFrame):
    def __init__(self, master, operations):
        super().__init__(master)
        self.operations = operations
        self.original_image = None
        self.processed_image = None
        self.original_preview = None
        self.processed_preview = None
        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=12, pady=12)

        ctk.CTkButton(top_bar, text="Upload Image", command=self.load_image).pack(side="left", padx=6, pady=8)
        self.operation_menu = ctk.CTkOptionMenu(
            top_bar,
            values=list(self.operations.keys()),
            command=lambda _: self.update_controls(),
        )
        self.operation_menu.pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Apply Operation", command=self.apply_operation).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Save Result", command=self.save_result).pack(side="left", padx=6, pady=8)

        self.controls = ctk.CTkFrame(self)
        self.controls.pack(fill="x", padx=12, pady=(0, 8))
        self._build_parameter_controls()

        self.status_label = ctk.CTkLabel(self, text="No image loaded.")
        self.status_label.pack(anchor="w", padx=18)

        previews = ctk.CTkFrame(self)
        previews.pack(fill="both", expand=True, padx=12, pady=12)
        previews.grid_columnconfigure((0, 1), weight=1)
        previews.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(previews, text="Original Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=10, pady=8
        )
        ctk.CTkLabel(previews, text="Processed Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=1, padx=10, pady=8
        )
        self.original_label = ctk.CTkLabel(previews, text="Upload an image")
        self.original_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.processed_label = ctk.CTkLabel(previews, text="Apply an operation")
        self.processed_label.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.update_controls()

    def _build_parameter_controls(self):
        self.brightness_control = SliderControl(
            self.controls, "Brightness", -100, 100, 0, 200, lambda value: f"{int(round(value))}"
        )
        self.contrast_control = SliderControl(
            self.controls,
            "Contrast",
            -1.0,
            1.0,
            0,
            200,
            lambda value: f"slider {value:.2f}, factor {contrast_factor_from_slider(value):.2f}x",
        )
        self.posterize_control = SliderControl(
            self.controls, "Posterization Levels", 2, 16, 4, 14, lambda value: f"{int(round(value))}"
        )

    def update_controls(self):
        for control in [self.brightness_control, self.contrast_control, self.posterize_control]:
            control.pack_forget()

        operation_name = self.operation_menu.get()
        if operation_name == "Brightness":
            self.brightness_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Contrast":
            self.contrast_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Posterization":
            self.posterize_control.pack(fill="x", padx=6, pady=4)

    def _operation_function(self):
        operation_name = self.operation_menu.get()
        if operation_name == "Brightness":
            value = self.brightness_control.get()
            factor = brightness_factor_from_slider(value)
            return lambda image: adjust_brightness(image, value), f"Brightness slider {value:.0f}, factor {factor:.2f}x"
        if operation_name == "Contrast":
            slider_value = self.contrast_control.get()
            factor = contrast_factor_from_slider(slider_value)
            return lambda image: adjust_contrast(image, factor), f"Contrast {factor:.2f}x"
        if operation_name == "Posterization":
            levels = int(round(self.posterize_control.get()))
            return lambda image: posterization(image, levels), f"Posterization {levels} levels"
        return self.operations[operation_name], operation_name

    def _display_image(self, label, image, attr_name):
        preview = image.copy()
        preview.thumbnail((360, 280))
        ctk_image = ctk.CTkImage(light_image=preview, dark_image=preview, size=preview.size)
        setattr(self, attr_name, ctk_image)
        label.configure(image=ctk_image, text="")

    def load_image(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            self.original_image = Image.open(path).convert("RGB")
            self.processed_image = None
            self._display_image(self.original_label, self.original_image, "original_preview")
            self.processed_label.configure(image=None, text="Apply an operation")
            width, height = self.original_image.size
            self.status_label.configure(text=f"Loaded: {os.path.basename(path)} | {width} x {height}")
        except Exception as error:
            messagebox.showerror("Image Error", str(error))

    def apply_operation(self):
        if self.original_image is None:
            messagebox.showwarning("Missing Image", "Please upload an image first.")
            return
        try:
            operation, description = self._operation_function()
            self.processed_image = operation(self.original_image)
            self._display_image(self.processed_label, self.processed_image, "processed_preview")
            self.status_label.configure(text=f"Applied: {description}")
        except Exception as error:
            messagebox.showerror("Processing Error", str(error))

    def save_result(self):
        if self.processed_image is None:
            messagebox.showwarning("Missing Result", "Please apply an operation first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Processed Image",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg"), ("All files", "*.*")],
        )
        if not path:
            return
        self.processed_image.save(path)
        messagebox.showinfo("Saved", f"Processed image saved to:\n{path}")


class GeometricTab(BaseImageTab):
    def _build_parameter_controls(self):
        self.scale_control = SliderControl(
            self.controls, "Scale Factor", 0.1, 3.0, 1.0, 290, lambda value: f"{value:.2f}x"
        )

        self.crop_control = ctk.CTkFrame(self.controls)
        for label_text, default in [("Left", "20"), ("Top", "20"), ("Right", "220"), ("Bottom", "220")]:
            ctk.CTkLabel(self.crop_control, text=label_text).pack(side="left", padx=(10, 4), pady=8)
            entry = ctk.CTkEntry(self.crop_control, width=70)
            entry.insert(0, default)
            entry.pack(side="left", padx=4, pady=8)
            setattr(self, f"{label_text.lower()}_entry", entry)

    def update_controls(self):
        for control in [self.scale_control, self.crop_control]:
            control.pack_forget()

        operation_name = self.operation_menu.get()
        if operation_name == "Scale":
            self.scale_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Custom Crop":
            self.crop_control.pack(fill="x", padx=6, pady=4)

    def _operation_function(self):
        operation_name = self.operation_menu.get()
        if operation_name == "Scale":
            factor = self.scale_control.get()
            return lambda image: nearest_neighbor_scale(image, factor), f"Scale {factor:.2f}x"
        if operation_name == "Custom Crop":
            values = [
                int(self.left_entry.get()),
                int(self.top_entry.get()),
                int(self.right_entry.get()),
                int(self.bottom_entry.get()),
            ]
            return lambda image: crop(image, *values), f"Custom Crop {values}"
        return self.operations[operation_name], operation_name


class AudioTab(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.audio = None
        self.processed_audio = None
        self._build_ui()

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=12, pady=12)

        ctk.CTkButton(top_bar, text="Upload Audio", command=self.load_audio).pack(side="left", padx=6, pady=8)
        self.operation_menu = ctk.CTkOptionMenu(
            top_bar,
            values=list(AUDIO_OPERATIONS.keys()),
            command=lambda _: self.update_controls(),
        )
        self.operation_menu.pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Apply Operation", command=self.apply_operation).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Save Audio", command=self.save_result).pack(side="left", padx=6, pady=8)

        self.controls = ctk.CTkFrame(self)
        self.controls.pack(fill="x", padx=12, pady=(0, 12))
        self.volume_control = SliderControl(
            self.controls, "Volume Factor", 0.0, 3.0, 1.0, 300, lambda value: f"{value:.2f}x"
        )

        self.cut_control = ctk.CTkFrame(self.controls)
        ctk.CTkLabel(self.cut_control, text="Start (sec)").pack(side="left", padx=(10, 4), pady=8)
        self.start_entry = ctk.CTkEntry(self.cut_control, width=90)
        self.start_entry.insert(0, "0")
        self.start_entry.pack(side="left", padx=4, pady=8)
        ctk.CTkLabel(self.cut_control, text="End (sec)").pack(side="left", padx=(10, 4), pady=8)
        self.end_entry = ctk.CTkEntry(self.cut_control, width=90)
        self.end_entry.insert(0, "3")
        self.end_entry.pack(side="left", padx=4, pady=8)

        info_box = ctk.CTkFrame(self)
        info_box.pack(fill="both", expand=True, padx=12, pady=12)
        self.original_info = ctk.CTkLabel(info_box, text="Original audio: none", justify="left", anchor="w")
        self.original_info.pack(fill="x", padx=16, pady=12)
        self.processed_info = ctk.CTkLabel(info_box, text="Processed audio: none", justify="left", anchor="w")
        self.processed_info.pack(fill="x", padx=16, pady=12)
        self.update_controls()

    def update_controls(self):
        self.volume_control.pack_forget()
        self.cut_control.pack_forget()
        operation_name = self.operation_menu.get()
        if operation_name == "Volume":
            self.volume_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Splice/Cut":
            self.cut_control.pack(fill="x", padx=6, pady=4)

    def _audio_summary(self, audio: AudioData) -> str:
        frames = len(audio.samples) if audio.channels == 1 else audio.samples.shape[0]
        return (
            f"Sample rate: {audio.sample_rate} Hz\n"
            f"Channels: {audio.channels}\n"
            f"Frames: {frames}\n"
            f"Duration: {duration_seconds(audio):.2f} seconds\n"
            f"Sample format: 16-bit PCM\n"
            f"Source format: {audio.source_format.upper()}"
        )

    def load_audio(self):
        path = filedialog.askopenfilename(
            title="Select Audio",
            filetypes=[("Audio files", "*.wav *.mp3"), ("WAV files", "*.wav"), ("MP3 files", "*.mp3")],
        )
        if not path:
            return
        try:
            self.audio = load_audio_file(path)
            self.processed_audio = None
            self.original_info.configure(text=f"Original audio: {os.path.basename(path)}\n{self._audio_summary(self.audio)}")
            self.processed_info.configure(text="Processed audio: none")
            self.end_entry.delete(0, "end")
            self.end_entry.insert(0, f"{min(3, duration_seconds(self.audio)):.2f}")
        except Exception as error:
            messagebox.showerror("Audio Error", str(error))

    def apply_operation(self):
        if self.audio is None:
            messagebox.showwarning("Missing Audio", "Please upload a WAV or MP3 file first.")
            return
        try:
            operation_name = self.operation_menu.get()
            if operation_name == "Volume":
                factor = self.volume_control.get()
                self.processed_audio = change_volume(self.audio, factor)
                description = f"Volume {factor:.2f}x"
            elif operation_name == "Splice/Cut":
                start = float(self.start_entry.get())
                end = float(self.end_entry.get())
                self.processed_audio = cut_audio(self.audio, start, end)
                description = f"Splice/Cut {start:.2f}s to {end:.2f}s"
            else:
                self.processed_audio = AUDIO_OPERATIONS[operation_name](self.audio)
                description = operation_name
            self.processed_info.configure(text=f"Processed audio: {description}\n{self._audio_summary(self.processed_audio)}")
        except Exception as error:
            messagebox.showerror("Processing Error", str(error))

    def save_result(self):
        if self.processed_audio is None:
            messagebox.showwarning("Missing Result", "Please apply an audio operation first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Audio",
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav"), ("MP3 files", "*.mp3")],
        )
        if not path:
            return
        try:
            save_audio_file(path, self.processed_audio)
            messagebox.showinfo("Saved", f"Processed audio saved to:\n{path}")
        except Exception as error:
            messagebox.showerror("Save Error", str(error))


class VideoFrameTab(BaseImageTab):
    def __init__(self, master):
        self.video_path = None
        self.video_info = None
        self.frame_folder = None
        safe_video_operations = {
            "Brightness": IMAGE_OPERATIONS["Brightness"],
            "Contrast": IMAGE_OPERATIONS["Contrast"],
            "Grayscale": COLOR_OPERATIONS["Grayscale"],
            "Sepia": COLOR_OPERATIONS["Sepia"],
            "Negative": COLOR_OPERATIONS["Negative"],
            "Posterization": COLOR_OPERATIONS["Posterization"],
            "Average Filter 3x3": IMAGE_OPERATIONS["Average Filter 3x3"],
            "Median Filter 3x3": IMAGE_OPERATIONS["Median Filter 3x3"],
            "Simple Edge Detection": IMAGE_OPERATIONS["Simple Edge Detection"],
            "Sobel Edge Detection": IMAGE_OPERATIONS["Sobel Edge Detection"],
        }
        super().__init__(master, safe_video_operations)

    def _build_ui(self):
        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=12, pady=12)

        ctk.CTkButton(top_bar, text="Load Video File", command=self.load_video_file).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Load Frame Folder", command=self.load_frame_folder).pack(side="left", padx=6, pady=8)
        self.operation_menu = ctk.CTkOptionMenu(
            top_bar,
            values=list(self.operations.keys()),
            command=lambda _: self.update_controls(),
        )
        self.operation_menu.pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Preview First Frame", command=self.apply_operation).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Save Processed Video", command=self.save_result).pack(side="left", padx=6, pady=8)
        ctk.CTkButton(top_bar, text="Save Processed Frames", command=self.save_processed_frames).pack(side="left", padx=6, pady=8)

        self.controls = ctk.CTkFrame(self)
        self.controls.pack(fill="x", padx=12, pady=(0, 8))
        self._build_parameter_controls()

        self.status_label = ctk.CTkLabel(
            self,
            text="No video loaded. Video processing applies manual image operations to every frame.",
        )
        self.status_label.pack(anchor="w", padx=18)

        previews = ctk.CTkFrame(self)
        previews.pack(fill="both", expand=True, padx=12, pady=12)
        previews.grid_columnconfigure((0, 1), weight=1)
        previews.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(previews, text="Original First Frame", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, padx=10, pady=8)
        ctk.CTkLabel(previews, text="Processed First Frame", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=1, padx=10, pady=8)
        self.original_label = ctk.CTkLabel(previews, text="Load a video file")
        self.original_label.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.processed_label = ctk.CTkLabel(previews, text="Preview an operation")
        self.processed_label.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.update_controls()

    def _build_parameter_controls(self):
        super()._build_parameter_controls()

    def update_controls(self):
        for control in [
            self.brightness_control,
            self.contrast_control,
            self.posterize_control,
        ]:
            control.pack_forget()

        operation_name = self.operation_menu.get()
        if operation_name == "Brightness":
            self.brightness_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Contrast":
            self.contrast_control.pack(fill="x", padx=6, pady=4)
        elif operation_name == "Posterization":
            self.posterize_control.pack(fill="x", padx=6, pady=4)

    def _operation_function(self):
        operation_name = self.operation_menu.get()
        if operation_name in ["Brightness", "Contrast", "Posterization"]:
            return super()._operation_function()
        return self.operations[operation_name], operation_name

    def _video_info_text(self):
        if self.video_info is None:
            return ""
        return (
            f"Loaded video: {os.path.basename(self.video_info.path)} | "
            f"FPS: {self.video_info.fps:.2f} | "
            f"Size: {self.video_info.width} x {self.video_info.height} | "
            f"Frames: {self.video_info.frame_count}"
        )

    def load_video_file(self):
        path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.m4v"),
                ("MP4 files", "*.mp4"),
                ("AVI files", "*.avi"),
                ("MOV files", "*.mov"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self.video_path = path
            self.video_info = load_video_info(path)
            self.frame_folder = None
            self.processed_image = None
            self.original_image = read_first_video_frame(path)
            self._display_image(self.original_label, self.original_image, "original_preview")
            self.processed_label.configure(image=None, text="Preview an operation")
            self.status_label.configure(
                text=f"{self._video_info_text()} | Manual image operation will be applied frame by frame."
            )
        except Exception as error:
            messagebox.showerror("Video Error", str(error))

    def load_frame_folder(self):
        folder = filedialog.askdirectory(title="Select Folder of Image Frames")
        if not folder:
            return
        self.frame_folder = folder
        self.video_path = None
        self.video_info = None
        self.original_image = None
        self.processed_image = None
        self.original_label.configure(image=None, text="Preview first frame")
        self.processed_label.configure(image=None, text="Preview an operation")
        self.status_label.configure(
            text=f"Loaded frame folder: {folder} | Manual image operation will be applied to each frame."
        )

    def apply_operation(self):
        if not self.video_path and not self.frame_folder:
            messagebox.showwarning("Missing Video", "Please load a video file or frame folder first.")
            return
        try:
            operation, description = self._operation_function()
            if self.video_path:
                original, processed = preview_processed_video_frame(self.video_path, operation)
                status = f"{self._video_info_text()} | Previewed first frame with: {description}"
            else:
                original, processed = preview_processed_frame(self.frame_folder, operation)
                status = f"Previewed first folder frame with: {description}"
            self.original_image = original
            self.processed_image = processed
            self._display_image(self.original_label, original, "original_preview")
            self._display_image(self.processed_label, processed, "processed_preview")
            self.status_label.configure(text=status)
        except Exception as error:
            messagebox.showerror("Frame Error", str(error))

    def save_result(self):
        if not self.video_path:
            messagebox.showwarning("Missing Video", "Please load a video file first.")
            return
        output_path = filedialog.asksaveasfilename(
            title="Save Processed Video",
            defaultextension=".avi",
            filetypes=[("AVI video", "*.avi"), ("MP4 video", "*.mp4")],
        )
        if not output_path:
            return
        try:
            operation, description = self._operation_function()
            count = process_video_file(self.video_path, output_path, operation)
            messagebox.showinfo("Saved", f"Processed {count} video frames with {description} into:\n{output_path}")
        except Exception as error:
            messagebox.showerror("Save Error", str(error))

    def save_processed_frames(self):
        if not self.frame_folder:
            messagebox.showwarning("Missing Folder", "Please load a frame folder first.")
            return
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if not output_folder:
            return
        try:
            operation, description = self._operation_function()
            # The same selected parameter values are applied to every frame in the folder.
            count = process_frame_folder(self.frame_folder, output_folder, operation)
            messagebox.showinfo("Saved", f"Processed {count} frames with {description} into:\n{output_folder}")
        except Exception as error:
            messagebox.showerror("Save Error", str(error))


class MultiMediaProcessingStudio(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MultiMedia Processing Studio")
        self.geometry("980x720")
        self.minsize(900, 640)
        self._build_ui()

    def _build_ui(self):
        header = ctk.CTkFrame(self, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(
            header,
            text="MultiMedia Processing Studio",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(14, 2))
        ctk.CTkLabel(
            header,
            text="CPIT-380 educational GUI for direct pixel, sample, and frame manipulation",
        ).pack(anchor="w", padx=18, pady=(0, 14))

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)

        image_tab = tabs.add("Image Processing")
        color_tab = tabs.add("Color Transformations")
        geometric_tab = tabs.add("Geometric Transformations")
        audio_tab = tabs.add("Audio Processing")
        video_tab = tabs.add("Video Frame Processing")

        BaseImageTab(image_tab, IMAGE_OPERATIONS).pack(fill="both", expand=True)
        BaseImageTab(color_tab, COLOR_OPERATIONS).pack(fill="both", expand=True)
        GeometricTab(geometric_tab, GEOMETRIC_OPERATIONS).pack(fill="both", expand=True)
        AudioTab(audio_tab).pack(fill="both", expand=True)
        VideoFrameTab(video_tab).pack(fill="both", expand=True)
