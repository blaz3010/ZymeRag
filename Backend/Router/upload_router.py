from fastapi import APIRouter
from Backend.Controller.upload_controller import (
    upload_pdf,
    upload_docx,
    upload_image,
    upload_csv,
    upload_audio,
    upload_video,
    upload_website,
    upload_raw_text,
    upload_presentation,
    replace_content,
)

upload_router = APIRouter()
upload_router.add_api_route("/upload_pdf", upload_pdf, methods=["POST"])
upload_router.add_api_route("/upload_docx", upload_docx, methods=["POST"])
upload_router.add_api_route("/upload_image", upload_image, methods=["POST"])
upload_router.add_api_route("/upload_csv", upload_csv, methods=["POST"])
upload_router.add_api_route("/upload_audio", upload_audio, methods=["POST"])
upload_router.add_api_route("/upload_video", upload_video, methods=["POST"])
upload_router.add_api_route("/upload_website", upload_website, methods=["POST"])
upload_router.add_api_route("/upload_raw_text", upload_raw_text, methods=["POST"])
upload_router.add_api_route("/replace_content", replace_content, methods=["POST"])
upload_router.add_api_route("/upload_presentation", upload_presentation, methods=["POST"])