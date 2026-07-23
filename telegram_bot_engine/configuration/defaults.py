"""
Default configuration schema for the Telegram Bot Generation Engine.

This module assembles the :class:`~configuration.schema.ConfigSchema` that
describes every option the engine understands.  It is the single place
where new configuration knobs are declared.

Engines should never reference this module directly — they receive a
:class:`~configuration.config.Configuration` object at construction time.
"""

from __future__ import annotations

from .schema import ConfigSchema, FieldSchema, SectionSchema


def build_default_schema() -> ConfigSchema:
    """Construct and return the default engine configuration schema."""

    logging_section = SectionSchema(
        name="logging",
        description="Controls how the engine records every step it performs.",
        fields=[
            FieldSchema(
                name="level",
                type=str,
                default="INFO",
                description="Minimum severity of log messages to emit.",
                choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            ),
            FieldSchema(
                name="format",
                type=str,
                default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                description="Format string for log records.",
            ),
            FieldSchema(
                name="log_dir",
                type=str,
                default="logs",
                description="Directory where log files are written.",
            ),
            FieldSchema(
                name="to_file",
                type=bool,
                default=True,
                description="Whether to write logs to a file.",
            ),
            FieldSchema(
                name="to_console",
                type=bool,
                default=True,
                description="Whether to emit logs to the console.",
            ),
        ],
    )

    pipeline_section = SectionSchema(
        name="pipeline",
        description="Controls the generation pipeline behaviour.",
        fields=[
            FieldSchema(
                name="fail_fast",
                type=bool,
                default=True,
                description=(
                    "When True the pipeline stops at the first failing "
                    "stage.  When False it collects all errors."
                ),
            ),
            FieldSchema(
                name="max_parallel_stages",
                type=int,
                default=1,
                description=(
                    "Maximum number of stages that may run concurrently. "
                    "Most stages must run sequentially."
                ),
                validator=lambda v: v >= 1,
            ),
            FieldSchema(
                name="continue_on_validation_warning",
                type=bool,
                default=False,
                description=(
                    "When True the pipeline continues even if a validator "
                    "produces warnings (not errors)."
                ),
            ),
        ],
    )

    output_section = SectionSchema(
        name="output",
        description="Controls how the final generated project is packaged.",
        fields=[
            FieldSchema(
                name="base_dir",
                type=str,
                default="output",
                description=(
                    "Root directory where generated projects are written."
                ),
            ),
            FieldSchema(
                name="project_prefix",
                type=str,
                default="bot_project",
                description=(
                    "Prefix used when generating unique project directory "
                    "names."
                ),
            ),
            FieldSchema(
                name="clean_before_build",
                type=bool,
                default=True,
                description=(
                    "When True the target directory is removed before a "
                    "new build starts."
                ),
            ),
            FieldSchema(
                name="create_zip",
                type=bool,
                default=True,
                description="Whether to create a zip archive of the result.",
            ),
        ],
    )

    registry_section = SectionSchema(
        name="registry",
        description="Controls how engines and builders are discovered.",
        fields=[
            FieldSchema(
                name="auto_discover",
                type=bool,
                default=True,
                description=(
                    "When True the registry scans known packages for "
                    "registered components."
                ),
            ),
            FieldSchema(
                name="engine_packages",
                type=str,
                default="telegram_bot_engine.engines.generators",
                description=(
                    "Comma-separated list of packages to scan for engine "
                    "implementations."
                ),
            ),
        ],
    )

    engine_section = SectionSchema(
        name="engine",
        description="Global defaults applied to individual generation engines.",
        fields=[
            FieldSchema(
                name="default_language",
                type=str,
                default="python",
                description="Programming language of generated bots.",
                choices=["python"],
            ),
            FieldSchema(
                name="default_python_version",
                type=str,
                default="3.11",
                description="Python version targeted by generated projects.",
            ),
            FieldSchema(
                name="default_framework",
                type=str,
                default="python-telegram-bot",
                description="Telegram library used in generated projects.",
            ),
        ],
    )

    return ConfigSchema(
        sections=[
            logging_section,
            pipeline_section,
            output_section,
            registry_section,
            engine_section,
        ],
    )


__all__ = ["build_default_schema"]
