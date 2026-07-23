"""
Blueprint composer engine — assembles a blueprint from a parsed intent.

This engine is the second step in the "understanding" phase.  It reads
the ``intent`` artefact produced by the intent parser and builds a
complete :class:`~telegram_bot_engine.blueprint.Blueprint`.

The composer uses a set of *profiles* — one per bot type — that
describe the default commands, handlers, conversations, and integrations
for that type.  Profiles are plain data so they can be extended or
replaced without touching the composer logic.
"""

from __future__ import annotations

import re
from typing import Dict, List

from ...blueprint import (
    Blueprint,
    BotMeta,
    CommandSpec,
    ConversationSpec,
    DatabaseSpec,
    HandlerSpec,
    IntegrationSpec,
    MiddlewareSpec,
    ProjectSpec,
    StateNode,
)
from ...core.context import GenerationContext
from ...core.result import StageResult
from ..base.base_engine import BaseEngine


def _slugify(text: str) -> str:
    """Convert text into a valid Python package name.

    Arabic text is transliterated to a meaningful English slug using a
    keyword map so that generated package names are readable and valid
    Python identifiers.
    """
    # Arabic keyword → English slug mapping for common bot types.
    ar_map = [
        ("متجر", "store"), ("إلكتروني", "ecommerce"), ("الكتروني", "ecommerce"),
        ("جروب", "group"), ("جروبات", "groups"), ("ادارة", "admin"),
        ("إدارة", "admin"), ("تحميل", "downloader"), ("فيديو", "video"),
        ("فيديوهات", "videos"), ("ذكاء", "ai"), ("اصطناعي", "assistant"),
        ("متجر", "store"), ("بوت", "bot"), ("اعمل", "make"),
        ("مهمة", "task"), ("مهام", "tasks"), ("تذكير", "reminder"),
        ("اخبار", "news"), ("أخبار", "news"), ("طقس", "weather"),
        ("اسعار", "prices"), ("أسعار", "prices"), ("عملة", "currency"),
        ("مساعد", "assistant"), ("استبيان", "survey"), ("اختبار", "quiz"),
    ]
    slug = text
    for ar, en in ar_map:
        slug = slug.replace(ar, f" {en} ")
    # Remove remaining non-ASCII characters.
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug).strip("_").lower()
    # Collapse multiple underscores.
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "generated_bot"


# ---------------------------------------------------------------------------
# Bot-type profiles.
# Each profile is a function returning the blueprint pieces specific to
# that bot type.  Keeping them separate means new bot types can be added
# by adding a new function and a new entry in the dispatch table — no
# existing code changes.
# ---------------------------------------------------------------------------

def _common_commands() -> List[CommandSpec]:
    return [
        CommandSpec(
            name="start",
            description="Initialise the bot and show a welcome message.",
            response_type="keyboard",
        ),
        CommandSpec(
            name="help",
            description="Show the list of available commands.",
        ),
    ]


def _group_admin_profile(intent: Dict) -> Dict:
    commands = _common_commands() + [
        CommandSpec(name="ban", description="Ban a user from the group.",
                    admin_only=True),
        CommandSpec(name="mute", description="Mute a user in the group.",
                    admin_only=True),
        CommandSpec(name="warn", description="Warn a user.",
                    admin_only=True),
        CommandSpec(name="settings", description="Show group settings.",
                    admin_only=True),
    ]
    handlers = [
        HandlerSpec(name="new_members", handler_type="message",
                    triggers=["new_chat_members"]),
        HandlerSpec(name="spam_filter", handler_type="message"),
    ]
    middlewares = [
        MiddlewareSpec(name="spam_filter", description="Filter spam messages."),
        MiddlewareSpec(name="rate_limiter", description="Limit message rate."),
    ]
    return {
        "commands": commands, "handlers": handlers,
        "middlewares": middlewares,
        "database": DatabaseSpec(
            enabled=True, backend="sqlite",
            models=[
                {"name": "GroupSettings", "fields": [
                    {"name": "chat_id", "type": "int", "primary": True},
                    {"name": "welcome_text", "type": "str"},
                    {"name": "rules", "type": "str"},
                ]},
                {"name": "Warn", "fields": [
                    {"name": "id", "type": "int", "primary": True},
                    {"name": "user_id", "type": "int"},
                    {"name": "chat_id", "type": "int"},
                    {"name": "reason", "type": "str"},
                ]},
            ],
        ),
    }


def _store_profile(intent: Dict) -> Dict:
    commands = _common_commands() + [
        CommandSpec(name="products", description="List available products."),
        CommandSpec(name="cart", description="Show the user's cart."),
        CommandSpec(name="order", description="Place an order."),
        CommandSpec(name="myorders", description="Show the user's orders."),
    ]
    conversations = [
        ConversationSpec(
            name="checkout",
            entry_command="order",
            entry_state="ask_name",
            states=[
                StateNode(name="ask_name", prompt="Please enter your full name."),
                StateNode(name="ask_address", prompt="Please enter your delivery address."),
                StateNode(name="ask_phone", prompt="Please enter your phone number.",
                          expected_input="contact"),
                StateNode(name="confirm", prompt="Confirm your order? (yes/no)",
                          next_state=None),
            ],
        ),
    ]
    return {
        "commands": commands,
        "conversations": conversations,
        "database": DatabaseSpec(
            enabled=True, backend="sqlite",
            models=[
                {"name": "Product", "fields": [
                    {"name": "id", "type": "int", "primary": True},
                    {"name": "name", "type": "str"},
                    {"name": "price", "type": "float"},
                    {"name": "description", "type": "str"},
                ]},
                {"name": "Order", "fields": [
                    {"name": "id", "type": "int", "primary": True},
                    {"name": "user_id", "type": "int"},
                    {"name": "total", "type": "float"},
                    {"name": "status", "type": "str"},
                ]},
            ],
        ),
        "integrations": [
            IntegrationSpec(
                name="payment", kind="payment",
                description="Payment processing integration.",
                env_vars=["PAYMENT_API_KEY"],
            ),
        ],
    }


def _downloader_profile(intent: Dict) -> Dict:
    commands = _common_commands() + [
        CommandSpec(name="download", description="Download a video from a URL.",
                    arguments=["url"]),
    ]
    return {
        "commands": commands,
        "handlers": [
            HandlerSpec(name="url_handler", handler_type="message",
                        triggers=["url"]),
        ],
        "integrations": [
            IntegrationSpec(
                name="yt_dlp", kind="downloader",
                description="yt-dlp backend for video downloads.",
                env_vars=[],
            ),
        ],
    }


def _ai_assistant_profile(intent: Dict) -> Dict:
    commands = _common_commands() + [
        CommandSpec(name="ask", description="Ask the AI a question.",
                    arguments=["query"]),
        CommandSpec(name="clear", description="Clear conversation history."),
        CommandSpec(name="setmodel", description="Set the AI model.",
                    arguments=["model"], admin_only=True),
    ]
    return {
        "commands": commands,
        "integrations": [
            IntegrationSpec(
                name="openai", kind="ai_provider",
                description="OpenAI-compatible AI provider.",
                env_vars=["OPENAI_API_KEY", "AI_MODEL"],
                config={"default_model": "gpt-4o-mini"},
            ),
        ],
        "database": DatabaseSpec(
            enabled=True, backend="sqlite",
            models=[
                {"name": "Conversation", "fields": [
                    {"name": "id", "type": "int", "primary": True},
                    {"name": "user_id", "type": "int"},
                    {"name": "role", "type": "str"},
                    {"name": "content", "type": "str"},
                ]},
            ],
        ),
    }


def _general_profile(intent: Dict) -> Dict:
    return {"commands": _common_commands()}


_PROFILES: Dict = {
    "group_admin": _group_admin_profile,
    "store": _store_profile,
    "downloader": _downloader_profile,
    "ai_assistant": _ai_assistant_profile,
    "general": _general_profile,
}


class BlueprintComposerEngine(BaseEngine):
    """Assembles a blueprint from a parsed intent."""

    def __init__(self) -> None:
        super().__init__(
            name="blueprint_composer",
            version="1.0.0",
            description=(
                "Builds a complete Blueprint from a structured intent "
                "using bot-type profiles."
            ),
            tags=["understanding"],
            metadata={"phase": "understanding"},
        )

    def execute(self, context: GenerationContext) -> StageResult:
        intent = context.get("intent")
        if intent is None:
            return self.failed(
                ["No 'intent' artefact found — run the intent parser first."]
            )

        raw = intent.get("raw", "telegram bot")
        bot_type = intent.get("bot_type", "general")
        features = intent.get("features", [])

        self._log.info("Composing blueprint",
                       {"bot_type": bot_type, "features": features})

        profile_fn = _PROFILES.get(bot_type, _general_profile)
        profile = profile_fn(intent)

        name = _slugify(raw)[:40]
        if not name.replace("_", "").isalnum():
            name = "generated_bot"

        meta = BotMeta(
            name=name,
            display_name=raw,
            description=raw,
            bot_type=bot_type,
        )

        project = ProjectSpec(
            name=name,
            description=raw,
            python_version=intent.get("language_version", "3.11"),
            dependencies=self._default_dependencies(bot_type, features),
        )

        blueprint = Blueprint(
            meta=meta,
            project=project,
            commands=profile.get("commands", []),
            handlers=profile.get("handlers", []),
            conversations=profile.get("conversations", []),
            database=profile.get("database", DatabaseSpec()),
            middlewares=profile.get("middlewares", []),
            integrations=profile.get("integrations", []),
            extra={"features": features},
        )

        self._log.info("Blueprint composed",
                       {"name": name, "commands": blueprint.command_names()})
        return self.ok(outputs={"blueprint": blueprint})

    @staticmethod
    def _default_dependencies(bot_type: str, features: List[str]) -> List[str]:
        deps = ["python-telegram-bot>=20.7"]
        if "database" in features or bot_type in ("store", "group_admin", "ai_assistant"):
            deps.append("SQLAlchemy>=2.0")
        if "ai" in features or bot_type == "ai_assistant":
            deps.append("openai>=1.0")
        if "media_download" in features or bot_type == "downloader":
            deps.append("yt-dlp")
        if "payments" in features:
            deps.append("stripe")
        return deps


__all__ = ["BlueprintComposerEngine"]
