"""
Conflict detector — detects conflicting, illogical, impossible, and
duplicate requirements.

The :class:`ConflictDetector` is responsible for detecting conflicts
between the requirements produced by the
:class:`RequirementClassifier`.  It detects four kinds of conflicts:

* **contradictory** — two requirements that cannot both be true
  (e.g. "use SQLite" and "use PostgreSQL").
* **illogical** — a requirement that does not make sense in the
  context of the project (e.g. "no database" when the project has
  database tables).
* **impossible** — a requirement that cannot be satisfied within the
  limits of the project (e.g. "support 1 million concurrent users"
  for a simple bot).
* **duplicate** — two requirements that describe the same need.

The detector does **not** write code, create files, or make build
decisions.  It only *detects* conflicts.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from .context_reader import ContextData
from .graph_reader import GraphData
from .report_data import (
    CONFLICT_CONTRADICTORY,
    CONFLICT_DUPLICATE,
    CONFLICT_ILLOGICAL,
    CONFLICT_IMPOSSIBLE,
    PRIORITY_NORMAL,
    Requirement,
    RequirementConflict,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    SOURCE_USER_REQUEST,
)


# ---------------------------------------------------------------------------#
# Contradictory technology pairs
# ---------------------------------------------------------------------------#
#
# Technologies that cannot be used together.  Each entry is a set of
# technologies that are mutually exclusive.  When two requirements
# reference technologies from the same group, a contradictory conflict
# is detected.

_CONTRADICTORY_TECH_GROUPS: List[Set[str]] = [
    {"sqlite", "postgres", "mysql", "mongodb", "redis", "mariadb"},
    {"python-telegram-bot", "aiogram", "pyrogram", "telebot", "telethon"},
]

# Impossible requirement indicators (unrealistic for a simple bot).
_IMPOSSIBLE_INDICATORS = [
    "million users", "billion users", "real-time", "zero latency",
    "infinite", "unlimited", "100% uptime", "zero downtime",
    "مليون مستخدم", "زمن صفر",
]


class ConflictDetector:
    """Detects conflicting, illogical, impossible, and duplicate
    requirements.

    The detector reads the :class:`Requirement` list and the
    :class:`ContextData` and :class:`GraphData` and produces a list of
    :class:`RequirementConflict` objects.

    The detector does not resolve conflicts — it only detects and
    records them.  The caller decides how to resolve them.
    """

    def __init__(self) -> None:
        self._next_cnf_id = 1

    # ----------------------------------------------------------------- #
    # Main entry point
    # ----------------------------------------------------------------- #

    def detect(
        self,
        requirements: List[Requirement],
        context: ContextData,
        graph: GraphData,
    ) -> List[RequirementConflict]:
        """Detect all conflicts and return a list of
        :class:`RequirementConflict` objects."""
        conflicts: List[RequirementConflict] = []

        conflicts.extend(
            self._detect_duplicates(requirements),
        )
        conflicts.extend(
            self._detect_contradictory_technologies(requirements),
        )
        conflicts.extend(
            self._detect_illogical(requirements, context, graph),
        )
        conflicts.extend(
            self._detect_impossible(requirements),
        )

        return conflicts

    # ----------------------------------------------------------------- #
    # Duplicate detection
    # ----------------------------------------------------------------- #

    def _detect_duplicates(
        self,
        requirements: List[Requirement],
    ) -> List[RequirementConflict]:
        """Detect duplicate requirements (same name or same
        description)."""
        conflicts: List[RequirementConflict] = []
        seen_by_name: Dict[str, List[Requirement]] = {}
        seen_by_desc: Dict[str, List[Requirement]] = {}

        for req in requirements:
            name_key = req.name.lower().strip() if req.name else ""
            if name_key:
                seen_by_name.setdefault(name_key, []).append(req)

            desc_key = req.description.lower().strip() if req.description else ""
            if desc_key and len(desc_key) > 10:
                seen_by_desc.setdefault(desc_key, []).append(req)

        # Detect by name.
        for key, reqs in seen_by_name.items():
            if len(reqs) > 1:
                conflicts.append(RequirementConflict(
                    id=self._next_cnf_id_str(),
                    kind=CONFLICT_DUPLICATE,
                    description=(
                        f"{len(reqs)} requirements share the same name "
                        f"'{reqs[0].name}': "
                        f"{', '.join(r.id for r in reqs)}."
                    ),
                    requirement_ids=[r.id for r in reqs],
                    severity=SEVERITY_WARNING,
                    resolution_hint=(
                        f"Merge the duplicate requirements or give them "
                        f"distinct names."
                    ),
                    source_artefact=reqs[0].source_artefact,
                ))

        # Detect by description (only when names differ).
        for key, reqs in seen_by_desc.items():
            if len(reqs) > 1:
                # Check if they already share a name (already reported).
                names = set(r.name.lower() for r in reqs)
                if len(names) == 1:
                    continue  # Already reported by name.
                conflicts.append(RequirementConflict(
                    id=self._next_cnf_id_str(),
                    kind=CONFLICT_DUPLICATE,
                    description=(
                        f"{len(reqs)} requirements share the same "
                        f"description: "
                        f"{', '.join(r.id for r in reqs)}."
                    ),
                    requirement_ids=[r.id for r in reqs],
                    severity=SEVERITY_WARNING,
                    resolution_hint=(
                        f"Merge the duplicate requirements or "
                        f"differentiate their descriptions."
                    ),
                    source_artefact=reqs[0].source_artefact,
                ))

        return conflicts

    # ----------------------------------------------------------------- #
    # Contradictory technology detection
    # ----------------------------------------------------------------- #

    def _detect_contradictory_technologies(
        self,
        requirements: List[Requirement],
    ) -> List[RequirementConflict]:
        """Detect contradictory technology requirements."""
        conflicts: List[RequirementConflict] = []

        # Group requirements by technology group.
        for group in _CONTRADICTORY_TECH_GROUPS:
            group_reqs: List[Requirement] = []
            for req in requirements:
                req_text = (
                    f"{req.name} {req.description} {req.keywords}"
                ).lower()
                for tech in group:
                    if tech in req_text:
                        group_reqs.append(req)
                        break

            # If more than one requirement references technologies from
            # the same mutually-exclusive group, that's a conflict.
            if len(group_reqs) > 1:
                # Check that they actually reference *different*
                # technologies from the group.
                referenced: Dict[str, List[Requirement]] = {}
                for req in group_reqs:
                    req_text = (
                        f"{req.name} {req.description} {req.keywords}"
                    ).lower()
                    for tech in group:
                        if tech in req_text:
                            referenced.setdefault(tech, []).append(req)
                            break

                if len(referenced) > 1:
                    # We have at least two different technologies from
                    # the same group — that's a contradiction.
                    tech_names = list(referenced.keys())
                    all_ids: List[str] = []
                    for reqs in referenced.values():
                        all_ids.extend(r.id for r in reqs)
                    conflicts.append(RequirementConflict(
                        id=self._next_cnf_id_str(),
                        kind=CONFLICT_CONTRADICTORY,
                        description=(
                            f"Conflicting technology requirements: "
                            f"'{tech_names[0]}' and "
                            f"'{tech_names[1]}' cannot be used "
                            f"together."
                        ),
                        requirement_ids=list(set(all_ids)),
                        severity=SEVERITY_ERROR,
                        resolution_hint=(
                            f"Choose one technology from the "
                            f"mutually-exclusive group: "
                            f"{', '.join(tech_names)}."
                        ),
                        source_artefact=group_reqs[0].source_artefact,
                    ))

        return conflicts

    # ----------------------------------------------------------------- #
    # Illogical detection
    # ----------------------------------------------------------------- #

    def _detect_illogical(
        self,
        requirements: List[Requirement],
        context: ContextData,
        graph: GraphData,
    ) -> List[RequirementConflict]:
        """Detect illogical requirements (requirements that don't make
        sense in the context of the project)."""
        conflicts: List[RequirementConflict] = []

        # If the project has database tables in the graph, but there's
        # a requirement that says "no database", that's illogical.
        has_db_tables = (
            graph.available and bool(graph.database_table_nodes)
        )
        if has_db_tables:
            for req in requirements:
                req_text = (
                    f"{req.name} {req.description}"
                ).lower()
                if "no database" in req_text or "without database" in req_text:
                    conflicts.append(RequirementConflict(
                        id=self._next_cnf_id_str(),
                        kind=CONFLICT_ILLOGICAL,
                        description=(
                            f"Requirement '{req.id}' states no "
                            f"database, but the project has database "
                            f"tables in the intelligence graph."
                        ),
                        requirement_ids=[req.id],
                        severity=SEVERITY_ERROR,
                        resolution_hint=(
                            f"Remove the 'no database' requirement or "
                            f"remove the database tables from the "
                            f"project."
                        ),
                        source_artefact=req.source_artefact,
                    ))

        return conflicts

    # ----------------------------------------------------------------- #
    # Impossible detection
    # ----------------------------------------------------------------- #

    def _detect_impossible(
        self,
        requirements: List[Requirement],
    ) -> List[RequirementConflict]:
        """Detect impossible requirements (requirements that cannot
        be satisfied within the limits of the project)."""
        conflicts: List[RequirementConflict] = []

        for req in requirements:
            req_text = (
                f"{req.name} {req.description} {req.keywords}"
            ).lower()
            for indicator in _IMPOSSIBLE_INDICATORS:
                if indicator in req_text:
                    conflicts.append(RequirementConflict(
                        id=self._next_cnf_id_str(),
                        kind=CONFLICT_IMPOSSIBLE,
                        description=(
                            f"Requirement '{req.id}' contains the "
                            f"impossible indicator '{indicator}', which "
                            f"cannot be satisfied within the limits of "
                            f"a typical bot project."
                        ),
                        requirement_ids=[req.id],
                        severity=SEVERITY_WARNING,
                        resolution_hint=(
                            f"Replace '{indicator}' with a realistic, "
                            f"achievable requirement."
                        ),
                        source_artefact=req.source_artefact,
                    ))
                    break  # Only one impossible per requirement.

        return conflicts

    # ----------------------------------------------------------------- #
    # Internal helpers
    # ----------------------------------------------------------------- #

    def _next_cnf_id_str(self) -> str:
        cnf_id = f"CNF-{self._next_cnf_id:03d}"
        self._next_cnf_id += 1
        return cnf_id


__all__ = ["ConflictDetector"]
