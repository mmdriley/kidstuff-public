import aiohttp
import asyncio
import mimetypes
import pathlib

from tqdm.asyncio import tqdm

from urlfunctions import url_suffix


MAX_CONCURRENT_DOWNLOADS = 10


class DownloadItem:
    filename: pathlib.Path
    url: str

    def __init__(self, filename: str | pathlib.Path, url: str, add_suffix: bool = True):
        self.filename = pathlib.Path(filename)
        self.url = url

        if add_suffix and not self.filename.suffix:
            # add suffix from URL
            self.filename = self.filename.with_suffix(url_suffix(url))


# TODO:
# - may want a mode that double-checks photos already downloaded
#   (with what? etag?)

# Downloads some URLs to `target_path`. Skips items already downloaded.
# TODO: remove `target_path`, make it part of `items`.
async def download_urls(items: list[DownloadItem], target_path: pathlib.Path):
    target_path.mkdir(exist_ok=True)
    limiter = asyncio.Semaphore(MAX_CONCURRENT_DOWNLOADS)
    tasks = []

    async with aiohttp.ClientSession() as session:
        async def download_one(url: str, final_path: pathlib.Path):
            # Invariant: file exists at final path only if it was downloaded
            # successfully and completely.
            assert final_path.suffix != '.unfinished'
            temp_path = final_path.with_suffix('.unfinished')
            async with limiter, session.get(url) as response:
                # response.raise_for_status()
                if response.status >= 400:
                    print(f'FAIL: {url}')
                    return

                mimetype = response.headers.getone('content-type')
                assert final_path.suffix in mimetypes.guess_all_extensions(
                    mimetype), f"{url} shouldn't be {mimetype}"

                with temp_path.open('wb') as f:
                    f.write(await response.read())
                temp_path.rename(final_path)
                # print(final_path)

        for i in items:
            final_path = target_path.joinpath(i.filename)
            if final_path.exists():
                continue

            tasks += [asyncio.create_task(download_one(i.url, final_path))]

        await tqdm.gather(*tasks)
