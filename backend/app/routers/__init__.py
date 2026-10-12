from fastapi import APIRouter
from .health import router as health_router
from .auth import router as auth_router, me_router
from .products import router as products_router
from .cart import router as cart_router
from .ai_chat import router as ai_chat_router
from .analytics import router as analytics_router
from .admin import router as admin_router
from .style_profile import router as style_profile_router
from .wardrobe import router as wardrobe_router
from .outfits import router as outfits_router
from .style_dna import router as style_dna_router
from .gaps import router as gaps_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(me_router)
api_v1_router.include_router(products_router)
api_v1_router.include_router(cart_router)
api_v1_router.include_router(ai_chat_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(admin_router)
api_v1_router.include_router(style_profile_router)
api_v1_router.include_router(wardrobe_router)
api_v1_router.include_router(outfits_router)
api_v1_router.include_router(style_dna_router)
api_v1_router.include_router(gaps_router)

__all__ = ["api_v1_router"]
