"""
Missing detector — detects missing information in the user's request.

The :class:`MissingDetector` is responsible for identifying information
that the user did not provide but that is needed to fully understand
the requirements.  When information is missing the detector does
**not** guess — it records a :class:`RequiredQuestion` so the caller
can ask the user, or apply a pre-approved assumption from the
knowledge base if one is explicitly defined.

The detector also detects points of ambiguity in the user's request
(vague terms, under-specified features, multiple possible
interpretations, missing context).

The detector does **not** write code, create files, or make build
decisions.  It only *identifies* what is missing.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .context_reader import ContextData
from .graph_reader import GraphData
from .knowledge_reader import KnowledgeData
from .report_data import (
    AMBIGUITY_MISSING_CONTEXT,
    AMBIGUITY_MULTIPLE_INTERPRETATIONS,
    AMBIGUITY_UNDER_SPECIFIED,
    AMBIGUITY_VAGUE,
    AmbiguityPoint,
    Requirement,
    RequiredQuestion,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_USER_REQUEST,
)
from .request_reader import RequestData


# ---------------------------------------------------------------------------#
# Vague term patterns
# ---------------------------------------------------------------------------#
#
# Words that indicate the user's request is vague or under-specified.
# These are matched case-insensitively.

_VAGUE_TERMS = [
    "something", "stuff", "things", "etc", "etcetera", "maybe",
    "perhaps", "probably", "some kind", "some sort", "various",
    "anything", "whatever", "and so on", "and more",
    "شيء", "أشياء", "إلخ", "ربما", "أنواع",
]

# Under-specified feature indicators.
_UNDER_SPECIFIED_INDICATORS = [
    "user management", "admin panel", "dashboard", "reports",
    "notifications", "analytics", "search", "filtering",
    "إدارة المستخدمين", "لوحة تحكم", "إشعارات", "تحليلات",
]


class MissingDetector:
    """Detects missing information and points of ambiguity.

    The detector reads the :class:`RequestData`, :class:`ContextData`,
    :class:`GraphData`, and :class:`KnowledgeData` and produces a list
    of :class:`RequiredQuestion` objects and a list of
    :class:`AmbiguityPoint` objects.

    When a piece of information is missing, the detector first checks
    whether the knowledge base has a pre-approved assumption for it.
    If so, the question is marked as resolved with the assumption
    value.  If not, the question remains unresolved.

    The detector does not guess.  It records the missing information as
    a :class:`RequiredQuestion` so the caller can decide how to
    proceed.
    """

    def __init__(self) -> None:
        self._next_q_id = 1
        self._next_amb_id = 1

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def detect(
        self,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
        requirements: List[Requirement],
    ) -> tuple:
        """Detect missing information and ambiguities.

        Returns a tuple ``(questions, ambiguities)``.
        """
        questions: List[RequiredQuestion] = []
        ambiguities: List[AmbiguityPoint] = []

        # Detect missing critical information.
        questions.extend(
            self._detect_missing_database(request, context, knowledge),
        )
        questions.extend(
            self._detect_missing_bot_type(request, context),
        )
        questions.extend(
            self._detect_missing_features(request, context, graph),
        )
        questions.extend(
            self._detect_missing_language(request, context, knowledge),
        )
        questions.extend(
            self._detect_missing_framework(request, context, knowledge),
        )

        # Detect ambiguities.
        ambiguities.extend(
            self._detect_vague_terms(request),
        )
        ambiguities.extend(
            self._detect_under_specified(request),
        )
        ambiguities.extend(
            self._detect_missing_context(request, context),
        )

        return questions, ambiguities

    # ----------------------------------------------------------------- #
    # Missing database
    # ----------------------------------------------------------------- #

    def _detect_missing_database(
        self,
        request: RequestData,
        context: ContextData,
        knowledge: KnowledgeData,
    ) -> List[RequiredQuestion]:
        """Detect when the database choice is missing."""
        # If the context already has a database, no question needed.
        if context.available and context.database:
            return []
        # If any technology in the request is a database, no question.
        db_keywords = ["sqlite", "postgres", "mysql", "mongodb", "redis"]
        for tech in request.technologies:
            if any(kw in tech.lower() for kw in db_keywords):
                return []

        # Check the knowledge base for a default database.
        kb_default = knowledge.defaults.get("database") if knowledge.available else None

        question = RequiredQuestion(
            id=self._next_q_id_str(),
            field_name="database",
            question=(
                "Which database should the bot use for persistent storage?"
            ),
            options=["sqlite", "postgres", "mysql", "mongodb", "none"],
            default=kb_default or "sqlite",
            required=False,
            source_artefact=SOURCE_USER_REQUEST,
            resolution="assumption" if kb_default else "",
            resolved_value=kb_default if kb_default else None,
        )
        return [question]

    # ----------------------------------------------------------------- #
    # Missing bot type
    # ----------------------------------------------------------------- #

    def _detect_missing_bot_type(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[RequiredQuestion]:
        """Detect when the bot type is missing."""
        if request.bot_types:
            return []
        if context.available and context.bot_type and context.bot_type != "general":
            return []

        question = RequiredQuestion(
            id=self._next_q_id_str(),
            field_name="bot_type",
            question=(
                "What type of bot is this? (e.g. command-based, "
                "conversational, notification, AI-powered, hybrid)"
            ),
            options=[
                "command", "conversational", "notification",
                "ai_powered", "hybrid",
            ],
            default="command",
            required=False,
            source_artefact=SOURCE_USER_REQUEST,
        )
        return [question]

    # ----------------------------------------------------------------- #
    # Missing features
    # ----------------------------------------------------------------- #

    def _detect_missing_features(
        self,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
    ) -> List[RequiredQuestion]:
        """Detect when no features have been specified."""
        has_features = bool(request.features)
        if context.available:
            has_features = has_features or bool(context.feature_names)
        if graph.available:
            has_features = has_features or bool(graph.feature_nodes)

        if has_features:
            return []

        question = RequiredQuestion(
            id=self._next_q_id_str(),
            field_name="features",
            question=(
                "What features should the bot have? No features were "
                "detected in the request."
            ),
            options=[],
            default=None,
            required=True,
            source_artefact=SOURCE_USER_REQUEST,
        )
        return [question]

    # ----------------------------------------------------------------- #
    # Missing language
    # ----------------------------------------------------------------- #

    def _detect_missing_language(
        self,
        request: RequestData,
        context: ContextData,
        knowledge: KnowledgeData,
    ) -> List[RequiredQuestion]:
        """Detect when the programming language is missing."""
        if context.available and context.language:
            return []

        kb_default = knowledge.defaults.get("language") if knowledge.available else None

        # Language defaults to python, so this is not strictly required.
        question = RequiredQuestion(
            id=self._next_q_id_str(),
            field_name="language",
            question="Which programming language should be used?",
            options=["python", "javascript", "typescript"],
            default=kb_default or "python",
            required=False,
            source_artefact=SOURCE_PROJECT_CONTEXT,
            resolution="assumption" if kb_default else "",
            resolved_value=kb_default if kb_default else None,
        )
        return [question]

    # ----------------------------------------------------------------- #
    # Missing framework
    # ----------------------------------------------------------------- #

    def _detect_missing_framework(
        self,
        request: RequestData,
        context: ContextData,
        knowledge: KnowledgeData,
    ) -> List[RequiredQuestion]:
        """Detect when the framework is missing."""
        if context.available and context.framework:
            return []

        kb_default = knowledge.defaults.get("framework") if knowledge.available else None

        question = RequiredQuestion(
            id=self._next_q_id_str(),
            field_name="framework",
            question="Which Telegram bot framework should be used?",
            options=[
                "python-telegram-bot", "aiogram", "pyrogram",
                "telebot", "telethon",
            ],
            default=kb_default or "python-telegram-bot",
            required=False,
            source_artefact=SOURCE_PROJECT_CONTEXT,
            resolution="assumption" if kb_default else "",
            resolved_value=kb_default if kb_default else None,
        )
        return [question]

    # ----------------------------------------------------------------- #
    # Ambiguity: vague terms
    # ----------------------------------------------------------------- #

    def _detect_vague_terms(
        self,
        request: RequestData,
    ) -> List[AmbiguityPoint]:
        """Detect vague terms in the user's request."""
        text = request.cleaned_request or request.raw_request
        if not text:
            return []

        lowered = text.lower()
        ambiguities: List[AmbiguityPoint] = []
        for term in _VAGUE_TERMS:
            if term in lowered:
                ambiguities.append(AmbiguityPoint(
                    id=self._next_amb_id_str(),
                    kind=AMBIGUITY_VAGUE,
                    description=(
                        f"The request contains the vague term "
                        f"'{term}', which does not specify a concrete "
                        f"requirement."
                    ),
                    affected_text=term,
                    possible_interpretations=[],
                    related_requirements=[],
                    resolution_hint=(
                        f"Replace '{term}' with a specific, concrete "
                        f"description of what is needed."
                    ),
                    source_artefact=SOURCE_USER_REQUEST,
                ))
        return ambiguities

    # ----------------------------------------------------------------- #
    # Ambiguity: under-specified
    # ----------------------------------------------------------------- #

    def _detect_under_specified(
        self,
        request: RequestData,
    ) -> List[AmbiguityPoint]:
        """Detect under-specified features in the user's request."""
        text = request.cleaned_request or request.raw_request
        if not text:
            return []

        lowered = text.lower()
        ambiguities: List[AmbiguityPoint] = []
        for indicator in _UNDER_SPECIFIED_INDICATORS:
            if indicator in lowered:
                ambiguities.append(AmbiguityPoint(
                    id=self._next_amb_id_str(),
                    kind=AMBIGUITY_UNDER_SPECIFIED,
                    description=(
                        f"The request mentions '{indicator}' but does "
                        f"not specify the details (what entities, "
                        f"what operations, what permissions, etc.)."
                    ),
                    affected_text=indicator,
                    possible_interpretations=[
                        "Full CRUD operations",
                        "Read-only access",
                        "Admin-only access",
                    ],
                    related_requirements=[],
                    resolution_hint=(
                        f"Specify the exact entities, operations, and "
                        f"permissions for '{indicator}'."
                    ),
                    source_artefact=SOURCE_USER_REQUEST,
                ))
        return ambiguities

    # ----------------------------------------------------------------- #
    # Ambiguity: missing context
    # ----------------------------------------------------------------- #

    def _detect_missing_context(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[AmbiguityPoint]:
        """Detect when the request lacks sufficient context."""
        ambiguities: List[AmbiguityPoint] = []
        text = request.cleaned_request or request.raw_request

        # If the request is very short, it may lack context.
        if text and len(text.split()) < 5:
            ambiguities.append(AmbiguityPoint(
                id=self._next_amb_id_str(),
                kind=AMBIGUITY_MISSING_CONTEXT,
                description=(
                    "The request is very short and may not provide "
                    "enough context to fully understand the user's "
                    "intent."
                ),
                affected_text=text[:100] if text else "",
                possible_interpretations=[],
                related_requirements=[],
                resolution_hint=(
                    "Provide more details about the bot's purpose, "
                    "target audience, and expected behaviour."
                ),
                source_artefact=SOURCE_USER_REQUEST,
            ))

        return ambiguities

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #

    def _next_q_id_str(self) -> str:
        qid = f"Q-{self._next_q_id:03d}"
        self._next_q_id += 1
        return qid

    def _next_amb_id_str(self) -> str:
        amb_id = f"AMB-{self._next_amb_id:03d}"
        self._next_amb_id += 1
        return amb_id


__all__ = ["MissingDetector"]
