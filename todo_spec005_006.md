# Spec 005 (completion) + Spec 006 — Implementation Todo

## Spec 005 — Finish the Blueprint Validator Engine
- [x] validation_report.py
- [x] conflict_detector.py
- [x] quality_scorer.py
- [x] layers/__init__.py + all 6 layer modules
- [x] blueprint_validator_engine.py (main engine)
- [x] blueprint_validator/__init__.py (package init)
- [x] Update generators/__init__.py (export engine)
- [x] Update bootstrap.py (register engine)
- [x] Update defaults.py (quality config section)
- [x] Write tests/test_blueprint_validator.py
- [x] Run all tests (manager + planner + validator)

## Spec 006 — Project Structure Generation Engine
- [x] Read & understand Spec 006 requirements
- [x] Read existing builders (DirectoryBuilder, FileBuilder, etc.)
- [x] Create structure_map.py (data model: ProjectStructureMap, FolderEntry, FileEntry)
- [x] Create naming_engine.py (internal naming engine)
- [x] Create folder_planner.py (folder planning)
- [x] Create file_planner.py (file planning)
- [x] Create structure_validator.py (validation before finishing)
- [x] Create structure_generation_engine.py (main engine)
- [x] Create __init__.py (package)
- [x] Update generators/__init__.py (export)
- [x] Update bootstrap.py (register)
- [x] Update defaults.py (structure_engine config)
- [x] Write tests/test_structure_generator.py
- [x] Run all tests
