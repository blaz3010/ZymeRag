import asyncio
import pickle
from pathlib import Path


def _find_dir(uuid: str) -> Path:
    if not uuid or uuid in (".", "..") or any(c in uuid for c in ("/", "\\")):
        raise ValueError(f"Invalid UUID: {uuid!r}")
    for kind in ("Feed", "Content"):
        candidate = Path("Data") / kind / uuid
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"No folder found for UUID: {uuid}")


def _load_pickle(pickle_file_path: Path, uuid: str):
    if not pickle_file_path.exists():
        raise FileNotFoundError(f"Pickle file not found for UUID: {uuid}")
    with open(pickle_file_path, "rb") as f:
        return pickle.load(f)


async def path_checker(uuid: str) -> Path:
    return await asyncio.to_thread(_find_dir, uuid)


async def read_pickle_file(uuid: str):
    path = await path_checker(uuid)
    return await asyncio.to_thread(_load_pickle, path / "index.pkl", uuid)