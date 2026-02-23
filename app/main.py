from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.config import settings
from app.api.routes import router
from app.api.chat_routes import router as chat_router
from app.api.templates_routes import router as templates_router
from app.api.knowledge_rules_routes import router as knowledge_rules_router
from mcp.server_http import router as mcp_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = FastAPI(
    title="ELMA365 Documentation Crawler",
    description="Crawler and normalizer for ELMA365 documentation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")
app.include_router(chat_router)
app.include_router(templates_router)
app.include_router(knowledge_rules_router)
app.include_router(mcp_router)


@app.on_event("startup")
async def startup_event():
    """Application startup."""
    logging.info("Application started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logging.info("Application shutting down")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ELMA365 Documentation Crawler API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

