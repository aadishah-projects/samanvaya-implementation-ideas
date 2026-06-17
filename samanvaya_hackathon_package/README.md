# Samanvaya Hackathon Package

This folder is a clean handoff package for the Samanvaya project.

Samanvaya is a reconciliation engine for Nepal's health insurance payment flow. It compares approved OpenIMIS claims against SOSYS/Mojaloop-style payment records, then flags missing payments, amount mismatches, pending payments, and duplicate payment risk.

## Folder Layout

```text
samanvaya_hackathon_package/
|-- current_implementation6/
|   |-- app/
|   |   |-- config.py
|   |   |-- setup_db.py
|   |   |-- seed_realistic_data.py
|   |   |-- mock_fhir.py
|   |   |-- mock_openimis_graphql.py
|   |   |-- extract_openimis.py
|   |   |-- extract_sosys.py
|   |   |-- reconcile_sql.py
|   |   |-- main.py
|   |   `-- requirements.txt
|   `-- implementation6_notes/
|       |-- implementation6.md
|       `-- implementation6-real.md
|-- past_implementations/
|   |-- basic_implementation/
|   |-- implementation2/
|   |-- implementation3/
|   |-- implementation4/
|   |-- implementation5/
|   `-- version/
`-- docs/
    |-- 01_FULL_PROJECT_DOCUMENTATION.md
    |-- 02_RUN_IMPLEMENTATION6_STEP_BY_STEP.md
    |-- 03_IMPLEMENTATION6_COMPONENT_ROLES.md
    `-- 04_REAL_WORLD_UPGRADE_ROADMAP.md
```

## What To Read First

1. Read `docs/01_FULL_PROJECT_DOCUMENTATION.md` to understand what has been built so far.
2. Read `docs/02_RUN_IMPLEMENTATION6_STEP_BY_STEP.md` to run the current implementation.
3. Read `docs/03_IMPLEMENTATION6_COMPONENT_ROLES.md` to understand each file and component.
4. Read `docs/04_REAL_WORLD_UPGRADE_ROADMAP.md` for hackathon upgrade ideas and production direction.

## Important Note

The packaged files are copies. The actual runnable project still lives in the main repository root:

```text
C:\Users\Acer\Downloads\samanvaya
```

Run commands from that root folder unless a guide explicitly says otherwise.
