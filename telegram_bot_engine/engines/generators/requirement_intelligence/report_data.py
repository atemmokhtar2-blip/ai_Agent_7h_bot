"""
Requirement Intelligence Report data model (Specification 012).

This module defines the :class:`RequirementIntelligenceReport` — the
complete, authoritative output of the
:class:`~telegram_bot_engine.engines.generators.requirement_intelligence.RequirementIntelligenceEngine`.

The Requirement Intelligence Engine is the engine responsible for
understanding the user's request with the highest possible precision.
It does **not** write code, build the project, or choose libraries.
Its sole function is to understand the user's intent and convert it
into precise, classified, prioritised, quality-validated engineering
requirements.

Data sources
-------------
The engine reads **four** data sources:

1. **User Request** — the raw user message (via the
   ``analysis_report`` artefact produced by the
   :class:`~telegram_bot_engine.engines.generators.analyzer.AnalyzerEngine`,
   or the raw ``context.request``).
2. **Project Context** — the ``project_context`` artefact produced by
   the
   :class:`~telegram_bot_engine.engines.generators.project_context.ProjectContextEngine`.
3. **Project Intelligence Graph** — the ``intelligence_graph``
   artefact produced by the
   :class:`~telegram_bot_engine.engines.generators.intelligence_graph.IntelligenceGraphEngine`.
4. **Knowledge Base** — the ``knowledge_base`` artefact, if present
   (a free-form dictionary of pre-approved assumptions and domain
   knowledge).

Design principles
-----------------
* **Understanding only.**  The engine produces *understanding*, not
  decisions.  It does not write code, create files, choose libraries,
  or make any build decision.  It only converts the user's intent into
  a structured, classified, prioritised, quality-validated report.
* **No guessing.**  When information is missing the engine does **not**
  guess.  It records the missing information as a
  :class:`RequiredQuestion` so the caller can ask the user, or it
  applies a pre-approved assumption from the knowledge base if one is
  explicitly defined.
* **Classification.**  Every requirement is classified into one of
  nine categories: functional, non-functional, performance, security,
  architecture, testing, deployment, future-expansion, and
  implicit.
* **Priority.**  Every requirement has a priority (``"critical"``,
  ``"high"``, ``"normal"``, ``"low"``) and a numeric rank used for
  ordering.  Priorities are assigned by the Priority Assigner based on
  importance, dependencies, and impact on the rest of the system.
* **Quality rules.**  No requirement may exist without a description,
  a goal, a reason, and a priority.  The Quality Validator enforces
  this rule and records violations as findings.
* **Traceability.**  Every requirement records the data source it was
  derived from (``source_artefact``) so any downstream decision can
  trace its data back to the original source.
* **Conflict detection.**  The engine detects conflicting
  requirements, illogical requirements, impossible requirements (within
  the project's limits), and duplicate requirements.
* **Implicit requirement discovery.**  The engine discovers
  requirements the user did not explicitly state but that are implied
  by the stated requirements or by the project context.

The report is a plain data container — no logic lives here.  The
engine and its helpers populate it; downstream consumers (the
generators, the manager, tests) read it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------#
# Source-artefact constants
# ---------------------------------------------------------------------------#
#
# Every requirement records the data source it was derived from.  These
# constants are the stable identifiers for the four data sources.

SOURCE_USER_REQUEST = "user_request"
SOURCE_PROJECT_CONTEXT = "project_context"
SOURCE_INTELLIGENCE_GRAPH = "intelligence_graph"
SOURCE_KNOWLEDGE_BASE = "knowledge_base"

ALL_SOURCES = (
    SOURCE_USER_REQUEST,
    SOURCE_PROJECT_CONTEXT,
    SOURCE_INTELLIGENCE_GRAPH,
    SOURCE_KNOWLEDGE_BASE,
)


# ---------------------------------------------------------------------------#
# Severity constants
# ---------------------------------------------------------------------------#

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"

ALL_SEVERITIES = (SEVERITY_ERROR, SEVERITY_WARNING, SEVERITY_INFO)


# ---------------------------------------------------------------------------#
# Requirement category constants
# ---------------------------------------------------------------------------#
#
# The nine categories into which requirements are classified.

CATEGORY_FUNCTIONAL = "functional"
CATEGORY_NON_FUNCTIONAL = "non_functional"
CATEGORY_PERFORMANCE = "performance"
CATEGORY_SECURITY = "security"
CATEGORY_ARCHITECTURE = "architecture"
CATEGORY_TESTING = "testing"
CATEGORY_DEPLOYMENT = "deployment"
CATEGORY_FUTURE_EXPANSION = "future_expansion"
CATEGORY_IMPLICIT = "implicit"

ALL_CATEGORIES = (
    CATEGORY_FUNCTIONAL,
    CATEGORY_NON_FUNCTIONAL,
    CATEGORY_PERFORMANCE,
    CATEGORY_SECURITY,
    CATEGORY_ARCHITECTURE,
    CATEGORY_TESTING,
    CATEGORY_DEPLOYMENT,
    CATEGORY_FUTURE_EXPANSION,
    CATEGORY_IMPLICIT,
)

# Human-readable display names for each category.
CATEGORY_DISPLAY_NAMES = {
    CATEGORY_FUNCTIONAL: "Functional Requirements",
    CATEGORY_NON_FUNCTIONAL: "Non-Functional Requirements",
    CATEGORY_PERFORMANCE: "Performance Requirements",
    CATEGORY_SECURITY: "Security Requirements",
    CATEGORY_ARCHITECTURE: "Architecture Requirements",
    CATEGORY_TESTING: "Testing Requirements",
    CATEGORY_DEPLOYMENT: "Deployment Requirements",
    CATEGORY_FUTURE_EXPANSION: "Future Expansion Requirements",
    CATEGORY_IMPLICIT: "Implicit Requirements",
}


# ---------------------------------------------------------------------------#
# Priority constants
# ---------------------------------------------------------------------------#
#
# Every requirement has a priority level and a numeric rank.  The
# priority level is a human-readable label; the rank is a number used
# for sorting (lower rank = higher priority).

PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_NORMAL = "normal"
PRIORITY_LOW = "low"

ALL_PRIORITIES = (
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_NORMAL,
    PRIORITY_LOW,
)

# Numeric ranks for each priority level (used for sorting).
PRIORITY_RANKS = {
    PRIORITY_CRITICAL: 10,
    PRIORITY_HIGH: 20,
    PRIORITY_NORMAL: 30,
    PRIORITY_LOW: 40,
}


# ---------------------------------------------------------------------------#
# Intent analysis constants
# ---------------------------------------------------------------------------#
#
# The Intent Analysis section captures the five dimensions the engine
# understands about the user's intent.

INTENT_DIMENSION_WANTS = "wants"
INTENT_DIMENSION_DOES_NOT_WANT = "does_not_want"
INTENT_DIMENSION_FINAL_GOAL = "final_goal"
INTENT_DIMENSION_CONSTRAINTS = "constraints"
INTENT_DIMENSION_QUALITY_LEVEL = "quality_level"

ALL_INTENT_DIMENSIONS = (
    INTENT_DIMENSION_WANTS,
    INTENT_DIMENSION_DOES_NOT_WANT,
    INTENT_DIMENSION_FINAL_GOAL,
    INTENT_DIMENSION_CONSTRAINTS,
    INTENT_DIMANTITY_LEVEL := INTENT_DIMENSION_QUALITY_LEVEL,
) if False else (
    INTENT_DIMENSION_WANTS,
    INTENT_DIMENSION_DOES_NOT_WANT,
    INTENT_DIMENSION_FINAL_GOAL,
    INTENT_DIMENSION_CONSTRAINTS,
    INTENT_DIMENSION_QUALITY_LEVEL,
)

# Quality levels the user may require.
QUALITY_LEVEL_MINIMAL = "minimal"
QUALITY_LEVEL_STANDARD = "standard"
QUALITY_LEVEL_HIGH = "high"
QUALITY_LEVEL_PRODUCTION = "production"

ALL_QUALITY_LEVELS = (
    QUALITY_LEVEL_MINIMAL,
    QUALITY_LEVEL_STANDARD,
    QUALITY_LEVEL_HIGH,
    QUALITY_LEVEL_PRODUCTION,
)


# ---------------------------------------------------------------------------#
# Conflict kind constants
# ---------------------------------------------------------------------------#

CONFLICT_CONTRADICTORY = "contradictory"
CONFLICT_ILLOGICAL = "illogical"
CONFLICT_IMPOSSIBLE = "impossible"
CONFLICT_DUPLICATE = "duplicate"

ALL_CONFLICT_KINDS = (
    CONFLICT_CONTRADICTORY,
    CONFLICT_ILLOGICAL,
    CONFLICT_IMPOSSIBLE,
    CONFLICT_DUPLICATE,
)


# ---------------------------------------------------------------------------#
# Ambiguity kind constants
# ---------------------------------------------------------------------------#

AMBIGUITY_VAGUE = "vague"
AMBIGUITY_UNDER_SPECIFIED = "under_specified"
AMBIGUITY_MULTIPLE_INTERPRETATIONS = "multiple_interpretations"
AMBIGUITY_MISSING_CONTEXT = "missing_context"

ALL_AMBIGUITY_KINDS = (
    AMBIGUITY_VAGUE,
    AMBIGUITY_UNDER_SPECIFIED,
    AMBIGUITY_MULTIPLE_INTERPRETATIONS,
    AMBIGUITY_MISSING_CONTEXT,
)


# ---------------------------------------------------------------------------#
# Intent dimension
# ---------------------------------------------------------------------------#

@dataclass
class IntentDimension:
    """A single dimension of the user's intent.

    The Intent Analysis section captures five dimensions:

    * **wants** — what the user wants (the desired outcome).
    * **does_not_want** — what the user explicitly does not want
      (constraints, exclusions, anti-requirements).
    * **final_goal** — the ultimate goal the user is trying to achieve.
    * **constraints** — the limitations and boundaries within which
      the solution must operate.
    * **quality_level** — the level of quality the user expects
      (minimal, standard, high, or production).

    Attributes:
        name: The dimension name (one of the ``INTENT_DIMENSION_*``
            constants).
        value: The dimension value (free text for the first four;
            one of the ``QUALITY_LEVEL_*`` constants for
            ``quality_level``).
        confidence: 0.0–1.0 confidence that the dimension was
            correctly understood.
        evidence: The evidence (keywords, phrases, or artefact
            references) that led to this understanding.
        source_artefact: The artefact this dimension was derived
            from (one of the ``SOURCE_*`` constants).
    """

    name: str = ""
    value: str = ""
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_USER_REQUEST

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Intent analysis
# ---------------------------------------------------------------------------#

@dataclass
class IntentAnalysis:
    """The complete intent analysis.

    This captures the five dimensions of the user's intent as
    understood by the engine.

    Attributes:
        wants: What the user wants (the desired outcome).
        does_not_want: What the user does not want (exclusions,
            anti-requirements).
        final_goal: The ultimate goal the user is trying to achieve.
        constraints: The limitations and boundaries.
        quality_level: The quality level the user expects (one of
            the ``QUALITY_LEVEL_*`` constants).
        dimensions: The full list of :class:`IntentDimension`
            objects (for traceability).
        confidence: The overall confidence in the intent analysis
            (0.0–1.0).
    """

    wants: str = ""
    does_not_want: str = ""
    final_goal: str = ""
    constraints: str = ""
    quality_level: str = QUALITY_LEVEL_STANDARD
    dimensions: List[IntentDimension] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wants": self.wants,
            "does_not_want": self.does_not_want,
            "final_goal": self.final_goal,
            "constraints": self.constraints,
            "quality_level": self.quality_level,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "confidence": self.confidence,
        }


# ---------------------------------------------------------------------------#
# Requirement
# ---------------------------------------------------------------------------#

@dataclass
class Requirement:
    """A single, atomic engineering requirement.

    This is the fundamental unit of the Requirement Intelligence
    Report.  Every requirement is atomic — it describes a single,
    independent need.  Composite needs are split into multiple
    requirements.

    Quality rules: no requirement may exist without a description,
    a goal, a reason, and a priority.  The Quality Validator
    enforces this.

    Attributes:
        id: A unique, machine-readable identifier (e.g.
            ``"REQ-001"``).
        name: A short, machine-friendly name (e.g.
            ``"command_handling"``).
        display_name: A human-readable name.
        description: A full description of what the requirement is.
        goal: The goal this requirement achieves (why it exists
            from the user's perspective).
        reason: The reason this requirement is needed (the
            engineering rationale).
        category: The requirement category (one of the
            ``CATEGORY_*`` constants).
        priority: The priority level (one of the
            ``PRIORITY_*`` constants).
        priority_rank: The numeric rank used for sorting (lower
            = higher priority).
        source_artefact: The artefact this requirement was
            derived from (one of the ``SOURCE_*`` constants).
        confidence: 0.0–1.0 confidence that the requirement was
            correctly identified.
        evidence: The evidence (keywords, phrases, or artefact
            references) that led to this requirement.
        depends_on: The IDs of other requirements this one
            depends on.
        depended_by: The IDs of requirements that depend on this
            one.
        is_implicit: ``True`` when this requirement was not
            explicitly stated by the user but was inferred from
            the stated requirements or the project context.
        is_assumption: ``True`` when this requirement was derived
            from a pre-approved assumption in the knowledge base.
        acceptance_criteria: The conditions that must be met for
            this requirement to be considered satisfied.
        keywords: The keywords that triggered this requirement.
    """

    id: str = ""
    name: str = ""
    display_name: str = ""
    description: str = ""
    goal: str = ""
    reason: str = ""
    category: str = CATEGORY_FUNCTIONAL
    priority: str = PRIORITY_NORMAL
    priority_rank: int = PRIORITY_RANKS[PRIORITY_NORMAL]
    source_artefact: str = SOURCE_USER_REQUEST
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    depended_by: List[str] = field(default_factory=list)
    is_implicit: bool = False
    is_assumption: bool = False
    acceptance_criteria: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Sync ``priority_rank`` from ``priority`` when not set.

        When a :class:`Requirement` is constructed with an explicit
        ``priority`` but no explicit ``priority_rank``, the rank is
        automatically derived from the priority level.
        """
        if self.priority in PRIORITY_RANKS:
            self.priority_rank = PRIORITY_RANKS[self.priority]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "goal": self.goal,
            "reason": self.reason,
            "category": self.category,
            "priority": self.priority,
            "priority_rank": self.priority_rank,
            "source_artefact": self.source_artefact,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "depends_on": list(self.depends_on),
            "depended_by": list(self.depended_by),
            "is_implicit": self.is_implicit,
            "is_assumption": self.is_assumption,
            "acceptance_criteria": list(self.acceptance_criteria),
            "keywords": list(self.keywords),
        }


# ---------------------------------------------------------------------------#
# Required question
# ---------------------------------------------------------------------------#

@dataclass
class RequiredQuestion:
    """A question that must be answered to resolve missing information.

    When the engine detects missing information it does **not** guess.
    Instead it records a :class:`RequiredQuestion` so the caller can
    ask the user, or apply a pre-approved assumption if one exists in
    the knowledge base.

    Attributes:
        id: A unique, machine-readable identifier (e.g.
            ``"Q-001"``).
        field_name: The field that is missing (e.g.
            ``"database_choice"``).
        question: The question to ask the user.
        options: Suggested options for the answer.
        default: A default value if the user does not answer (may
            be ``None`` when there is no sensible default).
        required: Whether this question must be answered to
            proceed.
        related_requirements: The IDs of the requirements that
            are affected by this question.
        source_artefact: The artefact this question was derived
            from.
        resolution: The resolution applied (``"user"``,
            ``"assumption"``, or empty when unresolved).
        resolved_value: The value used to resolve the question,
            if any.
    """

    id: str = ""
    field_name: str = ""
    question: str = ""
    options: List[str] = field(default_factory=list)
    default: Any = None
    required: bool = True
    related_requirements: List[str] = field(default_factory=list)
    source_artefact: str = SOURCE_USER_REQUEST
    resolution: str = ""
    resolved_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "field_name": self.field_name,
            "question": self.question,
            "options": list(self.options),
            "default": self.default,
            "required": self.required,
            "related_requirements": list(self.related_requirements),
            "source_artefact": self.source_artefact,
            "resolution": self.resolution,
            "resolved_value": self.resolved_value,
        }


# ---------------------------------------------------------------------------#
# Ambiguity point
# ---------------------------------------------------------------------------#

@dataclass
class AmbiguityPoint:
    """A point of ambiguity detected in the user's request.

    Attributes:
        id: A unique, machine-readable identifier (e.g.
            ``"AMB-001"``).
        kind: The ambiguity kind (one of the
            ``AMBIGUITY_*`` constants).
        description: A human-readable description of the
            ambiguity.
        affected_text: The text in the user's request that is
            ambiguous.
        possible_interpretations: The possible interpretations
            of the ambiguous text.
        related_requirements: The IDs of the requirements
            affected by this ambiguity.
        resolution_hint: An optional suggestion on how to
            resolve the ambiguity.
        source_artefact: The artefact this ambiguity was
            derived from.
    """

    id: str = ""
    kind: str = AMBIGUITY_VAGUE
    description: str = ""
    affected_text: str = ""
    possible_interpretations: List[str] = field(default_factory=list)
    related_requirements: List[str] = field(default_factory=list)
    resolution_hint: str = ""
    source_artefact: str = SOURCE_USER_REQUEST

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "description": self.description,
            "affected_text": self.affected_text,
            "possible_interpretations": list(self.possible_interpretations),
            "related_requirements": list(self.related_requirements),
            "resolution_hint": self.resolution_hint,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Requirement conflict
# ---------------------------------------------------------------------------#

@dataclass
class RequirementConflict:
    """A conflict between two or more requirements.

    The engine detects four kinds of conflicts:

    * **contradictory** — two requirements that cannot both be true.
    * **illogical** — a requirement that does not make sense in the
      context of the project.
    * **impossible** — a requirement that cannot be satisfied within
      the limits of the project.
    * **duplicate** — two requirements that describe the same need.

    Attributes:
        id: A unique, machine-readable identifier (e.g.
            ``"CNF-001"``).
        kind: The conflict kind (one of the ``CONFLICT_*``
            constants).
        description: A human-readable description of the
            conflict.
        requirement_ids: The IDs of the requirements involved in
            the conflict.
        severity: ``"error"`` or ``"warning"``.
        resolution_hint: An optional suggestion on how to
            resolve the conflict.
        source_artefact: The artefact this conflict was derived
            from.
    """

    id: str = ""
    kind: str = CONFLICT_CONTRADICTORY
    description: str = ""
    requirement_ids: List[str] = field(default_factory=list)
    severity: str = SEVERITY_ERROR
    resolution_hint: str = ""
    source_artefact: str = SOURCE_USER_REQUEST

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "description": self.description,
            "requirement_ids": list(self.requirement_ids),
            "severity": self.severity,
            "resolution_hint": self.resolution_hint,
            "source_artefact": self.source_artefact,
        }


# ---------------------------------------------------------------------------#
# Quality violation
# ---------------------------------------------------------------------------#

@dataclass
class QualityViolation:
    """A violation of the quality rules.

    The Quality Rules state that no requirement may exist without a
    description, a goal, a reason, and a priority.  The Quality
    Validator enforces this and records violations here.

    Attributes:
        requirement_id: The ID of the requirement that violates
            the quality rules.
        missing_fields: The fields that are missing or empty
            (subset of ``"description"``, ``"goal"``, ``"reason"``,
            ``"priority"``).
        severity: ``"error"`` or ``"warning"``.
        message: A human-readable description of the violation.
    """

    requirement_id: str = ""
    missing_fields: List[str] = field(default_factory=list)
    severity: str = SEVERITY_ERROR
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "requirement_id": self.requirement_id,
            "missing_fields": list(self.missing_fields),
            "severity": self.severity,
            "message": self.message,
        }


# ---------------------------------------------------------------------------#
# Report finding
# ---------------------------------------------------------------------------#

@dataclass
class ReportFinding:
    """A general finding produced during report building or
    validation.

    Attributes:
        severity: ``"error"``, ``"warning"``, or ``"info"``.
        code: A short, machine-readable code (e.g.
            ``"missing_intent"``).
        message: A human-readable description.
        affected: The name of the affected element.
        resolution_hint: An optional suggestion on how to fix
            the issue.
        category: The finding category (``"intent"``,
            ``"classification"``, ``"missing"``, ``"conflict"``,
            ``"priority"``, ``"quality"``).
    """

    severity: str = SEVERITY_WARNING
    code: str = ""
    message: str = ""
    affected: str = ""
    resolution_hint: str = ""
    category: str = "validation"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "affected": self.affected,
            "resolution_hint": self.resolution_hint,
            "category": self.category,
        }


# ---------------------------------------------------------------------------#
# Source provenance
# ---------------------------------------------------------------------------#

@dataclass
class ReportProvenance:
    """Records which data sources were used to build the report.

    This is the traceability record: any decision taken by a
    downstream engine can trace its data back to the original source.

    Attributes:
        request_available: Whether the user request was available.
        project_context_available: Whether the project context
            was available.
        intelligence_graph_available: Whether the intelligence
            graph was available.
        knowledge_base_available: Whether the knowledge base was
            available.
        all_sources_used: The list of all source artefact
            identifiers that contributed to the report.
        request_summary: A short summary of the user request.
        context_project_name: The project name from the project
            context, if available.
        graph_node_count: The number of nodes in the intelligence
            graph, if available.
        knowledge_base_keys: The keys in the knowledge base, if
            available.
    """

    request_available: bool = False
    project_context_available: bool = False
    intelligence_graph_available: bool = False
    knowledge_base_available: bool = False
    all_sources_used: List[str] = field(default_factory=list)
    request_summary: str = ""
    context_project_name: str = ""
    graph_node_count: int = 0
    knowledge_base_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_available": self.request_available,
            "project_context_available": self.project_context_available,
            "intelligence_graph_available": self.intelligence_graph_available,
            "knowledge_base_available": self.knowledge_base_available,
            "all_sources_used": list(self.all_sources_used),
            "request_summary": self.request_summary,
            "context_project_name": self.context_project_name,
            "graph_node_count": self.graph_node_count,
            "knowledge_base_keys": list(self.knowledge_base_keys),
        }


# ---------------------------------------------------------------------------#
# The full Requirement Intelligence Report
# ---------------------------------------------------------------------------#

@dataclass
class RequirementIntelligenceReport:
    """The complete, authoritative output of the Requirement
    Intelligence Engine.

    This is the **only** object the engine produces.  It is stored in
    the generation context as the
    ``requirement_intelligence_report`` artefact.

    The report is **read-only** for all downstream engines — no engine
    may modify it directly.  Any modification requires a dedicated
    engine.

    The report is the **single reference point** for the user's
    understood requirements.  Instead of re-reading the four data
    sources, every downstream engine reads this report.

    Attributes:
        intent: The :class:`IntentAnalysis` — the five-dimension
            intent analysis.
        requirements: The list of all :class:`Requirement` objects.
        required_questions: The list of :class:`RequiredQuestion`
            objects (missing information that must be answered).
        ambiguities: The list of :class:`AmbiguityPoint` objects
            (points of ambiguity).
        conflicts: The list of :class:`RequirementConflict`
            objects (conflicting, illogical, impossible, or
            duplicate requirements).
        quality_violations: The list of :class:`QualityViolation`
            objects (quality rule violations).
        findings: The list of :class:`ReportFinding` objects
            produced during report building and validation.
        provenance: The :class:`ReportProvenance` — traceability
            record.
        summary: A human-readable summary.
        notes: General notes about the report.
        warnings: Warnings produced during report building.
    """

    intent: IntentAnalysis = field(default_factory=IntentAnalysis)
    requirements: List[Requirement] = field(default_factory=list)
    required_questions: List[RequiredQuestion] = field(default_factory=list)
    ambiguities: List[AmbiguityPoint] = field(default_factory=list)
    conflicts: List[RequirementConflict] = field(default_factory=list)
    quality_violations: List[QualityViolation] = field(default_factory=list)
    findings: List[ReportFinding] = field(default_factory=list)
    provenance: ReportProvenance = field(default_factory=ReportProvenance)
    summary: str = ""
    notes: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    # -- convenience -------------------------------------------------------#

    @property
    def requirement_count(self) -> int:
        return len(self.requirements)

    @property
    def question_count(self) -> int:
        return len(self.required_questions)

    @property
    def ambiguity_count(self) -> int:
        return len(self.ambiguities)

    @property
    def conflict_count(self) -> int:
        return len(self.conflicts)

    @property
    def quality_violation_count(self) -> int:
        return len(self.quality_violations)

    @property
    def implicit_count(self) -> int:
        return sum(1 for r in self.requirements if r.is_implicit)

    @property
    def explicit_count(self) -> int:
        return sum(1 for r in self.requirements if not r.is_implicit)

    @property
    def is_empty(self) -> bool:
        return self.requirement_count == 0

    @property
    def has_errors(self) -> bool:
        return (
            any(f.severity == SEVERITY_ERROR for f in self.findings)
            or any(c.severity == SEVERITY_ERROR for c in self.conflicts)
            or any(
                v.severity == SEVERITY_ERROR
                for v in self.quality_violations
            )
        )

    @property
    def error_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == SEVERITY_ERROR
        )

    @property
    def warning_count(self) -> int:
        return sum(
            1 for f in self.findings if f.severity == SEVERITY_WARNING
        )

    @property
    def has_unresolved_questions(self) -> bool:
        return any(
            q.required and not q.resolution
            for q in self.required_questions
        )

    @property
    def ready(self) -> bool:
        """``True`` when the report is complete enough to proceed.

        The report is ready when:
        * It has at least one requirement.
        * It has no error-level conflicts.
        * It has no quality violations.
        * It has no unresolved required questions.
        """
        return (
            self.requirement_count > 0
            and not any(
                c.severity == SEVERITY_ERROR for c in self.conflicts
            )
            and self.quality_violation_count == 0
            and not self.has_unresolved_questions
        )

    # -- categorisation helpers -------------------------------------------#

    def requirements_by_category(
        self, category: str,
    ) -> List[Requirement]:
        """Return all requirements in a given category."""
        return [r for r in self.requirements if r.category == category]

    def requirements_by_priority(
        self, priority: str,
    ) -> List[Requirement]:
        """Return all requirements with a given priority level."""
        return [r for r in self.requirements if r.priority == priority]

    def sorted_requirements(self) -> List[Requirement]:
        """Return all requirements sorted by priority rank then id."""
        return sorted(
            self.requirements,
            key=lambda r: (r.priority_rank, r.id),
        )

    def category_counts(self) -> Dict[str, int]:
        """Return a mapping of category → count."""
        counts: Dict[str, int] = {}
        for r in self.requirements:
            counts[r.category] = counts.get(r.category, 0) + 1
        return counts

    def priority_counts(self) -> Dict[str, int]:
        """Return a mapping of priority → count."""
        counts: Dict[str, int] = {}
        for r in self.requirements:
            counts[r.priority] = counts.get(r.priority, 0) + 1
        return counts

    def source_counts(self) -> Dict[str, int]:
        """Return a mapping of source artefact → count."""
        counts: Dict[str, int] = {}
        for r in self.requirements:
            counts[r.source_artefact] = (
                counts.get(r.source_artefact, 0) + 1
            )
        return counts

    # -- look-up helpers --------------------------------------------------#

    def get_requirement(self, req_id: str) -> Optional[Requirement]:
        """Return the requirement with the given id, or ``None``."""
        for r in self.requirements:
            if r.id == req_id:
                return r
        return None

    def get_requirement_by_name(
        self, name: str,
    ) -> Optional[Requirement]:
        """Return the requirement with the given name, or ``None``."""
        for r in self.requirements:
            if r.name == name:
                return r
        return None

    # -- finding management -----------------------------------------------#

    def add_finding(
        self,
        severity: str,
        code: str,
        message: str,
        affected: str = "",
        resolution_hint: str = "",
        category: str = "validation",
    ) -> None:
        """Add a finding to the report."""
        self.findings.append(ReportFinding(
            severity=severity,
            code=code,
            message=message,
            affected=affected,
            resolution_hint=resolution_hint,
            category=category,
        ))
        if severity == SEVERITY_WARNING:
            self.warnings.append(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.to_dict(),
            "requirement_count": self.requirement_count,
            "explicit_count": self.explicit_count,
            "implicit_count": self.implicit_count,
            "question_count": self.question_count,
            "ambiguity_count": self.ambiguity_count,
            "conflict_count": self.conflict_count,
            "quality_violation_count": self.quality_violation_count,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "ready": self.ready,
            "category_counts": self.category_counts(),
            "priority_counts": self.priority_counts(),
            "source_counts": self.source_counts(),
            "summary": self.summary,
            "notes": list(self.notes),
            "warnings": list(self.warnings),
            "requirements": [r.to_dict() for r in self.requirements],
            "required_questions": [
                q.to_dict() for q in self.required_questions
            ],
            "ambiguities": [a.to_dict() for a in self.ambiguities],
            "conflicts": [c.to_dict() for c in self.conflicts],
            "quality_violations": [
                v.to_dict() for v in self.quality_violations
            ],
            "findings": [f.to_dict() for f in self.findings],
            "provenance": self.provenance.to_dict(),
        }


__all__ = [
    # Source-artefact constants
    "SOURCE_USER_REQUEST",
    "SOURCE_PROJECT_CONTEXT",
    "SOURCE_INTELLIGENCE_GRAPH",
    "SOURCE_KNOWLEDGE_BASE",
    "ALL_SOURCES",
    # Severity constants
    "SEVERITY_ERROR",
    "SEVERITY_WARNING",
    "SEVERITY_INFO",
    "ALL_SEVERITIES",
    # Requirement category constants
    "CATEGORY_FUNCTIONAL",
    "CATEGORY_NON_FUNCTIONAL",
    "CATEGORY_PERFORMANCE",
    "CATEGORY_SECURITY",
    "CATEGORY_ARCHITECTURE",
    "CATEGORY_TESTING",
    "CATEGORY_DEPLOYMENT",
    "CATEGORY_FUTURE_EXPANSION",
    "CATEGORY_IMPLICIT",
    "ALL_CATEGORIES",
    "CATEGORY_DISPLAY_NAMES",
    # Priority constants
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_NORMAL",
    "PRIORITY_LOW",
    "ALL_PRIORITIES",
    "PRIORITY_RANKS",
    # Intent dimension constants
    "INTENT_DIMENSION_WANTS",
    "INTENT_DIMENSION_DOES_NOT_WANT",
    "INTENT_DIMENSION_FINAL_GOAL",
    "INTENT_DIMENSION_CONSTRAINTS",
    "INTENT_DIMENSION_QUALITY_LEVEL",
    "ALL_INTENT_DIMENSIONS",
    # Quality level constants
    "QUALITY_LEVEL_MINIMAL",
    "QUALITY_LEVEL_STANDARD",
    "QUALITY_LEVEL_HIGH",
    "QUALITY_LEVEL_PRODUCTION",
    "ALL_QUALITY_LEVELS",
    # Conflict kind constants
    "CONFLICT_CONTRADICTORY",
    "CONFLICT_ILLOGICAL",
    "CONFLICT_IMPOSSIBLE",
    "CONFLICT_DUPLICATE",
    "ALL_CONFLICT_KINDS",
    # Ambiguity kind constants
    "AMBIGUITY_VAGUE",
    "AMBIGUITY_UNDER_SPECIFIED",
    "AMBIGUITY_MULTIPLE_INTERPRETATIONS",
    "AMBIGUITY_MISSING_CONTEXT",
    "ALL_AMBIGUITY_KINDS",
    # Data model
    "IntentDimension",
    "IntentAnalysis",
    "Requirement",
    "RequiredQuestion",
    "AmbiguityPoint",
    "RequirementConflict",
    "QualityViolation",
    "ReportFinding",
    "ReportProvenance",
    "RequirementIntelligenceReport",
]
