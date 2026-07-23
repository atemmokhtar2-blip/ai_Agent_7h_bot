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
- [ ] Write tests/test_blueprint_validator.py
- [ ] Run all tests (manager + planner + validator)

## Spec 006 — Project Structure Generation Engine
- [ ] Read & understand Spec 006 requirements
- [ ] Read existing builders (DirectoryBuilder, FileBuilder, etc.)
- [ ] Create structure_map.py (data model: ProjectStructureMap, FolderEntry, FileEntry)
- [ ] Create naming_engine.py (internal naming engine)
- [ ] Create folder_planner.py (folder planning)
- [ ] Create file_planner.py (file planning)
- [ ] Create structure_validator.py (validation before finishing)
- [ ] Create structure_generation_engine.py (main engine)
- [ ] Create __init__.py (package)
- [ ] Update generators/__init__.py (export)
- [ ] Update bootstrap.py (register)
- [ ] Write tests/test_structure_generator.py
- [ ] Run all tests
