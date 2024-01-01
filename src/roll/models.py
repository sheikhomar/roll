from pathlib import Path

from aiconfig import AIConfigRuntime, InferenceOptions


class AutoReplyContentGenerator:
    """Represents a class that generates content for auto-reply messages."""

    def __init__(self, config_file_path: Path, output_dir: Path, verbose: bool) -> None:
        """Initializes a new instance of the AutoReplyContentGenerator class.

        Args:
            config_file_path (Path): The path to the AI Config file to use.
            output_dir (Path): The directory to save outputs to.
            verbose (bool): Whether to print debug messages to stdout.
        """
        if not config_file_path.exists():
            raise ValueError(f"File {config_file_path} not found")

        self._output_path: Path = output_dir / config_file_path.name
        self._runtime: AIConfigRuntime = AIConfigRuntime.load(config_file_path)
        self._verbose = verbose

    async def generate_message(self) -> str:
        """Generates an auto-reply message.

        Returns:
            str: The generated message.
        """
        inference_options = InferenceOptions(stream=False)

        if self._verbose:
            print("Running inference for prompt 'generate-text'...")

        auto_reply_message = await self._runtime.run_and_get_output_text(
            prompt_name="generate-text",
            options=inference_options,
        )
        self._save_outputs()

        print(f"Generated auto-reply message:\n{auto_reply_message}\n")
        return auto_reply_message

    async def generate_image(self, auto_reply_message: str) -> str:
        """Generates an image to accompany the given auto-reply message.

        Args:
            auto_reply_message (str): The auto-reply message to use as inspiration for the image generation.

        Returns:
            str: The URL of the generated image.
        """
        if self._verbose:
            print("Running inference for prompt 'generate-dall-e-prompt'...")

        inference_options = InferenceOptions(stream=False)
        dall_e_prompt = await self._runtime.run_and_get_output_text(
            prompt_name="generate-dall-e-prompt",
            options=inference_options,
            params={
                "auto_reply_message": auto_reply_message,
            },
        )
        self._save_outputs()

        if self._verbose:
            print(f"Generated prompt for DALL-E:\n{dall_e_prompt}\n")
            print("Running inference for prompt 'generate-image'...")

        image_url = await self._runtime.run_and_get_output_text(
            prompt_name="generate-image",
            options=inference_options,
            params={
                "dall_e_prompt": dall_e_prompt,
            },
        )
        self._save_outputs()

        if self._verbose:
            print(f"Generated image URL:\n{image_url}\n")

        return image_url

    def _save_outputs(self) -> None:
        """Saves the outputs of the models to a JSON file."""
        self._runtime.save(
            json_config_filepath=str(self._output_path),
            include_outputs=True,
        )
