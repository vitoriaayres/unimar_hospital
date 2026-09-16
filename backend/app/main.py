from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import auth, products, inventory, predictions, dashboard, alerts, consumption
from app.config import settings
from app.database import close_db, init_db
from app.utils.exceptions import AppException
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency", ["method", "endpoint"])


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_METRICS:
            return await call_next(request)

        method = request.method
        path = request.url.path

        with REQUEST_LATENCY.labels(method=method, endpoint=path).time():
            response = await call_next(request)

        REQUEST_COUNT.labels(method=method, endpoint=path, status=response.status_code).inc()
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting application", version=settings.APP_VERSION, environment=settings.ENVIRONMENT)
    await init_db()
    yield
    logger.info("Shutting down application")
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="PharmaPredict - Hospital Pharmacy Demand Prediction API",
        docs_url="/docs" if settings.ENABLE_SWAGGER else None,
        redoc_url="/redoc" if settings.ENABLE_REDOC else None,
        openapi_url="/openapi.json" if settings.ENABLE_SWAGGER else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    # Metrics
    if settings.ENABLE_METRICS:
        app.add_middleware(MetricsMiddleware)

    # Exception handlers
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        logger.warning(
            "Application exception",
            path=request.url.path,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred" if not settings.DEBUG else str(exc),
            },
        )

    # Health check
    @app.get("/health", tags=["Health"])
    async def health_check() -> dict:
        return {
            "status": "healthy",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/metrics", tags=["Monitoring"])
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type="text/plain")

    # API Routes
    app.include_router(auth.router, prefix=settings.API_PREFIX, tags=["Authentication"])
    app.include_router(alerts.router, prefix=settings.API_PREFIX, tags=["Alerts"])
    app.include_router(products.router, prefix=settings.API_PREFIX, tags=["Products"])
    app.include_router(inventory.router, prefix=settings.API_PREFIX, tags=["Inventory"])
    app.include_router(consumption.router, prefix=settings.API_PREFIX, tags=["Consumption"])
    app.include_router(predictions.router, prefix=settings.API_PREFIX, tags=["Predictions"])
    app.include_router(dashboard.router, prefix=settings.API_PREFIX, tags=["Dashboard"])

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS if not settings.DEBUG else 1,
    )