from fastapi import APIRouter
from Backend.Controller.delete_controller import delete_id
from Backend.Controller.upload_controller import *
delete_router = APIRouter()
delete_router.add_api_route("/delete_content", delete_id, methods=["DELETE"])