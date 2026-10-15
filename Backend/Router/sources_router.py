from fastapi import APIRouter, Depends
from Backend.Middleware.auth import auth_middleware
from Backend.Controller.sources_controller import get_my_sources, get_all_sources

sources_router = APIRouter()
sources_router.add_api_route("/my_sources", get_my_sources, methods=["GET"], dependencies=[Depends(auth_middleware)])
sources_router.add_api_route("/all_sources", get_all_sources, methods=["GET"], dependencies=[Depends(auth_middleware)])

