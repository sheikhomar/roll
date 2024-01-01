from pathlib import Path
from typing import cast

import anyio
import streamlit as st
from roll.config import settings
from roll.data import ActiveOutOfOfficeSetting, AutoReplyRecord, DataRepository
from roll.email import AutoReplyHtmlCreator, OutlookAutoReplyClient
from roll.image import ImageOptimizer
from roll.io import FileDownloader
from roll.models import AutoReplyContentGenerator
from roll.utils import utcnow


class StreamlitApp:
    def __init__(
        self,
        data_dir: Path,
        ai_config_path: Path,
        html_template_file_path: Path,
        oof_data_dir: Path,
        outlook_login_name: str,
        outlook_password: str,
        outlook_account_name: str,
    ) -> None:
        self._db = DataRepository(data_dir=data_dir)
        self._ai_config_path = ai_config_path
        self._html_template_file_path = html_template_file_path
        self._oof_data_dir = oof_data_dir
        self._outlook_login_name = outlook_login_name
        self._outlook_password = outlook_password
        self._outlook_account_name = outlook_account_name

    @property
    def current_key(self) -> str:
        """Return the current key."""
        return cast(str, st.session_state.get("current_key", ""))

    @current_key.setter
    def current_key(self, value: str) -> None:
        """Set the current key."""
        st.session_state["current_key"] = value

    async def run(self) -> None:
        await self._setup_page_config()
        await self._build_sidebar()
        await self._build_main_content()

    async def _setup_page_config(self) -> None:
        """Set up any app settings, if any."""
        st.set_page_config(
            page_title="Roll",
            page_icon="👩‍💻",
            layout="wide",
            initial_sidebar_state="expanded",
        )

    async def _build_sidebar(self) -> None:
        """Build the sidebar of the app."""

        if st.sidebar.button(
            label="Create new auto-reply content", use_container_width=True
        ):
            await self._create_new_content()

        records = await self._db.get_all()
        if len(records) > 0:
            for record in records:
                cols = st.sidebar.columns(spec=[0.65, 0.25, 0.1])
                n_word_count = 0
                # created_ts = record.created_at.strftime("%Y-%m-%d %H:%M")
                if record.text is not None:
                    n_word_count = len(record.text.split())
                    cols[0].write(f"Message has {n_word_count} words")
                else:
                    cols[0].write("Message not generated yet.")
                if record.optimized_image_path is not None:
                    cols[1].image(str(record.optimized_image_path), width=65)
                else:
                    cols[1].write("❌")
                if cols[2].button(label="✏️", key=record.key, use_container_width=True):
                    self.current_key = record.key

    async def _build_main_content(self) -> None:
        """Build the main content of the app."""
        st.header("🥐 Roll: Auto Reply Content Generator", anchor=False)

        rec = await self._db.get(key=self.current_key)

        if rec is None:
            st.write("Please select a record on the sidebar or create a new record.")
        else:
            await self._render_navbar(record=rec)

            msg = "" if rec.text is None else rec.text

            col_left, col_right = st.columns(spec=[0.5, 0.5], gap="small")
            with col_left:
                rec.text = st.text_area(label="Message", value=msg, height=500)
                if rec.text != msg:
                    if rec.text_created_at is None:
                        rec.text_created_at = utcnow()
                    await self._db.save(record=rec)
                    st.toast("Message updated.")
            with col_right:
                st.write("Image")
                if rec.optimized_image_path is not None:
                    st.image(str(rec.optimized_image_path))
                else:
                    st.write("No image yet.")

    async def _render_navbar(self, record: AutoReplyRecord) -> None:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns(spec=4)

            if col1.button(label="Save content", use_container_width=True):
                await self._db.save(record=record)
                st.toast("Content saved.", icon="✅")

            if col2.button(label="Generate message", use_container_width=True):
                await self._generate_message(record=record)

            if col3.button(label="Generate image", use_container_width=True):
                if record.text is None:
                    st.toast("Please generate message first.", icon="⚠️")
                else:
                    await self._generate_image(record=record)

            if col4.button(label="Set out-of-office", use_container_width=True):
                if record.text is None:
                    st.toast("Please generate message first.", icon="⚠️")
                elif record.optimized_image_path is None:
                    st.toast("Please generate image first.", icon="⚠️")
                else:
                    await self._set_out_of_office(record=record)

    async def _create_new_content(self) -> None:
        """Create a new record."""
        new_record = await self._db.create(
            ai_config_path=self._ai_config_path,
            html_template_path=self._html_template_file_path,
        )
        self.current_key = new_record.key

    async def _generate_message(self, record: AutoReplyRecord) -> None:
        """Generate message."""

        generator = AutoReplyContentGenerator(
            config_file_path=record.ai_config_path,
            output_dir=record.dir,
            verbose=True,
        )

        message = await generator.generate_message()
        record.text = message
        record.text_created_at = utcnow()
        await self._db.save(record=record)

    async def _generate_image(self, record: AutoReplyRecord) -> None:
        """Generate image."""

        generator = AutoReplyContentGenerator(
            config_file_path=record.ai_config_path,
            output_dir=record.dir,
            verbose=True,
        )

        # Generate image
        auto_reply_message = record.text
        assert auto_reply_message is not None
        image_url = await generator.generate_image(
            auto_reply_message=auto_reply_message,
        )
        record.image_url = image_url
        record.image_created_at = utcnow()
        await self._db.save(record=record)

        # Download image
        downloader = FileDownloader(
            output_dir=record.dir, verify_ssl=False, verbose=True
        )
        try:
            img_path = await downloader.download_one(url=image_url)
        finally:
            await downloader.close()
        record.original_image_path = img_path
        await self._db.save(record=record)

        # Optimize image
        optimizer = ImageOptimizer(max_width=512, quantize=False, image_quality=80)
        img_optimized_path = optimizer.run(input_path=img_path)
        record.optimized_image_path = img_optimized_path
        await self._db.save(record=record)

    async def _set_out_of_office(self, record: AutoReplyRecord) -> None:
        """Set out-of-office."""

        if record.text is None:
            st.toast("Please generate message first.", icon="⚠️")
            return

        if record.optimized_image_path is None:
            st.toast("Please generate image first.", icon="⚠️")
            return

        # Create email body
        email_creator = AutoReplyHtmlCreator(
            template_file_path=self._html_template_file_path
        )
        email_file_path = record.dir / "auto-reply.html"
        assert record.text is not None
        assert record.optimized_image_path is not None
        email_text = await email_creator.run(
            message=record.text,
            image_file_path=record.optimized_image_path,
            output_path=email_file_path,
        )
        print(f"Auto-reply email text:\n{email_text}\n")

        # Backup current out-of-office settings before setting new one
        utcnow_str = utcnow().strftime("%Y-%m-%d_%H-%M-%S-%f")
        outlook_old_settings_path = (
            self._oof_data_dir / "backups" / f"{utcnow_str}-outlook-oof.json"
        )
        outlook_old_settings_path.parent.mkdir(parents=True, exist_ok=True)
        outlook_oof = OutlookAutoReplyClient(
            login_name=self._outlook_login_name,
            password=self._outlook_password,
            account_name=self._outlook_account_name,
        )
        print(
            (
                f"Backing up Outlook's current out-of-office settings to "
                f"{outlook_old_settings_path}..."
            )
        )
        await outlook_oof.backup_to_json_file(output_path=outlook_old_settings_path)

        # Set new out-of-office settings
        print("Setting internal auto-reply message...")
        await outlook_oof.set_internal_reply(html_content=email_text)

        # Save current out-of-office settings
        active_oof = ActiveOutOfOfficeSetting(
            created_at=utcnow(),
            record_key=record.key,
            generated_message=record.text,
            original_generated_image_path=record.original_image_path,
            optimized_generated_image_path=record.optimized_image_path,
            email_text=email_text,
            outlook_old_settings_path=outlook_old_settings_path,
        )
        await active_oof.save(output_dir=self._oof_data_dir)

        # Done
        st.toast("Out-of-office message set succesfully", icon="✅")


async def main() -> None:
    """Main entry point of the UI."""
    app = StreamlitApp(
        data_dir=Path("data/repository"),
        ai_config_path=Path("config/auto-reply-content-gen.aiconfig.json"),
        html_template_file_path=Path("config/auto-reply-template.html"),
        oof_data_dir=Path("data/oof"),
        outlook_login_name=settings.LOGIN,
        outlook_password=settings.PASSWORD,
        outlook_account_name=settings.ACCOUNT_NAME,
    )
    await app.run()


if __name__ == "__main__":
    anyio.run(main)
