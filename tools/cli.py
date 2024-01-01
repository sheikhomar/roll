from pathlib import Path

import anyio
from roll.config import settings
from roll.email import AutoReplyHtmlCreator, OutlookAutoReplyClient
from roll.image import ImageOptimizer
from roll.io import FileDownloader
from roll.models import AutoReplyContentGenerator
from roll.utils import utcnow


async def main() -> None:
    run_id = utcnow().strftime("%Y-%m-%d_%H-%M-%S-%f")
    output_dir = Path(f"data/cli-runs/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    config_file_path = Path("config/auto-reply-content-gen.aiconfig.json")
    generator = AutoReplyContentGenerator(
        config_file_path=config_file_path,
        output_dir=output_dir,
        verbose=True,
    )

    message = await generator.generate_message()
    image_url = await generator.generate_image(auto_reply_message=message)

    print(f"Generated image URL:\n{image_url}\n")

    downloader = FileDownloader(output_dir=output_dir, verify_ssl=False, verbose=True)
    try:
        img_path = await downloader.download_one(url=image_url)
    finally:
        await downloader.close()

    optimizer = ImageOptimizer(max_width=512, quantize=False, image_quality=80)
    img_optimized_path = optimizer.run(input_path=img_path)
    print(f"Optimized image saved to {img_optimized_path}")

    email_creator = AutoReplyHtmlCreator(
        template_file_path=Path("config/auto-reply-template.html")
    )
    email_file_path = output_dir / "auto-reply.html"
    email_text = await email_creator.run(
        message=message,
        image_file_path=img_optimized_path,
        output_path=email_file_path,
    )

    print(f"Auto-reply email text:\n{email_text}\n")

    outlook_old_settings_path = output_dir / "outlook-oof-settings-backup.json"
    outlook_oof = OutlookAutoReplyClient(
        login_name=settings.LOGIN,
        password=settings.PASSWORD,
        account_name=settings.ACCOUNT_NAME,
    )
    print(
        f"Backing up Outlook's current out-of-office settings to {outlook_old_settings_path}..."
    )
    await outlook_oof.backup_to_json_file(output_path=outlook_old_settings_path)

    print("Setting internal auto-reply message...")
    await outlook_oof.set_internal_reply(html_content=email_text)

    print("Done.")


if __name__ == "__main__":
    anyio.run(main)
