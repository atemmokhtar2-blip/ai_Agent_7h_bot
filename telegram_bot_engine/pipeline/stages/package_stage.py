"""
Package stage — assembles the final deliverable.

This stage hands off to the :class:`~telegram_bot_engine.output.OutputManager`
which:

* Verifies the generated project structure.
* Optionally creates a zip archive.
* Returns the final project path.

The stage never writes files directly — it uses the output manager.
"""

from __future__ import annotations

from typing import List

from ...core.context import GenerationContext
from ...core.result import StageResult
from ...output import OutputManager
from ..base_stage import BaseStage


class PackageStage(BaseStage):
    """Packages the generated project into the final deliverable."""

    stage_name = "package"
    requires: List[str] = ["generated_files", "output_validation_reports"]
    provides: List[str] = ["final_project"]

    def __init__(self, output_manager: OutputManager) -> None:
        super().__init__()
        self._output_manager = output_manager

    def execute(self, context: GenerationContext) -> StageResult:
        # Check that the output validation passed.
        reports = context.get("output_validation_reports", [])
        has_errors = any(not r.passed for r in reports)
        if has_errors:
            error_msgs = []
            for r in reports:
                error_msgs.extend(r.errors)
            return StageResult.failed(
                self.name,
                ["Output validation reported errors — cannot package."] + error_msgs,
            )

        try:
            package_info = self._output_manager.package(context)
        except Exception as exc:  # noqa: BLE001
            return StageResult.failed(
                self.name,
                [f"Packaging failed: {exc}"],
            )

        context.set("final_project", package_info)
        return StageResult.ok(
            self.name,
            outputs={"package": package_info},
            metadata={"project_path": package_info.get("project_path")},
        )


__all__ = ["PackageStage"]
