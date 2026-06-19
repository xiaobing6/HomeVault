from fastapi import APIRouter

from app.api.routes import auth, configuration, health, inventory

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(configuration.router)
api_router.include_router(inventory.router)
