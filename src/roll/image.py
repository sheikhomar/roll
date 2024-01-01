from pathlib import Path

from PIL import Image


class ImageOptimizer:
    def __init__(self, max_width: int, quantize: bool, image_quality: int) -> None:
        """Initializes a new instance of the ImageOptimizer class.

        Args:
            max_width (int): The maximum width of the image in pixels.
            quantize (bool): Whether to quantize the image to reduce file size.
            image_quality (int): The quality of the image when saving it to disk from 1 to 100.
        """
        self._max_width = max_width
        self._quantize = quantize
        self._image_quality = image_quality

    def run(self, input_path: Path) -> Path:
        """Optimizes an image and stores the image on disk.

        Args:
            input_path (Path): The path to the image to optimize.

        Returns:
            Path: The location of the optimized image on disk.
        """
        output_path = input_path.parent / f"{input_path.stem}-optimized.jpg"

        img = Image.open(input_path)
        img = img.convert("RGB")

        img.thumbnail(size=(self._max_width, self._max_width), resample=Image.LANCZOS)

        if self._quantize:
            # Quantize image to reduce file size. Pillow converts the image to a
            # palette image with at most 256 colors. This is done by storing 1 byte for
            # each pixel instead of storing 3 bytes for R, G and B for each pixel.
            # The single byte is used to store the index into the palette.
            img = img.quantize()

            if output_path.suffix.lower() in [".jpg", ".jpeg"]:
                # Convert to RGB before saving to JPEG to avoid errors.
                img = img.convert("RGB")

        img.save(output_path, optimize=True, quality=self._image_quality)
        return output_path
