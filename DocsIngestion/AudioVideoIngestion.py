import asyncio
import os
import tempfile
import threading
import uuid
from pathlib import Path as SyncPath

import ffmpeg

from Dbhelper.document_chunks_db_helper import save_chunks_to_database, delete_chunks_from_database
from Dbhelper.pdf_db_helper import save_content_to_database
from Embeddings.Embeddingmaker import embedder as embedding_maker
from Splitter.PdfSplitter import pdf_splitter

_whisper_model = None
_whisper_lock = threading.Lock()
_transcribe_semaphore = asyncio.Semaphore(1)


def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        with _whisper_lock:
            if _whisper_model is None:
                import torch
                from faster_whisper import WhisperModel

                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
                _whisper_model = WhisperModel("medium", device=device, compute_type=compute_type)
    return _whisper_model


def transcribe_audio_file(audio_path: str) -> str:
    model = get_whisper_model()
    segments, _info = model.transcribe(audio_path, beam_size=5)
    texts = [segment.text.strip() for segment in segments]
    return "\n".join(t for t in texts if t)


def extract_audio_from_video(video_path: str, audio_out_path: str) -> None:
    try:
        (
            ffmpeg
            .input(video_path)
            .output(audio_out_path, ac=1, ar=16000, format="wav")
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
    except ffmpeg.Error as e:
        stderr = e.stderr.decode(errors="ignore") if e.stderr else str(e)
        raise RuntimeError(f"ffmpeg failed to extract audio: {stderr[-500:]}") from e


def _write_temp_file_sync(file_bytes: bytes, suffix: str) -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    path = tmp.name
    try:
        with tmp:
            tmp.write(file_bytes)
    except Exception:
        _remove_files_sync(path)
        raise
    return path


def _remove_files_sync(*paths: str) -> None:
    for p in paths:
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass


async def _transcribe(audio_path: str) -> str:
    async with _transcribe_semaphore:
        return await asyncio.to_thread(transcribe_audio_file, audio_path)


async def read_text_from_audio(file) -> str:
    audio_bytes = await file.read()
    suffix = SyncPath(getattr(file, "filename", None) or "audio.wav").suffix or ".wav"
    tmp_path = await asyncio.to_thread(_write_temp_file_sync, audio_bytes, suffix)
    try:
        return await _transcribe(tmp_path)
    finally:
        await asyncio.to_thread(_remove_files_sync, tmp_path)


async def read_text_from_video(file) -> str:
    video_bytes = await file.read()
    suffix = SyncPath(getattr(file, "filename", None) or "video.mp4").suffix or ".mp4"
    tmp_video_path = await asyncio.to_thread(_write_temp_file_sync, video_bytes, suffix)
    tmp_audio_path = tmp_video_path + ".wav"
    try:
        await asyncio.to_thread(extract_audio_from_video, tmp_video_path, tmp_audio_path)
        return await _transcribe(tmp_audio_path)
    finally:
        await asyncio.to_thread(_remove_files_sync, tmp_video_path, tmp_audio_path)


async def build_and_save_index(chunks, content_id=None, feed_id=None) -> bool:
    documents = [chunk.page_content for chunk in chunks]
    embeddings = await asyncio.to_thread(embedding_maker.embed_documents, documents)
    success = await save_chunks_to_database(
        chunks=chunks,
        embeddings=embeddings,
        content_id=content_id,
        feed_id=feed_id,
    )
    if not success:
        raise RuntimeError("Failed to save document embeddings")
    return True


async def _ingest_transcript(text: str, name: str, doc_type: str):
    if not text or not text.strip():
        print(f"No speech detected in {doc_type} '{name}'")
        return None

    chunks = await asyncio.to_thread(pdf_splitter.split, text)
    if not chunks:
        print(f"Splitter produced no chunks for {doc_type} '{name}'")
        return None

    content_id = str(uuid.uuid4())
    chunks_saved = False
    try:
        await build_and_save_index(chunks, content_id=content_id, feed_id=None)
        chunks_saved = True
        database_saved = await save_content_to_database(
            name=name, content_id=content_id, doc_type=doc_type, chunks=len(chunks)
        )
        if database_saved:
            print(f"{doc_type.capitalize()} ingested and saved to database with ID: {content_id}")
            return content_id

        await delete_chunks_from_database(content_id=content_id)
        return None
    except Exception:
        if chunks_saved:
            try:
                await delete_chunks_from_database(content_id=content_id)
            except Exception as cleanup_error:
                print(f"Cleanup failed for {content_id}: {cleanup_error}")
        raise


async def ingestaudio(file, name: str):
    try:
        text = await read_text_from_audio(file)
        return await _ingest_transcript(text, name, "audio")
    except Exception as e:
        print(f"Error occurred while processing audio '{name}': {e}")
        return None


async def ingestvideo(file, name: str):
    try:
        text = await read_text_from_video(file)
        return await _ingest_transcript(text, name, "video")
    except Exception as e:
        print(f"Error occurred while processing video '{name}': {e}")
        return None