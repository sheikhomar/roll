import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from pydantic import BaseModel, Field

from roll.utils import utcnow

RECORD_FILE_NAME = "record.json"


def format_datetime(dt: Optional[datetime]) -> Optional[str]:
    """Format datetime."""
    if dt is None:
        return None
    return dt.isoformat()


def format_path(path: Optional[Path]) -> Optional[str]:
    """Format path."""
    if path is None:
        return None
    return str(path)


def parse_datetime(dt: Optional[str]) -> Optional[datetime]:
    """Parse datetime."""
    if dt is None:
        return None
    return datetime.fromisoformat(dt)


def parse_path(path: Optional[str]) -> Optional[Path]:
    """Parse path."""
    if path is None:
        return None
    return Path(path)


class AutoReplyRecord:
    def __init__(
        self,
        key: str,
        dir: Path,
        ai_config_path: Path,
        html_template_path: Path,
        created_at: Optional[datetime] = None,
        text: Optional[str] = None,
        text_created_at: Optional[datetime] = None,
        image_created_at: Optional[datetime] = None,
        image_url: Optional[str] = None,
        original_image_path: Optional[Path] = None,
        optimized_image_path: Optional[Path] = None,
    ) -> None:
        # Immutable attributes
        self._key = key
        self._dir = dir
        self._ai_config_path = ai_config_path
        self._html_template_path = html_template_path
        self._created_at: datetime = (
            datetime.now(tz=timezone.utc) if created_at is None else created_at
        )

        # Mutable attributes
        self.text: Optional[str] = text
        self.text_created_at: Optional[datetime] = text_created_at
        self.image_created_at: Optional[datetime] = image_created_at
        self.image_url: Optional[str] = image_url
        self.original_image_path: Optional[Path] = original_image_path
        self.optimized_image_path: Optional[Path] = optimized_image_path

    @property
    def key(self) -> str:
        return self._key

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def dir(self) -> Path:
        return self._dir

    @property
    def ai_config_path(self) -> Path:
        return self._ai_config_path

    @property
    def html_template_path(self) -> Path:
        return self._html_template_path

    def to_json(self, indent: int = 2) -> str:
        """Dump the model as JSON."""
        return json.dumps(
            obj=self.to_dict(),
            indent=indent,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the model to a dict."""
        return {
            "key": self.key,
            "created_at": format_datetime(self.created_at),
            "dir": str(self.dir),
            "ai_config_path": str(self.ai_config_path),
            "html_template_path": str(self.html_template_path),
            "text": self.text,
            "text_created_at": format_datetime(self.text_created_at),
            "image_created_at": format_datetime(self.image_created_at),
            "image_url": self.image_url,
            "original_image_path": format_path(self.original_image_path),
            "optimized_image_path": format_path(self.optimized_image_path),
        }

    @classmethod
    def from_json(cls, json_data: str) -> "AutoReplyRecord":
        """Load the model from JSON."""
        return cls.from_dict(json.loads(json_data))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoReplyRecord":
        """Load the model from a dict."""
        return cls(
            key=data["key"],
            created_at=parse_datetime(data["created_at"]),
            dir=Path(data["dir"]),
            ai_config_path=Path(data["ai_config_path"]),
            html_template_path=Path(data["html_template_path"]),
            text=data["text"],
            text_created_at=parse_datetime(data["text_created_at"]),
            image_created_at=parse_datetime(data["image_created_at"]),
            image_url=data["image_url"],
            original_image_path=parse_path(data["original_image_path"]),
            optimized_image_path=parse_path(data["optimized_image_path"]),
        )


class DataRepository:
    """Represents a file-based data repository."""

    def __init__(self, data_dir: Path) -> None:
        """Initializes a new instance of the DataRepository class.

        Args:
            data_dir (Path): The directory to store data in.
        """
        self._data_dir = data_dir
        if not self._data_dir.exists():
            self._data_dir.mkdir(parents=True, exist_ok=True)

    async def get_keys(self) -> List[str]:
        """Returns the keys of existing records."""
        file_names = [
            file_path.name
            for file_path in self._data_dir.iterdir()
            if file_path.is_dir()
        ]
        return file_names

    async def get_all(self) -> List[AutoReplyRecord]:
        """Returns existing records.

        Returns:
            List[AutoReplyRecord]: A list of all records order by created time.
        """
        keys = await self.get_keys()
        records = [await self.get(key=key) for key in keys]
        sorted_records = sorted(records, key=lambda r: r.created_at, reverse=True)
        return list(sorted_records)

    async def create(
        self, ai_config_path: Path, html_template_path: Path
    ) -> AutoReplyRecord:
        """Create a new record.

        Args:
            ai_config_path (Path): The path to the AI Config file.
            html_template_path (Path): The path to the HTML template file.

        Returns:
            AutoReplyRecord: The newly created record.
        """
        key = uuid.uuid4().hex

        dir_path = self._data_dir / key
        dir_path.mkdir(parents=True, exist_ok=True)

        new_ai_config_path = dir_path / ai_config_path.name
        shutil.copyfile(src=ai_config_path, dst=new_ai_config_path)

        new_html_template_path = dir_path / html_template_path.name
        shutil.copyfile(src=html_template_path, dst=new_html_template_path)

        record = AutoReplyRecord(
            key=key,
            dir=dir_path,
            ai_config_path=new_ai_config_path,
            html_template_path=new_html_template_path,
        )

        await self.save(record=record)
        return record

    async def save(self, record: AutoReplyRecord) -> None:
        """Save the given record to disk.

        Args:
            record (AutoReplyRecord): The record to save.
        """
        file_path = record.dir / RECORD_FILE_NAME
        async with aiofiles.open(file_path, mode="w") as f:
            await f.write(record.to_json(indent=2))

    async def get(self, key: str) -> Optional[AutoReplyRecord]:
        """Finds a record by its key.

        Args:
            key (str): The key to search for.

        Returns:
            Optional[AutoReplyRecord]: The record if found, None otherwise.
        """
        file_path = self._data_dir / key / RECORD_FILE_NAME
        if not file_path.exists():
            return None
        async with aiofiles.open(file_path, mode="r") as f:
            json_data = await f.read()
        return AutoReplyRecord.from_json(json_data=json_data)


class ActiveOutOfOfficeSetting(BaseModel):
    """Represents the active out-of-office setting."""

    created_at: datetime = Field(...)
    """The date and time when the OOF was set."""

    record_key: str = Field(...)
    """The key of the AutoReplyRecord that generating this OOF."""

    generated_message: str = Field(...)
    """The generated message."""

    original_generated_image_path: Path = Field(...)
    """The path to the original generated image."""

    optimized_generated_image_path: Path = Field(...)
    """The path to the optimized generated image."""

    email_text: str = Field(...)
    """The email text."""

    outlook_old_settings_path: Path = Field(...)
    """The location of the backup of the old Outlook OOF settings."""

    async def save(self, output_dir: Path) -> None:
        """Save the active out-of-office setting to disk.

        Args:
            output_dir (Path): The output directory.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "active-oof.json"

        # Backup current active out-of-office settings.
        if output_path.exists():
            utcnow_str = utcnow().strftime("%Y-%m-%d_%H-%M-%S-%f")
            backup_path = output_dir / f"{utcnow_str}-active-oof.json"
            shutil.copyfile(src=output_path, dst=backup_path)

        async with aiofiles.open(output_path, mode="w") as f:
            await f.write(self.model_dump_json(indent=2))
