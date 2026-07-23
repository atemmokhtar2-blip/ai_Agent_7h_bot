"""
Core package for the Telegram Bot Generation Engine.

This package defines the foundational contracts that every engine,
builder, and validator must honour.  It contains no generation logic —
only the interfaces, shared types, and the orchestration entry points.
"""

from .context import GenerationContext
from .result import GenerationResult, StageResult, Severity, ValidationReport
from .contracts import (
    Engine,
    Builder,
    Validator,
    PipelineStage,
    Component,
)
from .errors import (
    EngineError,
    EngineExecutionError,
    BuilderError,
    ValidationError,
    PipelineError,
    ConfigurationError,
)
from .bootstrap import bootstrap, build_configuration

__all__ = [
    "GenerationContext",
    "GenerationResult",
    "StageResult",
    "Severity",
    "ValidationReport",
    "Engine",
    "Builder",
    "Validator",
    "PipelineStage",
    "Component",
    "EngineError",
    "EngineExecutionError",
    "BuilderError",
    "ValidationError",
    "PipelineError",
    "ConfigurationError",
    "bootstrap",
    "build_configuration",
]
