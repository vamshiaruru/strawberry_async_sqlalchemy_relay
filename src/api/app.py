"""Main api module for the app"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter
from api.exception_handler import default_exception_handler

from api.settings import get_settings
from api.routers import resource
from api.graphql.schema import schema
from api.graphql.core.context import get_context_for_fastapi

settings = get_settings()

app = FastAPI(
    title="App",
    # for dev
    debug=os.getenv("DEBUG", default="0") == "1",
)
app.add_exception_handler(Exception, default_exception_handler)

# add middlewares
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["OPTIONS", "GET", "POST"],
)
# add any event handlers if needed

# add routes
app.include_router(resource.router, prefix="/resources", tags=["Resources"])

# garphql route
graphql_app = GraphQLRouter(schema, context_getter=get_context_for_fastapi)
app.include_router(graphql_app, prefix="/graphql")