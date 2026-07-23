"""
Intent parser engine — converts the user request into a structured intent.

This engine is the first step in the "understanding" phase.  It takes
the raw natural-language request from the context and produces a
structured ``intent`` dictionary that the blueprint composer can use.

The current implementation uses a rule-based heuristic.  In a future
phase this engine can be replaced with an LLM-backed implementation
without affecting any other component — they all rely on the
``intent`` artefact shape, not on this engine's internals.
"""

from __future__ import annotations

import re
from typing import Dict, List

from ...core.context import GenerationContext
from ...core.result import StageResult
from ..base.base_engine import BaseEngine

# ---------------------------------------------------------------------------
# Bot-type classification rules.
# Each rule maps a list of keywords (matched case-insensitively) to a
# bot type identifier.  The first matching rule wins.
# ---------------------------------------------------------------------------

_BOT_TYPE_RULES: List = [
    (["group", "admin", "manage", "moderat", "ادارة", "إدارة"], "group_admin"),
    (["store", "shop", "ecommerce", "متجر", "متجري"], "store"),
    (["download", "downloader", "تحميل", "يوتيوب", "youtube", "video", "فيديو"], "downloader"),
    (["ai", "gpt", "chatgpt", "ذكاء", "اصطناعي"], "ai_assistant"),
    (["todo", "task", "reminder", "مهمة", "مهام"], "task_manager"),
    (["quiz", "poll", "survey", "استبيان"], "quiz"),
    (["news", "rss", "اخبار", "أخبار"], "news"),
    (["weather", "طقس"], "weather"),
    (["currency", "price", "اسعار", "أسعار"], "currency"),
    (["chat", "assistant", "helper", "مساعد"], "assistant"),
]


class IntentParserEngine(BaseEngine):
    """Parses a natural-language request into a structured intent."""

    def __init__(self) -> None:
        super().__init__(
            name="intent_parser",
            version="1.0.0",
            description=(
                "Converts a natural-language bot description into a "
                "structured intent dictionary."
            ),
            tags=["understanding"],
            metadata={"phase": "understanding"},
        )

    def execute(self, context: GenerationContext) -> StageResult:
        request = context.request.strip()
        if not request:
            return self.failed(["Empty request — nothing to parse."])

        self._log.info("Parsing intent", {"request": request})

        bot_type = self._classify(request)
        features = self._extract_features(request)
        language = self._detect_language(request)

        intent: Dict = {
            "raw": request,
            "bot_type": bot_type,
            "features": features,
            "language": language,
            "language_version": "3.11",
            "framework": "python-telegram-bot",
        }

        self._log.info("Intent parsed",
                       {"bot_type": bot_type, "features": features})
        return self.ok(outputs={"intent": intent})

    # -- classification ----------------------------------------------------

    @staticmethod
    def _classify(request: str) -> str:
        lowered = request.lower()
        for keywords, bot_type in _BOT_TYPE_RULES:
            if any(kw in lowered for kw in keywords):
                return bot_type
        return "general"

    @staticmethod
    def _extract_features(request: str) -> List[str]:
        """Detect requested features from keywords in the request."""
        lowered = request.lower()
        feature_map: Dict[str, List[str]] = {
            "database": ["database", "db", "store data", "قاعدة", "بيانات"],
            "admin_panel": ["admin", "panel", "لوحة", "تحكم"],
            "payments": ["payment", "pay", "checkout", "دفع", "مدفوعات"],
            "ai": ["ai", "gpt", "ذكاء", "اصطناعي"],
            "media_download": ["download", "youtube", "تحميل", "فيديو"],
            "scheduling": ["schedule", "cron", "جدولة", "مجدول"],
            "multi_language": ["language", "multilingual", "لغات", "متعدد"],
            "rate_limit": ["rate", "limit", "حد", "محدود"],
            "logging": ["log", "logging", "سجل", "تسجيل"],
        }
        detected: List[str] = []
        for feature, keywords in feature_map.items():
            if any(kw in lowered for kw in keywords):
                detected.append(feature)
        return detected

    @staticmethod
    def _detect_language(request: str) -> str:
        # Detect whether the request contains Arabic characters.
        if re.search(r"[\u0600-\u06FF]", request):
            return "ar"
        return "en"


__all__ = ["IntentParserEngine"]
