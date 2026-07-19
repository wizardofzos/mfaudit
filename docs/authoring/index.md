# Authoring controls

Controls are YAML documents. Every control maps to one or more mfpandas DataFrames, runs a query or Python snippet, and produces a verdict.

---

## Before you start

1. Know which mfpandas DataFrame holds the data you need. The main DataFrames are:

    | DataFrame | Source | Key columns |
    |---|---|---|
    | `setropts.fieldInfo` | SETROPTS | `Setting`, `Value` |
    | `setropts.classInfo` | SETROPTS | `name`, `CLASSACT`, `RACLIST`, `GENERIC` |
    | `irrdbu00.users` | IRRDBU00 | `USBD_NAME`, `USBD_SPECIAL`, `USBD_OPER`, `USBD_NOPWD`, `USBD_REVOKE` |
    | `irrdbu00.groups` | IRRDBU00 | `GPBD_NAME`, `GPBD_SUPGRP_ID` |
    | `irrdbu00.generalSTDATA` | IRRDBU00 | `GRST_CLASS_NAME`, `GRST_NAME`, `GRST_USER_ID`, `GRST_TRUSTED` |
    | `irrdbu00.generals` | IRRDBU00 | `GRBD_CLASS_NAME`, `GRBD_NAME`, `GRBD_UACC` |
    | `irrdbu00.generalAccess` | IRRDBU00 | `GRAC_CLASS_NAME`, `GRAC_NAME`, `GRAC_AUTH_ID`, `GRAC_ACCESS` |
    | `irrdbu00.userOMVS` | IRRDBU00 | `USOMVS_NAME`, `USOMVS_UID` |
    | `irrdbu00.datasets` | IRRDBU00 | `DSBD_NAME`, `DSBD_UACC` |
    | `dcollect.datasets` | DCOLLECT | `DCDDSNAM`, `DCDVOLSR`, `DCDRACFD`, `DCDSMSM`, `DCDTEMP`, `DCDTYPE`, `DCDKLBL` |

2. Decide which engine fits:
    - **`pandas_query`** — single filter expression, empty result = PASS
    - **`python`** — anything more complex: multiple DataFrames, conditional logic, per-row decisions

3. Choose a stable `control_id`:
    - `CIS-x.y.z` — CIS Benchmark controls
    - `CUSTOM-SLUG` — shop-specific rules

---

## Quick example — pandas_query

```yaml
controls:
  - control_id: CUSTOM-NO-GLOBAL-UACC
    title: "No dataset profile may have UACC=ALTER"
    severity: high
    custom:
      benchmark: "Internal policy"
      category:  "Dataset protection"
    data_sources_needed: [irrdbu00]
    implementation:
      engine: pandas_query
      dataset: irrdbu00.datasets
      select_columns: [DSBD_NAME, DSBD_UACC]
      filter: "DSBD_UACC == 'ALTER'"
      assertion: "no rows returned"
    remediation: >
      Change UACC for the listed profiles:
      ALTDSD '<profile>' UACC(READ)
```

---

## Quick example — python engine

```yaml
  - control_id: CUSTOM-STCS-PROTECTED
    title: "All STARTED class profiles must specify PROTECTED userids"
    severity: high
    custom:
      benchmark: "Internal policy"
      category:  "Started tasks"
    data_sources_needed: [irrdbu00]
    implementation:
      engine: python
      dataset: irrdbu00.generalSTDATA
      select_columns: [GRST_CLASS_NAME, GRST_NAME, GRST_USER_ID, GRST_TRUSTED]
      logic: |
        started = df[df['GRST_CLASS_NAME'] == 'STARTED']
        # Look up each assigned userid in the users DataFrame
        bad = []
        for _, row in started.iterrows():
            uid = row['GRST_USER_ID']
            user_row = users_df[users_df['USBD_NAME'] == uid]
            if user_row.empty or user_row['USBD_NOPWD'].values[0] != 'YES':
                bad.append(row.to_dict())
        if bad:
            status = 'FAIL'
            detail = f"{len(bad)} STARTED profile(s) with non-PROTECTED userid"
            findings = bad
        else:
            status = 'PASS'
            detail = "All STARTED profiles assign PROTECTED userids"
    remediation: >
      For each listed userid, issue: ALTUSER <userid> NOPASSWORD
```

---

## Next steps

- [Full YAML schema](schema.md) — every field documented with types and defaults
- [Python engine](python-engine.md) — available variables, patterns, and pitfalls
