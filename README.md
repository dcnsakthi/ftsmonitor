# Microsoft Fabric Tenant Settings Monitoring.

## Overview

This repository contains a **Microsoft Fabric end-to-end monitoring solution** for tenant settings:

- **Notebook** (`nb_ftsm_tenant_settings.Notebook`) extracts tenant settings snapshots
- **Lakehouse** (`FTSMonitorLH.Lakehouse`) stores persisted snapshot data
- **Semantic Model** (`FTSMonitorSM.SemanticModel`) provides analytical modeling
- **Report** (`FTSMonitorRPT.Report`) visualizes the current snapshot and historical comparison

The objective is to track tenant setting changes over time for governance and audit scenarios.

---

## Repository Structure

```text
.
├── nb_ftsm_tenant_settings.Notebook/     # Fabric Notebook artifact
│   ├── notebook-content.py               # Notebook logic (Python)
│   ├── .schedules                        # Notebook schedule metadata
│   └── .platform                         # Fabric platform metadata
├── FTSMonitorLH.Lakehouse/               # Fabric Lakehouse artifact
│   ├── lakehouse.metadata.json
│   ├── shortcuts.metadata.json
│   ├── alm.settings.json
│   └── .platform
├── FTSMonitorSM.SemanticModel/           # Fabric Semantic Model artifact
│   ├── definition.pbism
│   ├── definition/
│   └── .platform
├── FTSMonitorRPT.Report/                 # Fabric Report artifact
│   ├── definition.pbir
│   ├── definition/
│   ├── StaticResources/
│   └── .platform
├── README.md
└── LICENSE
```

---

## Solution Architecture

1. **Extract (Notebook)**
   - The Fabric notebook runs scheduled/on-demand.
   - It captures tenant settings snapshot data at execution time.

2. **Persist (Lakehouse)**
   - Snapshot output is written to Lakehouse-managed storage/tables.

3. **Model (Semantic Model)**
   - The semantic model is built over Lakehouse data for analytics.

4. **Visualize (Report)**
   - The report consumes the semantic model to show:
     - current settings snapshot
     - comparisons across snapshots/versions

---

## Artifacts

### 1) Notebook: `nb_ftsm_tenant_settings.Notebook`

- Main code file: `notebook-content.py`
- Includes schedule configuration: `.schedules`
- Used to extract and prepare tenant settings snapshot data

### 2) Lakehouse: `FTSMonitorLH.Lakehouse`

- `lakehouse.metadata.json` defines core Lakehouse metadata
- `shortcuts.metadata.json` contains shortcut metadata (currently minimal)
- `alm.settings.json` provides deployment/environment binding settings for ALM flows

### 3) Semantic Model: `FTSMonitorSM.SemanticModel`

- `definition.pbism` + `definition/` store model definitions
- Exposes modeled data for report consumption

### 4) Report: `FTSMonitorRPT.Report`

- `definition.pbir` + `definition/` store report definitions
- `StaticResources/` includes report static assets/resources

---

## Deployment / Usage

### Prerequisites

- Microsoft Fabric workspace with Git integration enabled
- Access to this repository and the branch
- Appropriate Fabric permissions to run notebook and refresh model/report

### Steps

1. Connect Fabric workspace to this Git repository.
2. Sync artifacts from Git into Fabric workspace.
3. Open **`nb_ftsm_tenant_settings.Notebook`** and validate runtime/environment settings.
4. Run notebook once to generate/refresh snapshot data in **`FTSMonitorLH.Lakehouse`**.
5. Refresh **`FTSMonitorSM.SemanticModel`**.
6. Open **`FTSMonitorRPT.Report`** to validate visuals for current snapshot and comparisons.
7. Configure or verify notebook schedule from `.schedules` metadata (in Fabric UI).

---

## Operational Notes

- Keep notebook schedule aligned with your governance monitoring interval.
- Use semantic model refresh sequencing after notebook runs.
- Validate environment-specific settings in `alm.settings.json` before promoting across environments.
- Consider adding alerting (e.g., pipeline/Teams/email) for notebook or refresh failures.

---

## Current Documentation Status

This README reflects the artifact structure present in the branch and documents intended end-to-end usage.  
For deeper technical documentation, consider adding:

- notebook parameter definitions and expected outputs
- actual Lakehouse table schema details
- semantic model measures and relationships
- report page-level KPI definitions

---

## License

This project is licensed under the terms in [LICENSE](LICENSE).
