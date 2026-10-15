import os
from dotenv import load_dotenv
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )
load_dotenv()

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from Backend.Router.upload_router import upload_router
from Backend.Router.delete_router import delete_router
from Backend.Router.user_router import user_router
from Backend.Router.query_router import query_router
from Backend.Router.sources_router import sources_router

app = FastAPI(title="ZymeRag Backend API", description="API for ZymeRag Backend", version="1.0.0")

cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix="/upload", tags=["Upload"])
app.include_router(delete_router, prefix="/delete", tags=["Delete"])
app.include_router(query_router, prefix="/query", tags=["Query"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(sources_router, prefix="/sources", tags=["Sources"])

static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

@app.get("/favicon.ico")
@app.get("/favicon.svg")
async def get_favicon():
    fav_svg = os.path.join(static_dir, "favicon.svg")
    if os.path.exists(fav_svg):
        return FileResponse(fav_svg, media_type="image/svg+xml")
    return {"status": "not found"}

@app.get("/")
@app.get("/ui")
async def read_ui():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return {"message": "ZymeRag API is running. Testing UI index.html not found."}