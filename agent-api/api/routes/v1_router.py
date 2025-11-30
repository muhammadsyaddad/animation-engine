from fastapi import APIRouter

from api.routes.agents import agents_router
from api.routes.health import health_router
from api.routes.playground import playground_router
from api.routes.datasets import router as datasets_router
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(agents_router)
v1_router.include_router(datasets_router)
v1_router.include_router(playground_router)
v1_router.include_router(chat_router)
