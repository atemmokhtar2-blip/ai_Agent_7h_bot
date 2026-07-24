"""
Priority assigner — assigns priorities to requirements based on
importance, dependencies, and impact.

The :class:`PriorityAssigner` is responsible for assigning a priority
level (``critical``, ``high``, ``normal``, or ``low``) to each
requirement based on three factors:

1. **Importance** — how critical the requirement is to the project's
   core functionality.  Requirements that are essential to the bot's
   primary purpose get higher priority.
2. **Dependencies** — requirements that other requirements depend on
   get higher priority (they must be satisfied first).
3. **Impact** — requirements that have a large impact on the rest of
   the system get higher priority.

The assigner also builds the ``depends_on`` and ``depended_by`` lists
for each requirement.

The assigner does **not** write code, create files, or make build
decisions.  It only *assigns* priorities.
"""

from __future__ import annotations

from typing import Dict, List, Set

from .context_reader import ContextData
from .knowledge_reader import KnowledgeData
from .report_data import (
    CATEGORY_FUNCTIONAL,
    CATEGORY_SECURITY,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_NORMAL,
    PRIORITY_RANKS,
    Requirement,
    SOURCE_USER_REQUEST,
)
from .request_reader import RequestData


# ---------------------------------------------------------------------------#
# Priority heuristics
# ---------------------------------------------------------------------------#
#
# Keywords that indicate a requirement is of a particular importance
# level.  These are matched case-insensitively against the requirement
# name and description.

_CRITICAL_KEYWORDS = [
    "authentication", "authorisation", "authorization", "core",
    "essential", "critical", "mandatory", "required", "must",
    "main", "primary", "central", "vital", "foundation",
    "مصادقة", "أساسي", "ضروري", "إلزامي", "جوهر",
]

_HIGH_KEYWORDS = [
    "security", "database", "storage", "command", "handler",
    "api", "service", "data", "model", "validation",
    "أمان", "قاعدة بيانات", "تخزين", "أمر", "بيانات",
]

_LOW_KEYWORDS = [
    "future", "expansion", "later", "nice to have", "optional",
    "enhancement", "polish", "cosmetic", "documentation",
    "مستقبل", "توسع", "اختياري", "تحسين",
]

# Functional requirement name patterns that indicate high importance.
_CORE_FUNCTIONAL_PATTERNS = [
    "start", "help", "main", "core", "primary", "default",
    "بداية", "مساعدة", "رئيسي",
]


class PriorityAssigner:
    """Assigns priorities to requirements.

    The assigner reads the :class:`Requirement` list and the
    :class:`RequestData`, :class:`ContextData`, and
    :class:`KnowledgeData` and assigns a priority to each requirement.
    It also builds the ``depends_on`` and ``depended_by`` lists.

    Priority levels (with numeric ranks):
    * ``critical`` (rank 10) — the project cannot function without it.
    * ``high`` (rank 20) — important for the project's core
      functionality.
    * ``normal`` (rank 30) — standard requirements.
    * ``low`` (rank 40) — nice-to-have, future, or optional
      requirements.
    """

    def __init__(self) -> None:
        self._requirement_index: Dict[str, Requirement] = {}

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def assign(
        self,
        requirements: List[Requirement],
        request: RequestData,
        context: ContextData,
        knowledge: KnowledgeData,
    ) -> List[Requirement]:
        """Assign priorities and build dependency links.

        Returns the same list of requirements (mutated in place).
        """
        # Build the index.
        self._requirement_index = {r.id: r for r in requirements}

        # Step 1: build dependency links.
        self._build_dependency_links(requirements)

        # Step 2: assign initial priorities based on importance.
        for req in requirements:
            self._assign_initial_priority(req, request, context)

        # Step 3: boost priorities based on dependencies (depended_by).
        for req in requirements:
            if req.depended_by:
                # If this requirement is depended on by others, it
                # should be at least high priority.
                if req.priority_rank > PRIORITY_RANKS[PRIORITY_HIGH]:
                    self._set_priority(req, PRIORITY_HIGH)

        # Step 4: adjust for security requirements (always at least high).
        for req in requirements:
            if req.category == CATEGORY_SECURITY:
                if req.priority_rank > PRIORITY_RANKS[PRIORITY_HIGH]:
                    self._set_priority(req, PRIORITY_HIGH)

        # Step 5: adjust for future-expansion and implicit requirements
        # (cap at normal — they should not be critical, but they should
        # also not be lower than normal).
        for req in requirements:
            if req.category == "future_expansion" or (
                req.is_implicit and req.category == CATEGORY_FUNCTIONAL
            ):
                if req.priority_rank != PRIORITY_RANKS[PRIORITY_NORMAL]:
                    self._set_priority(req, PRIORITY_NORMAL)

        return requirements

    # ----------------------------------------------------------------- #
    # Dependency link building
    # ----------------------------------------------------------------- #

    def _build_dependency_links(
        self,
        requirements: List[Requirement],
    ) -> None:
        """Build the ``depends_on`` and ``depended_by`` lists.

        A requirement A depends on requirement B when:
        * B's name appears in A's description or keywords, or
        * A and B are in the same category and B is a prerequisite
          (e.g. a database model is a prerequisite for a repository).
        """
        for req_a in requirements:
            for req_b in requirements:
                if req_a.id == req_b.id:
                    continue
                if self._depends_on(req_a, req_b):
                    if req_b.id not in req_a.depends_on:
                        req_a.depends_on.append(req_b.id)
                    if req_a.id not in req_b.depended_by:
                        req_b.depended_by.append(req_a.id)

    @staticmethod
    def _depends_on(a: Requirement, b: Requirement) -> bool:
        """Return True when requirement A depends on requirement B."""
        if not a.name or not b.name:
            return False
        a_text = f"{a.name} {a.description}".lower()
        b_name_lower = b.name.lower()

        # A depends on B if B's name appears in A's description.
        if b_name_lower in a_text and b_name_lower != a.name.lower():
            return True

        # Database model → repository (model is a prerequisite).
        if "repository" in a.name.lower() and "model" in b.name.lower():
            return True
        if "service" in a.name.lower() and "repository" in b.name.lower():
            return True
        if "handler" in a.name.lower() and "service" in b.name.lower():
            return True

        return False

    # ----------------------------------------------------------------- #
    # Initial priority assignment
    # ----------------------------------------------------------------- #

    def _assign_initial_priority(
        self,
        req: Requirement,
        request: RequestData,
        context: ContextData,
    ) -> None:
        """Assign the initial priority based on importance keywords."""
        text = f"{req.name} {req.display_name} {req.description}".lower()

        # Check for critical keywords.
        for kw in _CRITICAL_KEYWORDS:
            if kw in text:
                self._set_priority(req, PRIORITY_CRITICAL)
                return

        # Check for core functional patterns.
        for pattern in _CORE_FUNCTIONAL_PATTERNS:
            if pattern in req.name.lower():
                self._set_priority(req, PRIORITY_HIGH)
                return

        # Check for high keywords.
        for kw in _HIGH_KEYWORDS:
            if kw in text:
                self._set_priority(req, PRIORITY_HIGH)
                return

        # Check for low keywords (future, optional, etc.).
        for kw in _LOW_KEYWORDS:
            if kw in text:
                self._set_priority(req, PRIORITY_LOW)
                return

        # If the requirement is from the user's explicit request, it's
        # at least normal.
        if req.source_artefact == SOURCE_USER_REQUEST:
            self._set_priority(req, PRIORITY_NORMAL)
            return

        # Default: normal.
        self._set_priority(req, PRIORITY_NORMAL)

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #

    @staticmethod
    def _set_priority(req: Requirement, priority: str) -> None:
        """Set the priority and priority_rank on a requirement."""
        req.priority = priority
        req.priority_rank = PRIORITY_RANKS.get(priority, PRIORITY_RANKS[PRIORITY_NORMAL])


__all__ = ["PriorityAssigner"]
