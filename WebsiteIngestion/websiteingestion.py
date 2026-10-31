import asyncio
import sys
import uuid

from playwright.async_api import async_playwright
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    CacheMode,
)
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from Dbhelper.document_chunks_db_helper import (
    save_chunks_to_database,
    delete_chunks_from_database,
)
from Dbhelper.website_db_helper import (
    save_website_to_database,
    update_website_last_crawled,
)
from Splitter.WebsiteSplitter import WebsiteTextSplitter
from Embeddings.Embeddingmaker import embedder as embedding_maker

markdown_generator = DefaultMarkdownGenerator(
    content_filter=PruningContentFilter(threshold=0.5)
)
website_splitter = WebsiteTextSplitter()

config = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    excluded_tags=["nav", "footer", "header", "style", "script"],
    exclude_external_links=False,
    remove_overlay_elements=True,
    remove_consent_popups=True,
    wait_until="domcontentloaded",
    scan_full_page=True,
    markdown_generator=markdown_generator,
)

# Caps how many browsers run at once.
_CRAWL_LIMIT = asyncio.Semaphore(2)


# ---------- loop handling ----------

def _run_in_proactor(coro_fn, *args):
    # Runs in a worker thread, so no loop is running there yet.
    # Only called on Windows, where ProactorEventLoop exists.
    return asyncio.run(coro_fn(*args), loop_factory=asyncio.ProactorEventLoop)


async def _run_with_subprocess_support(coro_fn, *args):
    """
    Playwright / crawl4ai spawn a browser subprocess, which on Windows needs
    ProactorEventLoop. If the current loop is a Selector loop (uvicorn with
    --reload or workers), run the coroutine on a fresh Proactor loop in a
    worker thread. Otherwise run it on the current loop.
    """
    loop = asyncio.get_running_loop()
    print("Active event loop:", type(loop).__name__)

    if sys.platform != "win32" or isinstance(loop, asyncio.ProactorEventLoop):
        return await coro_fn(*args)

    return await asyncio.to_thread(_run_in_proactor, coro_fn, *args)


# ---------- crawling ----------

async def _crawl_impl(url: str):
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url, config=config)
    if result.success:
        print("Successfully crawled the website.")
        return result.markdown.fit_markdown
    print("Failed to crawl the website.")
    return None


async def _crawl2_impl(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_load_state("load")
            return await page.locator("body").inner_text()
        finally:
            await browser.close()


async def website_crawl(url: str):
    try:
        async with _CRAWL_LIMIT:
            return await _run_with_subprocess_support(_crawl_impl, url)
    except Exception as e:
        print(f"Error occurred while crawling the website: {e!r}")
        return None


async def website_crawl2(url: str):
    async with _CRAWL_LIMIT:
        return await _run_with_subprocess_support(_crawl2_impl, url)


async def _get_markdown(url: str):
    markdown = await website_crawl(url)
    if not markdown or not markdown.strip():
        try:
            markdown = await website_crawl2(url)
        except Exception as e:
            print(f"Fallback crawl failed for {url}: {e!r}")
            return None
    if not markdown or not markdown.strip():
        return None
    return markdown


# ---------- chunk + embed ----------

async def _split_and_embed(markdown: str):
    chunks = await asyncio.to_thread(website_splitter.split, markdown)
    if not chunks:
        return None, None
    documents = [chunk.page_content for chunk in chunks]
    embeddings = await asyncio.to_thread(
        embedding_maker.embed_documents, documents
    )
    return chunks, embeddings


# ---------- public API ----------

async def ingest_website(url: str):
    try:
        markdown = await _get_markdown(url)
        if markdown is None:
            print("No markdown content to process.")
            return None

        chunks, embeddings = await _split_and_embed(markdown)
        if not chunks:
            print(f"Splitter produced no chunks for {url}")
            return None

        feed_id = str(uuid.uuid4())

        # The feeds row goes first: document_chunks.feed_id is a foreign key
        # to feeds, so chunks can't be inserted before it exists.
        database_saved = await save_website_to_database(
            url=url, feed_id=feed_id, chunks=len(chunks)
        )
        if not database_saved:
            return None

        chunks_saved = await save_chunks_to_database(
            chunks=chunks,
            embeddings=embeddings,
            feed_id=feed_id,
        )
        if not chunks_saved:
            print(f"Failed to save chunks for {url}; feed row {feed_id} is orphaned")
            return None

        print(f"Website {url} ingested and saved to database with ID: {feed_id}")
        return feed_id

    except Exception as e:
        print(f"Error occurred while ingesting website: {e!r}")
        return None


async def update_website(url: str, id: str):
    try:
        markdown = await _get_markdown(url)
        if markdown is None:
            print("No markdown content to process.")
            return None

        chunks, embeddings = await _split_and_embed(markdown)
        if not chunks:
            print(f"Splitter produced no chunks for {url}")
            return None

        # save_chunks_to_database replaces the old chunks and inserts the new
        # ones in one transaction, so the temp-folder swap isn't needed.
        chunks_saved = await save_chunks_to_database(
            chunks=chunks,
            embeddings=embeddings,
            feed_id=id,
        )
        if not chunks_saved:
            return None

        await update_website_last_crawled(feed_id=id, chunks=len(chunks))
        print(f"Website {url} updated and saved to database with ID: {id}")
        return id

    except Exception as e:
        print(f"Error occurred while updating website: {e!r}")
        return None


async def delete_website(id: str) -> bool:
    try:
        deleted = await delete_chunks_from_database(feed_id=id)
        if deleted:
            print(f"Feed with ID: {id} deleted successfully.")
            return True
        print(f"Feed with ID: {id} could not be deleted.")
        return False
    except Exception as e:
        print(f"Error occurred while deleting Feed: {e!r}")
        return False