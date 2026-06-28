from fastapi import APIRouter

from app.api.routes import admin, audit, auth, configuration, health, inventory, reminders

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(audit.router)
api_router.include_router(configuration.router)
api_router.include_router(inventory.router)
api_router.include_router(reminders.router)
