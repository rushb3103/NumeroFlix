from fastapi import APIRouter

from app.api import auth, collections, library, metadata, movies, streaming, tags

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(movies.router)
api_router.include_router(tags.router)
api_router.include_router(collections.router)
api_router.include_router(library.router)
api_router.include_router(streaming.router)
api_router.include_router(metadata.router)

