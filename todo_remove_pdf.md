# Remove PDF / Visual Page Reconstruction Engine

## Tasks

### Delete files
- [x] Delete the `visual_page_reconstruction/` engine package (9 .py files + __pycache__)
- [x] Delete `telegram_bot_engine/pipeline/stages/visual_reconstruction_stage.py`
- [x] Delete `tests/test_visual_page_reconstruction.py`

### Edit references
- [x] Remove `VisualPageReconstructionEngine` from `telegram_bot_engine/engines/generators/__init__.py` (import + __all__)
- [x] Remove `VisualPageReconstructionEngine` from `telegram_bot_engine/core/bootstrap.py` (import + registry + manager registration)
- [x] Remove `VisualReconstructionStage` from `telegram_bot_engine/pipeline/stages/__init__.py` (import + __all__)

### Fix stale test counts (engine count was 9 → now 12)
- [x] Fix `tests/test_manager.py` (BI count 9 → 12)
- [x] Fix `tests/test_project_planner.py` (BI-02, BI-03, BI-07 counts 9 → 12)

### Verify
- [x] All existing tests pass with no regressions
- [x] No remaining references to "pdf" or "visual_page_reconstruction" in source
