import json
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import cast

import aiofiles
from exchangelib import Account, Credentials, OofSettings
from exchangelib.ewsdatetime import EWSDateTime


class OutlookAutoReplyClient:
    """Represents a client for interacting with Outlook's out-of-office settings."""

    def __init__(self, login_name: str, password: str, account_name: str) -> None:
        """Initializes a new instance of the OutlookAutoReplyClient class.

        Args:
            login_name (str): The login name of the Outlook account.
            password (str): The password of the Outlook account.
            account_name (str): The name of the Outlook account.

        """
        credentials = Credentials(username=login_name, password=password)
        self._account = Account(
            account_name, credentials=credentials, autodiscover=True
        )

    async def backup_to_json_file(self, output_path: Path) -> None:
        """Backup Outlook's current out-of-office settings to disk.

        Args:
            output_path (Path): The location where to store the backup.
        """
        oof = cast(OofSettings, self._account.oof_settings)
        start_at = cast(EWSDateTime, oof.start)
        end_at = cast(EWSDateTime, oof.end)
        settings = {
            "state": oof.state,
            "start": start_at.ewsformat(),
            "end": end_at.ewsformat(),
            "external_audience": oof.external_audience,
            "internal_reply": oof.internal_reply,
            "external_reply": oof.external_reply,
        }
        # Save settings to disk as JSON
        async with aiofiles.open(output_path, "w") as file:
            json_content = json.dumps(settings, indent=2)
            await file.write(json_content)

    async def set_internal_reply(self, html_content: str) -> None:
        """Sets the internal auto-reply message for a month.

        Args:
            html_content (str): The message to set as the internal auto-reply.
        """
        start_at = datetime.now(tz=timezone.utc) - timedelta(days=1)
        end_at = datetime.now(tz=timezone.utc) + timedelta(days=5)

        print(f"Setting internal auto-reply message from {start_at} to {end_at}...")
        self._account.oof_settings = OofSettings(
            state=OofSettings.ENABLED,
            # https://learn.microsoft.com/en-us/exchange/client-developer/web-service-reference/externalaudience
            # The external_audience determines to whom external Out of Office messages are sent:
            # - Known: External Out of Office messages are sent only to recipients who are in the user's Contacts folder.
            # - All: External Out of Office messages are sent to all recipients.
            # - None: No external Out of Office messages are sent.
            external_audience="None",
            internal_reply=html_content,
            external_reply="-",  # Cannot be empty string or None!
            start=start_at,
            end=end_at,
        )


class AutoReplyHtmlCreator:
    """Represents a class that creates the HTML for an auto-reply message."""

    def __init__(self, template_file_path: Path) -> None:
        """Initializes a new instance of the AutoReplyHtmlCreator class.

        Args:
            template_file_path (Path): The path to the HTML template to use.
        """
        self._template_file_path = template_file_path

        if not template_file_path.exists():
            raise ValueError(f"File {template_file_path} not found")

    async def run(self, message: str, image_file_path: Path, output_path: Path) -> str:
        """Creates the HTML for an auto-reply message.

        Args:
            message (str): The message to include in the auto-reply.
            image_file_path (Path): The path to the image to include in the auto-reply.
            output_path (Path): The path to save the HTML to.

        Returns:
            str: The HTML for the auto-reply message.
        """
        async with aiofiles.open(self._template_file_path, "r") as file:
            template = await file.read()

        async with aiofiles.open(image_file_path, "rb") as file:
            image_data = await file.read()
            image_base64 = b64encode(image_data).decode("utf-8")

        message_in_html = message.replace("\n\n", "</p><p>")
        message_in_html = message_in_html.replace("\n", "<br/>")
        message_in_html = f"<p>{message_in_html}</p>"

        html = template.replace("{{CONTENT}}", message_in_html)
        html = html.replace("{{IMAGE_BASE64}}", image_base64)
        html = html.replace("{{IMAGE_CONTENT_TYPE}}", "image/jpeg")

        async with aiofiles.open(output_path, "w") as file:
            await file.write(html)

        return html
