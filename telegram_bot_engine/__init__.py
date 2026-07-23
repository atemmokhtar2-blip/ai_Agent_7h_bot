"""
Telegram Bot Generation Engine
==============================

A modular engine that generates complete Telegram bot projects from a
natural-language description.  The engine is not a bot itself — it is a
factory that builds bots.

Architecture
------------
The system is composed of independent layers:

* **Configuration** — centralised, schema-validated settings.  No engine
  hardcodes values.
* **Logging** — every step is recorded for traceability.
* **Blueprint** — the intermediate representation of a bot, the contract
  between the "understanding" and "building" phases.
* **Engines** — generators that transform a blueprint into project files.
  Each engine has a single responsibility.
* **Builders** — the only components that write files to disk.
* **Validators** — components that verify artefacts at each stage.
* **Pipeline** — the ordered path a request follows, with fail-fast
  semantics.
* **Registry** — the central catalogue of all components.
* **Output** — assembles and packages the final deliverable.
* **Core** — bootstrap that wires everything together.

Quick start
-----------
::

    from telegram_bot_engine import bootstrap, generate_bot

    result = generate_bot("اعمل بوت متجر إلكتروني")
    print(result.project_path)

See :func:`generate_bot` for the high-level entry point.
"""

from .core import bootstrap, build_configuration
from .pipeline import PipelineOrchestrator
from .registry import EngineRegistry


def generate_bot(request: str, work_dir=None):
    """Generate a complete Telegram bot project from a description.

    This is the main entry point.  It bootstraps the engine, runs the
    full pipeline, and returns a :class:`~core.result.GenerationResult`.

    Parameters:
        request: A natural-language description of the desired bot.
        work_dir: Optional override for the working directory.

    Returns:
        A :class:`GenerationResult` with the outcome and project path.
    """
    _registry, orchestrator, _manager = bootstrap()
    return orchestrator.run(request, work_dir=work_dir)


__all__ = [
    "bootstrap",
    "build_configuration",
    "generate_bot",
    "PipelineOrchestrator",
    "EngineRegistry",
]
