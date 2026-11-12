from fastapi import APIRouter
from Backend.Controller.sources_controller import get_all_sources, show_all_chunks

sources_router = APIRouter()
sources_router.add_api_route("/all_sources", get_all_sources, methods=["GET"])
sources_router.add_api_route("/show_chunks", show_all_chunks, methods=["GET"])