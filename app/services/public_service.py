import json
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.repositories.hero_repository import HeroRepository
from app.repositories.faq_repository import FAQRepository
from app.repositories.testimonial_repository import TestimonialRepository
from app.repositories.why_sts_repository import WhySTSRepository
from app.config.logging import logger

CACHE_TTL = 1800  # 30 minutes in seconds

class PublicService:
    """Handles cached localized static content layouts."""

    @staticmethod
    def _to_dict(model_obj) -> dict:
        if not model_obj:
            return {}
        # Convert columns to simple dictionary
        return {c.name: str(getattr(model_obj, c.name)) for c in model_obj.__table__.columns}

    @classmethod
    async def get_hero(
        self, 
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        lang: str
    ) -> Dict[str, Any]:
        """Resolves localized Hero text content, checking Redis cache first."""
        cache_key = f"cache:public:layout:{lang}:hero"
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error("Redis read error on Hero layout", error=str(e))

        repo = HeroRepository(db)
        hero = await repo.get_by_lang(lang)
        
        # If DB is empty, provide fallback default dictionary
        if not hero:
            result = {
                "title": "Welcome to STS Platform" if lang == "en" else "مرحباً بكم في منصة إس تي إس",
                "subtitle": "Secure academic tutor verification gateway." if lang == "en" else "بوابتكم الموثوقة للتحقق من المعلمين الأكاديميين.",
                "lang": lang
            }
        else:
            result = self._to_dict(hero)

        try:
            await redis_client.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        except Exception as e:
            logger.error("Redis write error on Hero layout", error=str(e))

        return result

    @classmethod
    async def get_why_sts(
        self, 
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        lang: str
    ) -> List[Dict[str, Any]]:
        """Resolves localized value propositions, checking Redis cache first."""
        cache_key = f"cache:public:layout:{lang}:why-sts"
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error("Redis read error on WhySTS layout", error=str(e))

        repo = WhySTSRepository(db)
        items = await repo.get_by_lang(lang)
        
        if not items:
            # Fallback mock items
            result = [
                {
                    "title": "Automated Verification" if lang == "en" else "التحقق التلقائي",
                    "description": "AI recommendation letter evaluation checks university details." if lang == "en" else "عمليات تدقيق تلقائية تتحقق من خطابات التوصية الأكاديمية.",
                    "lang": lang
                }
            ]
        else:
            result = [self._to_dict(item) for item in items]

        try:
            await redis_client.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        except Exception as e:
            logger.error("Redis write error on WhySTS layout", error=str(e))

        return result

    @classmethod
    async def get_faqs(
        self, 
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        lang: str
    ) -> List[Dict[str, Any]]:
        """Resolves localized FAQ layouts, checking Redis cache first."""
        cache_key = f"cache:public:layout:{lang}:faq"
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error("Redis read error on FAQ layout", error=str(e))

        repo = FAQRepository(db)
        items = await repo.get_by_lang(lang)
        
        if not items:
            result = [
                {
                    "question": "How is student account verification handled?" if lang == "en" else "كيف يتم التحقق من حساب الطالب؟",
                    "answer": "We mail code confirmation OTPs to your registered university email." if lang == "en" else "نقوم بإرسال رموز التحقق إلى البريد الجامعي المسجل.",
                    "lang": lang
                }
            ]
        else:
            result = [self._to_dict(item) for item in items]

        try:
            await redis_client.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        except Exception as e:
            logger.error("Redis write error on FAQ layout", error=str(e))

        return result

    @classmethod
    async def get_testimonials(
        self, 
        db: AsyncSession, 
        redis_client: aioredis.Redis, 
        lang: str
    ) -> List[Dict[str, Any]]:
        """Resolves localized reviews, checking Redis cache first."""
        cache_key = f"cache:public:layout:{lang}:testimonials"
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error("Redis read error on Testimonials layout", error=str(e))

        repo = TestimonialRepository(db)
        items = await repo.get_by_lang(lang)
        
        if not items:
            result = [
                {
                    "author": "Ali Al-Fahad",
                    "rating": 5,
                    "comment": "Perfect localized experience." if lang == "en" else "تجربة محلية ممتازة.",
                    "lang": lang
                }
            ]
        else:
            result = [self._to_dict(item) for item in items]

        try:
            await redis_client.set(cache_key, json.dumps(result), ex=CACHE_TTL)
        except Exception as e:
            logger.error("Redis write error on Testimonials layout", error=str(e))

        return result
