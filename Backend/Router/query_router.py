from fastapi import APIRouter
from Backend.Controller.query_controller import (
    query_endpoint,
    query_endpoint_fullcontext,
    get_query_history_endpoint,
    delete_query_history_endpoint,
    clear_query_history_endpoint,
    get_queryable_sources,
    web_search_query_endpoint,
)

query_router = APIRouter()
query_router.add_api_route("/query", query_endpoint, methods=["GET"])
query_router.add_api_route("/query_fullcontext", query_endpoint_fullcontext, methods=["GET"])
query_router.add_api_route("/web_search", web_search_query_endpoint, methods=["GET"])
query_router.add_api_route("/all_queryable_sources", get_queryable_sources, methods=["GET"])
query_router.add_api_route("/history", get_query_history_endpoint, methods=["GET"])
query_router.add_api_route("/history/{query_id}", delete_query_history_endpoint, methods=["DELETE"])
query_router.add_api_route("/history", clear_query_history_endpoint, methods=["DELETE"])