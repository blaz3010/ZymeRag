from fastapi import APIRouter, Depends
from Backend.Controller.query_controller import (
    query_endpoint,
    query_endpoint_fullcontext,
    user_query_endpoint,
    get_query_history_endpoint,
    delete_query_history_endpoint,
    clear_query_history_endpoint,
    get_user_queryable_sources,
    get_all_queryable_sources,
)
from Backend.Middleware.auth import auth_middleware

query_router = APIRouter()
query_router.add_api_route("/query", query_endpoint, methods=["GET"])
query_router.add_api_route("/query_fullcontext", query_endpoint_fullcontext, methods=["GET"])
query_router.add_api_route("/user_query", user_query_endpoint, methods=["POST"], dependencies=[Depends(auth_middleware)])
query_router.add_api_route("/my_queryable_sources", get_user_queryable_sources, methods=["GET"], dependencies=[Depends(auth_middleware)])
query_router.add_api_route("/all_queryable_sources", get_all_queryable_sources, methods=["GET"], dependencies=[Depends(auth_middleware)])
query_router.add_api_route("/history", get_query_history_endpoint, methods=["GET"], dependencies=[Depends(auth_middleware)])
query_router.add_api_route("/history/{query_id}", delete_query_history_endpoint, methods=["DELETE"], dependencies=[Depends(auth_middleware)])
query_router.add_api_route("/history", clear_query_history_endpoint, methods=["DELETE"], dependencies=[Depends(auth_middleware)])