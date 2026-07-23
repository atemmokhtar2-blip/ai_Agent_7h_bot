"""
Core bootstrap — assembles the engine from its components.

This module is the *only* place that knows which concrete engines,
builders, and validators to instantiate and register.  It wires the
whole system together using the configuration and returns a ready-to-use
:class:`~telegram_bot_engine.registry.EngineRegistry` and a configured
:class:`~telegram_bot_engine.pipeline.PipelineOrchestrator`.

Keeping the wiring in a single function means:

* Adding a new engine is a one-line change here.
* Tests can build a custom registry by calling ``bootstrap`` with a
  custom configuration or by manually registering components.
* The pipeline never imports concrete engines.
"""

from __future__ import annotations

from typing import Optional

from ..builders import DirectoryBuilder, FileBuilder, PythonModuleBuilder
from ..configuration import ConfigSource, Configuration
from ..configuration.defaults import build_default_schema
from ..engines.generators import (
    AnalyzerEngine,
    BlueprintComposerEngine,
    IntentParserEngine,
    ProjectPlanningEngine,
    BlueprintValidatorEngine,
    StructureGenerationEngine,
    ComponentDetectionEngine,
    FileGenerationPlanningEngine,
)
from ..logging import EngineLogger
from ..manager import CoreEngineManager
from ..output import OutputManager
from ..pipeline import PipelineOrchestrator
from ..registry import EngineRegistry
from ..validators import BlueprintValidator, StructureValidator
from .errors import ConfigurationError


def build_configuration(
    sources: Optional[list] = None,
) -> Configuration:
    """Build a :class:`Configuration` from the default schema and sources.

    ``sources`` is a list of :class:`ConfigSource` instances.  When
    omitted, the defaults and environment are used.
    """
    schema = build_default_schema()
    if sources is None:
        sources = [ConfigSource(name="defaults")]
    return Configuration(schema=schema, sources=sources)


def bootstrap(
    config: Optional[Configuration] = None,
    sources: Optional[list] = None,
) -> tuple:
    """Initialise the whole engine and return (registry, orchestrator).

    Parameters:
        config: An already-built configuration.  When ``None`` a new
            configuration is built from ``sources`` (or defaults).
        sources: Configuration sources used when ``config`` is ``None``.

    Returns:
        A tuple ``(registry, orchestrator, manager)`` ready to generate
        bots.  The ``manager`` is the :class:`CoreEngineManager` that
        governs engine lifecycle, dependencies, and execution order.
    """
    if config is None:
        config = build_configuration(sources=sources)

    EngineLogger.configure(config)

    registry = EngineRegistry()

    # -- builders ----------------------------------------------------------
    directory_builder = DirectoryBuilder()
    file_builder = FileBuilder()
    python_module_builder = PythonModuleBuilder()
    registry.register_builder(directory_builder)
    registry.register_builder(file_builder)
    registry.register_builder(python_module_builder)

    # -- understanding engines ---------------------------------------------
    analyzer = AnalyzerEngine()
    intent_parser = IntentParserEngine()
    blueprint_composer = BlueprintComposerEngine()
    project_planner = ProjectPlanningEngine()
    registry.register_engine(analyzer)
    registry.register_engine(intent_parser)
    registry.register_engine(blueprint_composer)
    registry.register_engine(project_planner)

    # -- understanding engines (validator) -------------------------------
    blueprint_validator = BlueprintValidatorEngine()
    registry.register_engine(blueprint_validator)

    # -- structure generation engine (Specification 006) -----------------
    structure_generator = StructureGenerationEngine()
    registry.register_engine(structure_generator)

    # -- component detection engine (Specification 007) ------------------
    # The component detector scans the blueprint and structure map to
    # detect every software component before code generation begins.
    # It does not write code — it only produces a Component Registry.
    component_detector = ComponentDetectionEngine()
    registry.register_engine(component_detector)

    # -- file generation planning engine (Specification 008) -------------
    # The file planner plans every file the project will contain
    # before any file is created on disk.  It reads the blueprint,
    # validation report, structure map, and component registry, and
    # produces a File Generation Plan.  It does not write code or
    # create files.
    file_planner = FileGenerationPlanningEngine()
    registry.register_engine(file_planner)

    # -- validators --------------------------------------------------------
    registry.register_validator(BlueprintValidator())
    registry.register_validator(StructureValidator())

    # -- Core Engine Manager (Specification 003) --------------------------
    # The manager is the executive brain that governs every engine's
    # lifecycle, dependencies, execution order, and error handling.
    # It is wired here so the pipeline (and any caller) has access to
    # managed execution.  The manager uses the same engine instances
    # already registered with the dumb EngineRegistry.
    manager = CoreEngineManager(config=config)
    manager.register(analyzer, engine_id="analyzer", priority=10,
                     dependencies=[])
    manager.register(intent_parser, engine_id="intent_parser", priority=20,
                     dependencies=["analyzer"])
    manager.register(blueprint_composer, engine_id="blueprint_composer",
                     priority=30, dependencies=["analyzer", "intent_parser"])
    manager.register(project_planner, engine_id="project_planner",
                     priority=40, dependencies=["analyzer"])
    manager.register(blueprint_validator, engine_id="blueprint_validator",
                     priority=50, dependencies=["project_planner"])
    manager.register(structure_generator, engine_id="structure_generator",
                     priority=60, dependencies=["blueprint_validator"])
    manager.register(component_detector, engine_id="component_detector",
                     priority=70, dependencies=["structure_generator"])
    manager.register(file_planner, engine_id="file_planner",
                     priority=80, dependencies=["component_detector"])

    # -- output & pipeline -------------------------------------------------
    output_manager = OutputManager(config=config)
    orchestrator = PipelineOrchestrator(
        registry=registry, output_manager=output_manager, config=config,
    )

    return registry, orchestrator, manager


__all__ = ["bootstrap", "build_configuration"]
