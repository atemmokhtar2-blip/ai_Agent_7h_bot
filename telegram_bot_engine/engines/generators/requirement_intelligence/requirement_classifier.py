"""
Requirement classifier — classifies requirements into nine categories.

The :class:`RequirementClassifier` is responsible for taking the raw
understanding of the user's intent (the :class:`IntentAnalysis`, the
:class:`RequestData`, :class:`ContextData`, :class:`GraphData`, and
:class:`KnowledgeData`) and producing a list of :class:`Requirement`
objects, each classified into one of nine categories:

* **functional** — what the system must *do* (commands, handlers,
  business logic).
* **non-functional** — how the system must *be* (usability,
  maintainability, readability).
* **performance** — performance-related requirements (response time,
  throughput, resource usage).
* **security** — security-related requirements (authentication,
  authorisation, data protection).
* **architecture** — architecture-related requirements (modularity,
  layers, separation of concerns).
* **testing** — testing-related requirements (unit tests, integration
  tests, coverage).
* **deployment** — deployment-related requirements (Docker, CI/CD,
  environment).
* **future_expansion** — requirements explicitly marked as
  future/expansion.
* **implicit** — requirements the user did not explicitly state but
  that are implied by the stated requirements or the project context.

The classifier is rule-based and heuristic.  In a future phase it can
be replaced with an LLM-backed implementation without affecting any
other component.

The classifier does **not** write code, create files, or make build
decisions.  It only *understands* and *classifies*.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from .context_reader import ContextData
from .graph_reader import GraphData
from .knowledge_reader import KnowledgeData
from .report_data import (
    CATEGORY_ARCHITECTURE,
    CATEGORY_DEPLOYMENT,
    CATEGORY_FUNCTIONAL,
    CATEGORY_FUTURE_EXPANSION,
    CATEGORY_IMPLICIT,
    CATEGORY_NON_FUNCTIONAL,
    CATEGORY_PERFORMANCE,
    CATEGORY_SECURITY,
    CATEGORY_TESTING,
    PRIORITY_NORMAL,
    PRIORITY_RANKS,
    Requirement,
    SOURCE_INTELLIGENCE_GRAPH,
    SOURCE_KNOWLEDGE_BASE,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_USER_REQUEST,
)
from .request_reader import RequestData


# ---------------------------------------------------------------------------#
# Category keyword maps
# ---------------------------------------------------------------------------#
#
# For each category, a list of keywords that indicate a requirement
# belongs to that category.  Keywords are matched case-insensitively
# against the requirement name and keywords.

_CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    CATEGORY_FUNCTIONAL: [
        "command", "handler", "message", "callback", "reply", "chat",
        "bot", "feature", "function", "logic", "workflow", "process",
        "action", "service", "api", "endpoint", "menu", "keyboard",
        "inline", "query", "text", "notification", "alert", "broadcast",
        "أمر", "معالج", "رسالة", "رد", "محادثة", "بوت", "ميزة", "دالة",
    ],
    CATEGORY_NON_FUNCTIONAL: [
        "usability", "maintainability", "readability", "logging",
        "error handling", "i18n", "localization", "localisation",
        "accessibility", "documentation", "config", "configuration",
        "settings", "user experience", "ux", "internationalization",
        "قابلية", "صيانة", "قراءة", "تسجيل", "معالجة الأخطاء",
    ],
    CATEGORY_PERFORMANCE: [
        "performance", "latency", "throughput", "speed", "response time",
        "fast", "slow", "cache", "caching", "optimization", "optimise",
        "optimize", "concurrent", "async", "resource", "memory", "cpu",
        "أداء", "سرعة", "استجابة", "ذاكرة", "تخزين مؤقت",
    ],
    CATEGORY_SECURITY: [
        "security", "auth", "authentication", "authorisation",
        "authorization", "permission", "role", "access control", "token",
        "secret", "password", "encrypt", "encryption", "hash", "verify",
        "validation", "sanitize", "sanitise", "injection", "xss", "csrf",
        "sql injection", "data protection", "privacy", "gdpr",
        "أمان", "مصادقة", "صلاحية", "تشفير", "كلمة مرور", "خصوصية",
    ],
    CATEGORY_ARCHITECTURE: [
        "architecture", "modular", "module", "layer", "separation",
        "concern", "design pattern", "coupling", "cohesion", "interface",
        "abstract", "dependency injection", "solid", "clean", "structure",
        "package", "namespace", "component", "class", "inheritance",
        "معمارية", "وحدات", "طبقة", "تصميم", "بنية", "مكون",
    ],
    CATEGORY_TESTING: [
        "test", "testing", "unit test", "integration test", "mock",
        "fixture", "coverage", "pytest", "unittest", "tdd", "bdd",
        "assertion", "fixture", "fuzz", "regression", "quality assurance",
        "اختبار", "تغطية", "وحدة", "تكامل",
    ],
    CATEGORY_DEPLOYMENT: [
        "deploy", "deployment", "docker", "container", "kubernetes",
        "k8s", "ci", "cd", "ci/cd", "pipeline", "github actions",
        "gitlab", "jenkins", "heroku", "aws", "gcp", "azure", "vps",
        "server", "hosting", "environment", "production", "staging",
        "env", "dotenv", "systemd", "nginx", "reverse proxy", "ssl",
        "tls", "domain", "تطبيق", "نشر", "خادم", "بيئة",
    ],
    CATEGORY_FUTURE_EXPANSION: [
        "future", "expansion", "later", "phase 2", "v2", "next version",
        "roadmap", "todo", "enhancement", "extend", "scalable",
        "تطوير", "مستقبل", "توسع", "لاحق",
    ],
}

# Keywords that indicate a requirement is about the database / storage.
_DATABASE_KEYWORDS = [
    "database", "db", "sqlite", "postgres", "mysql", "mongodb", "redis",
    "storage", "store", "persist", "persistence", "model", "schema",
    "migration", "table", "query", "orm", "sql", "nosql", "repository",
    "قاعدة بيانات", "تخزين", "جدول",
]


class RequirementClassifier:
    """Classifies requirements into the nine categories.

    The classifier takes the raw understanding (intent, request,
    context, graph, knowledge) and produces a list of
    :class:`Requirement` objects, each with a category, a priority
    (initially ``normal``), and traceability (source artefact).

    The classifier is the first step of the requirement intelligence
    pipeline.  After classification, the :class:`MissingDetector`,
    :class:`ConflictDetector`, :class:`PriorityAssigner`, and
    :class:`QualityValidator` further refine the report.
    """

    def __init__(self) -> None:
        self._next_id = 1

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def classify(
        self,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> List[Requirement]:
        """Classify the requirements and return a list of
        :class:`Requirement` objects."""
        requirements: List[Requirement] = []

        # Step 1: classify explicit features from the request.
        requirements.extend(
            self._classify_features(request, context),
        )

        # Step 2: classify explicit bot-type requirements.
        requirements.extend(
            self._classify_bot_types(request, context),
        )

        # Step 3: classify technology / framework requirements.
        requirements.extend(
            self._classify_technologies(request, context),
        )

        # Step 4: classify from the project context's components.
        requirements.extend(
            self._classify_context_components(context),
        )

        # Step 5: classify from the intelligence graph's nodes.
        requirements.extend(
            self._classify_graph_nodes(graph),
        )

        # Step 6: classify from the knowledge base's domain rules.
        requirements.extend(
            self._classify_knowledge_rules(knowledge),
        )

        # Step 7: classify implicit requirements (those not explicitly
        # stated but implied by the project).
        requirements.extend(
            self._classify_implicit(request, context, graph, knowledge),
        )

        # Step 8: classify future-expansion requirements.
        requirements.extend(
            self._classify_future_expansion(request, context),
        )

        return requirements

    # ----------------------------------------------------------------- #
    # Feature classification
    # ----------------------------------------------------------------- #

    def _classify_features(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[Requirement]:
        """Classify each feature as a functional requirement."""
        requirements: List[Requirement] = []
        for feature_name in request.features:
            category = self._classify_by_name(feature_name)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(feature_name),
                display_name=feature_name,
                description=(
                    f"The bot must support the '{feature_name}' feature."
                ),
                goal=(
                    f"Provide the '{feature_name}' capability to the user."
                ),
                reason=(
                    f"The user explicitly requested the '{feature_name}' "
                    f"feature."
                ),
                category=category,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_USER_REQUEST,
                confidence=0.9,
                evidence=[f"feature: {feature_name}"],
                keywords=[feature_name],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Bot-type classification
    # ----------------------------------------------------------------- #

    def _classify_bot_types(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[Requirement]:
        """Classify each bot-type as a functional requirement."""
        requirements: List[Requirement] = []
        for bot_type in request.bot_types:
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(f"bot_type_{bot_type}"),
                display_name=f"Bot Type: {bot_type}",
                description=(
                    f"The bot must operate as a '{bot_type}' bot."
                ),
                goal=(
                    f"Implement the bot as a '{bot_type}' type bot."
                ),
                reason=(
                    f"The user specified the bot type as '{bot_type}'."
                ),
                category=CATEGORY_FUNCTIONAL,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_USER_REQUEST,
                confidence=0.85,
                evidence=[f"bot_type: {bot_type}"],
                keywords=[bot_type],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Technology classification
    # ----------------------------------------------------------------- #

    def _classify_technologies(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[Requirement]:
        """Classify each technology as an architecture requirement."""
        requirements: List[Requirement] = []
        # Combine technologies from the request and the context.
        techs: List[str] = list(request.technologies)
        if context.available:
            if context.framework and context.framework not in techs:
                techs.append(context.framework)
            if context.language and context.language not in techs:
                techs.append(context.language)
            if context.database and context.database not in techs:
                techs.append(context.database)

        for tech in techs:
            # Database technologies go to a functional/database req.
            if self._is_database_tech(tech):
                category = CATEGORY_FUNCTIONAL
                desc = (
                    f"The project must use '{tech}' for data storage."
                )
                goal = f"Use '{tech}' as the database backend."
            else:
                category = CATEGORY_ARCHITECTURE
                desc = (
                    f"The project must be built with '{tech}'."
                )
                goal = f"Use '{tech}' as the technology stack."

            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(f"tech_{tech}"),
                display_name=f"Technology: {tech}",
                description=desc,
                goal=goal,
                reason=(
                    f"The technology '{tech}' was specified in the "
                    f"request or project context."
                ),
                category=category,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=(
                    SOURCE_PROJECT_CONTEXT if context.available
                    else SOURCE_USER_REQUEST
                ),
                confidence=0.8,
                evidence=[f"technology: {tech}"],
                keywords=[tech],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Context component classification
    # ----------------------------------------------------------------- #

    def _classify_context_components(
        self,
        context: ContextData,
    ) -> List[Requirement]:
        """Classify each component from the project context as a
        functional requirement."""
        requirements: List[Requirement] = []
        if not context.available:
            return requirements
        for component_name in context.component_names:
            category = self._classify_by_name(component_name)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(component_name),
                display_name=f"Component: {component_name}",
                description=(
                    f"The project must include the '{component_name}' "
                    f"component."
                ),
                goal=(
                    f"Implement the '{component_name}' component."
                ),
                reason=(
                    f"The component '{component_name}' was detected in "
                    f"the project context."
                ),
                category=category,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_PROJECT_CONTEXT,
                confidence=0.75,
                evidence=[f"component: {component_name}"],
                keywords=[component_name],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Graph node classification
    # ----------------------------------------------------------------- #

    def _classify_graph_nodes(
        self,
        graph: GraphData,
    ) -> List[Requirement]:
        """Classify each node from the intelligence graph as a
        functional or architecture requirement."""
        requirements: List[Requirement] = []
        if not graph.available:
            return requirements

        seen_names: Set[str] = set()

        # Component nodes → functional.
        for node_name in graph.component_nodes:
            if node_name in seen_names:
                continue
            seen_names.add(node_name)
            category = self._classify_by_name(node_name)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(node_name),
                display_name=f"Graph Component: {node_name}",
                description=(
                    f"The component '{node_name}' must be present in "
                    f"the project."
                ),
                goal=f"Implement the '{node_name}' component.",
                reason=(
                    f"The component '{node_name}' was detected in the "
                    f"intelligence graph."
                ),
                category=category,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_INTELLIGENCE_GRAPH,
                confidence=0.7,
                evidence=[f"graph component: {node_name}"],
                keywords=[node_name],
            )
            requirements.append(req)

        # Feature nodes → functional.
        for node_name in graph.feature_nodes:
            if node_name in seen_names:
                continue
            seen_names.add(node_name)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(node_name),
                display_name=f"Graph Feature: {node_name}",
                description=(
                    f"The feature '{node_name}' must be implemented."
                ),
                goal=f"Implement the '{node_name}' feature.",
                reason=(
                    f"The feature '{node_name}' was detected in the "
                    f"intelligence graph."
                ),
                category=CATEGORY_FUNCTIONAL,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_INTELLIGENCE_GRAPH,
                confidence=0.7,
                evidence=[f"graph feature: {node_name}"],
                keywords=[node_name],
            )
            requirements.append(req)

        # Command nodes → functional.
        for node_name in graph.command_nodes:
            if node_name in seen_names:
                continue
            seen_names.add(node_name)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(f"command_{node_name}"),
                display_name=f"Command: {node_name}",
                description=(
                    f"The bot must handle the '{node_name}' command."
                ),
                goal=f"Implement the '{node_name}' command handler.",
                reason=(
                    f"The command '{node_name}' was detected in the "
                    f"intelligence graph."
                ),
                category=CATEGORY_FUNCTIONAL,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_INTELLIGENCE_GRAPH,
                confidence=0.7,
                evidence=[f"command: {node_name}"],
                keywords=[node_name],
            )
            requirements.append(req)

        return requirements

    # ----------------------------------------------------------------- #
    # Knowledge rule classification
    # ----------------------------------------------------------------- #

    def _classify_knowledge_rules(
        self,
        knowledge: KnowledgeData,
    ) -> List[Requirement]:
        """Classify each domain rule from the knowledge base as a
        requirement."""
        requirements: List[Requirement] = []
        if not knowledge.available:
            return requirements
        for i, rule in enumerate(knowledge.domain_rules):
            category = self._classify_by_name(rule)
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(f"domain_rule_{i}"),
                display_name=f"Domain Rule: {rule[:60]}",
                description=(
                    f"The project must respect the domain rule: {rule}."
                ),
                goal=(
                    f"Adhere to the domain rule: {rule}."
                ),
                reason=(
                    f"The domain rule was defined in the knowledge base."
                ),
                category=category,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_KNOWLEDGE_BASE,
                confidence=0.85,
                evidence=[f"domain_rule: {rule[:80]}"],
                is_assumption=True,
                keywords=[rule],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Implicit requirement classification
    # ----------------------------------------------------------------- #

    def _classify_implicit(
        self,
        request: RequestData,
        context: ContextData,
        graph: GraphData,
        knowledge: KnowledgeData,
    ) -> List[Requirement]:
        """Classify implicit requirements — those not explicitly
        stated but implied by the project."""
        requirements: List[Requirement] = []

        # If no data source is available at all, there is nothing to
        # infer implicit requirements from.
        if (
            not request.available
            and not context.available
            and not graph.available
            and not knowledge.available
        ):
            return requirements

        # Every bot needs error handling.
        requirements.append(Requirement(
            id=self._next_id_str(),
            name="error_handling",
            display_name="Error Handling",
            description=(
                "The bot must handle errors gracefully and report "
                "them to the user in a friendly manner."
            ),
            goal="Provide robust error handling across all bot commands.",
            reason=(
                "Every bot requires error handling, even when the user "
                "does not explicitly request it."
            ),
            category=CATEGORY_NON_FUNCTIONAL,
            priority=PRIORITY_NORMAL,
            priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
            source_artefact=(
                SOURCE_PROJECT_CONTEXT if context.available
                else SOURCE_USER_REQUEST
            ),
            confidence=0.9,
            evidence=["implicit: every bot needs error handling"],
            is_implicit=True,
            keywords=["error", "handling", "graceful"],
        ))

        # Every bot needs logging.
        requirements.append(Requirement(
            id=self._next_id_str(),
            name="logging",
            display_name="Logging",
            description=(
                "The bot must log important events for debugging and "
                "monitoring."
            ),
            goal="Provide logging for all important bot events.",
            reason=(
                "Every bot requires logging for debugging and "
                "operational visibility."
            ),
            category=CATEGORY_NON_FUNCTIONAL,
            priority=PRIORITY_NORMAL,
            priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
            source_artefact=(
                SOURCE_PROJECT_CONTEXT if context.available
                else SOURCE_USER_REQUEST
            ),
            confidence=0.85,
            evidence=["implicit: every bot needs logging"],
            is_implicit=True,
            keywords=["logging", "monitoring"],
        ))

        # If the project has a database, it needs data validation.
        has_db = (
            any(self._is_database_tech(t) for t in request.technologies)
            or (context.available and bool(context.database))
            or (graph.available and bool(graph.database_table_nodes))
        )
        if has_db:
            requirements.append(Requirement(
                id=self._next_id_str(),
                name="data_validation",
                display_name="Data Validation",
                description=(
                    "All data entering the database must be validated "
                    "and sanitised."
                ),
                goal="Ensure data integrity through validation.",
                reason=(
                    "A project with a database requires data validation "
                    "to prevent corruption and injection attacks."
                ),
                category=CATEGORY_SECURITY,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=(
                    SOURCE_PROJECT_CONTEXT if context.available
                    else SOURCE_USER_REQUEST
                ),
                confidence=0.8,
                evidence=["implicit: database requires data validation"],
                is_implicit=True,
                keywords=["validation", "sanitise", "database"],
            ))

        return requirements

    # ----------------------------------------------------------------- #
    # Future-expansion classification
    # ----------------------------------------------------------------- #

    def _classify_future_expansion(
        self,
        request: RequestData,
        context: ContextData,
    ) -> List[Requirement]:
        """Classify future-expansion areas as future_expansion
        requirements."""
        requirements: List[Requirement] = []
        areas: List[str] = []
        if context.available:
            areas.extend(context.expansion_areas)
        for area in areas:
            req = Requirement(
                id=self._next_id_str(),
                name=self._slug(f"expansion_{area}"),
                display_name=f"Future Expansion: {area}",
                description=(
                    f"The project should be designed to allow future "
                    f"expansion into '{area}'."
                ),
                goal=(
                    f"Enable future expansion into '{area}'."
                ),
                reason=(
                    f"The expansion area '{area}' was identified in the "
                    f"project context."
                ),
                category=CATEGORY_FUTURE_EXPANSION,
                priority=PRIORITY_NORMAL,
                priority_rank=PRIORITY_RANKS[PRIORITY_NORMAL],
                source_artefact=SOURCE_PROJECT_CONTEXT,
                confidence=0.7,
                evidence=[f"expansion: {area}"],
                is_implicit=True,
                keywords=[area, "expansion", "future"],
            )
            requirements.append(req)
        return requirements

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #

    def _classify_by_name(self, name: str) -> str:
        """Classify a requirement by its name using keyword matching."""
        lowered = (name or "").lower()
        if not lowered:
            return CATEGORY_FUNCTIONAL

        for category, keywords in _CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in lowered:
                    return category

        # Default to functional.
        return CATEGORY_FUNCTIONAL

    @staticmethod
    def _is_database_tech(tech: str) -> bool:
        """Return True when the technology is a database technology."""
        lowered = (tech or "").lower()
        return any(kw in lowered for kw in _DATABASE_KEYWORDS)

    def _next_id_str(self) -> str:
        """Return the next requirement id (e.g. ``REQ-001``)."""
        req_id = f"REQ-{self._next_id:03d}"
        self._next_id += 1
        return req_id

    @staticmethod
    def _slug(name: str) -> str:
        """Convert a display name to a machine-friendly slug."""
        if not name:
            return ""
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip())
        slug = slug.strip("_").lower()
        return slug


__all__ = ["RequirementClassifier"]
