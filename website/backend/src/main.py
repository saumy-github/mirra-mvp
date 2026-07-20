"""FastAPI app assembly: routers, CORS, error handlers, lifespan."""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import get_settings
from .core.errors import register_exception_handlers
from .analytics.routes import router as analytics_router
from .auth.routes import router as auth_router
from .avatars.routes import router as avatars_router
from .capture.routes import router as capture_router
from .catalog.routes import router as catalog_router
from .measurements.routes import router as measurements_router
from .signature_looks.routes import router as signature_looks_router
from .tryon.routes import router as tryon_router
from .users.routes import router as users_router

logger = logging.getLogger("mirra.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await db.ensure_indexes()
        logger.info("Mongo indexes ensured (database=%s)", get_settings().database_name)
    except Exception as exc:
        # Boot anyway so dev without Mongo still gets a responding app;
        # /health reports the database as unreachable.
        logger.warning("Could not ensure Mongo indexes at startup: %s", exc)
    yield
    await db.close_client()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Mirra Website Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,  # the refresh cookie needs credentialed CORS
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    api = APIRouter(prefix="/api/v1")

    @api.get("/health")
    async def health():
        db_ok = await db.ping()
        return {"status": "ok", "database": "connected" if db_ok else "unreachable"}

    # Service routers are mounted here as phases land (backend-implementation-plan.md).
    api.include_router(auth_router)
    api.include_router(users_router)
    api.include_router(measurements_router)
    api.include_router(avatars_router)
    api.include_router(catalog_router)
    api.include_router(tryon_router)
    api.include_router(signature_looks_router)
    api.include_router(analytics_router)
    api.include_router(capture_router)
    app.include_router(api)
    return app


app = create_app()
