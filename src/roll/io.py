from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import aiofiles
import aiohttp
from tqdm.asyncio import tqdm_asyncio


class FileDownloader:
    """Represents a class that downloads files."""

    def __init__(
        self,
        output_dir: Path,
        verify_ssl: bool,
        verbose: bool,
        download_chunk_size: int = 1024,
    ) -> None:
        """Initializes a new instance of the FileDownloader class.

        Args:
            output_dir (Path): The directory to save downloaded files to.
            verify_ssl (bool): Whether to verify SSL certificates when downloading files.
            download_chunk_size (int, optional): The size of each chunk to download. Defaults to 1024.
        """
        self._http = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=verify_ssl)  # type: ignore
        )
        self._chunk_size = download_chunk_size

        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._verbose = verbose

    async def download_one(
        self, url: str, local_file_name: Optional[str] = None
    ) -> Path:
        """Downloads an file from a URL and stores it on local disk.

        Args:
            url (str): The URL to download the file from.
            local_file_name (Optional[str], optional): The name of the file to save the downloaded file to. Defaults to None.

        Returns:
            Path: The location of the downloaded file in the local disk.
        """
        file_path = self._get_local_file_path(url=url, file_name=local_file_name)
        async with self._http.get(url=url) as response:
            if response.status != 200:
                raise Exception(f"Failed to download file: {response.status}")

            if self._verbose:
                print(f"Downloading file from {url} to {file_path}...")

            total_size = int(response.headers.get("content-length", 0))
            with tqdm_asyncio(
                total=total_size, unit="B", unit_scale=True, desc="Downloading"
            ) as progress_bar:
                async with aiofiles.open(file_path, "wb") as file:
                    async for data in response.content.iter_chunked(self._chunk_size):
                        await file.write(data)
                        progress_bar.update(len(data))
        return file_path

    async def close(self) -> None:
        """Closes the HTTP session."""
        await self._http.close()

    def _get_local_file_path(self, url: str, file_name: Optional[str]) -> Path:
        """Gets the path to save the downloaded file to.

        Args:
            file_name (Optional[str]): The name of the file to save the downloaded file to. Defaults to None.

        Returns:
            Path: The path to save the downloaded file to.
        """
        if file_name is None:
            file_name = unquote(urlparse(url).path.split("/")[-1])
        file_path = self._output_dir / file_name
        if file_path.exists():
            # raise Exception(f"File {file_path} already downloaded.")
            print(f"WARNING. File {file_path} already exists. Overwritting...")
        return file_path
