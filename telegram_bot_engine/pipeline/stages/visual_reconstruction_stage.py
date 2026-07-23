"""
Visual page reconstruction stage (Specification 009).
This stage runs the :class:`VisualPageReconstructionEngine` to
reconstruct PDF pages with pixel-accurate fidelity.  It takes the
``original_pdf`` artefact from the generation context, runs the engine,
and stores the results.
The stage does **not** create project files.  It only produces
page analysis artefacts and similarity reports.
"""
from __future__ import annotations
from typing import List
from ...core.context import GenerationContext
from ...core.result import StageResult
from ...registry import EngineRegistry
from ..base_stage import BaseStage


class VisualReconstructionStage(BaseStage):
    """Runs the Visual Page Reconstruction Engine."""
    stage_name = "visual_reconstruction"
    requires: List[str] = ["original_pdf"]
    provides: List[str] = [
        "page_analyses",
        "rebuilt_pdf_bytes",
        "visual_similarity_reports",
    ]

    def __init__(self, registry: EngineRegistry) -> None:
        super().__init__()
        self._registry = registry

    def execute(self, context: GenerationContext) -> StageResult:
        pdf_data = context.get("original_pdf")
        if pdf_data is None:
            return StageResult.failed(
                self.name,
                ["VisualReconstructionStage requires the 'original_pdf' "
                 "artefact."],
            )

        engine = self._registry.get_engine("visual_page_reconstruction")
        if engine is None:
            return StageResult.failed(
                self.name,
                ["VisualPageReconstructionEngine is not registered."],
            )

        try:
            result = engine.execute(context)
        except Exception as exc:
            return StageResult.failed(
                self.name,
                [f"VisualPageReconstructionEngine crashed: {exc}"],
            )

        if not result.success:
            return StageResult.failed(
                self.name,
                result.errors,
                outputs=result.outputs,
                warnings=result.warnings,
                metadata=result.metadata,
            )

        # Store outputs in context.
        context.set("page_analyses", result.outputs.get("page_analyses", []))
        context.set("rebuilt_pdf_bytes", result.outputs.get("rebuilt_pdf_bytes", b""))
        context.set("visual_similarity_reports",
                     result.outputs.get("visual_similarity_reports", []))

        return StageResult.ok(
            self.name,
            outputs={
                "page_analyses": result.outputs.get("page_analyses", []),
                "rebuilt_pdf_bytes": result.outputs.get("rebuilt_pdf_bytes", b""),
                "visual_similarity_reports":
                    result.outputs.get("visual_similarity_reports", []),
                "total_pages": result.outputs.get("total_pages", 0),
                "overall_passed": result.outputs.get("overall_passed", False),
            },
            warnings=result.warnings,
            metadata=result.metadata,
        )


__all__ = ["VisualReconstructionStage"]
