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
- **Fabric Administrator role** (or equivalent tenant admin API access) for the identity that runs the notebook. The notebook calls two Fabric Admin REST APIs that are restricted to tenant admins:
  - `GET v1/admin/tenantsettings`
  - `GET v1/admin/capacities/delegatedTenantSettingOverrides`
  - Without this role, these two calls fail with a permission error (see [Error Handling & Permissions](#error-handling--permissions) below) and their tables receive no new rows — the rest of the notebook still completes.
- Standard **Contributor** (or higher) role on the Fabric workspace to run the notebook and refresh the model/report.
- Capacity-level visibility (Capacity Contributor/Admin, or tenant admin) if you want `fabric.list_capacities()` to return capacities you don't directly own.

### Steps

1. Connect Fabric workspace to this Git repository.
2. Sync artifacts from Git into Fabric workspace.
3. Open **`nb_ftsm_tenant_settings.Notebook`** and validate runtime/environment settings.
4. Run notebook once to generate/refresh snapshot data in **`FTSMonitorLH.Lakehouse`**.
5. Refresh **`FTSMonitorSM.SemanticModel`**.
6. Open **`FTSMonitorRPT.Report`** to validate visuals for current snapshot and comparisons.
7. Configure or verify notebook schedule from `.schedules` metadata (in Fabric UI).

---

## Error Handling & Permissions

Each Admin API extraction in `notebook-content.py` (`get_tenantSettings`, `get_capacities`, `get_delegatedTenantSettings`) wraps its REST call in a `try/except` block:

- On a permission error (`FabricHTTPException`, typically HTTP 401/403), the cell prints a `WARNING:` message naming the required role and **does not raise** — the notebook keeps running and simply appends zero rows to that table for the current snapshot.
- On any other unexpected error, a generic `WARNING:` message is printed and the same zero-row behavior applies.

**Practical implication:** the notebook (and its schedule run) reports **Succeeded** even when the executing identity lacks tenant admin rights — it does not fail loudly. If `ftsm_tenant_settings` or `ftsm_capacity_settings` stay empty after a run, check the notebook's cell output/run logs for `WARNING:` lines before assuming a code or connectivity issue. To get full data, run the notebook (or its schedule) as a user or service principal that holds the Fabric Administrator role.

---

## Parameterized Deployment (`parameter.yml`)

This repository includes a [`parameter.yml`](parameter.yml) file at the repository root, consumed automatically by [fabric-cicd](https://microsoft.github.io/fabric-cicd/latest/) when deploying via Git integration or the `msfabric_solution_catalog` installer.

Why it's needed: `FTSMonitorSM.SemanticModel/definition/expressions.tmdl` embeds a Direct Lake connection string (`AzureStorage.DataLake(".../{workspaceId}/{lakehouseId}")`) pointing at the **original authoring workspace and Lakehouse**. Without parameterization, every deployment to a new workspace would silently keep querying the original dev Lakehouse instead of the newly deployed one. `parameter.yml` uses `find_replace` with dynamic `$workspace`/`$items` variables to rewrite both GUIDs to the target deployment's workspace and `FTSMonitorLH` Lakehouse IDs at publish time.

If you connect a Fabric workspace directly to this repo via Git integration (bypassing fabric-cicd), `parameter.yml` is **not** applied automatically — you must manually rebind the semantic model's Direct Lake connection (Semantic model settings → Manage connections, or via Power BI Desktop) to the new workspace's Lakehouse after the first sync.

---

## Operational Notes

- Keep notebook schedule aligned with your governance monitoring interval.
- Use semantic model refresh sequencing after notebook runs.
- Validate environment-specific settings in `alm.settings.json` before promoting across environments.
- Consider adding alerting (e.g., pipeline/Teams/email) for notebook or refresh failures.
- Review notebook cell output for `WARNING:` messages after each run — see [Error Handling & Permissions](#error-handling--permissions).

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
