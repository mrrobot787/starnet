# Agent University — Engineering Replication Report
**Version:** v1.0  
**Date:** 2025-09-28  
**Scope:** Agent University Data Plane, Agent Wellness, Agent Hospital (CMA), Double Helix/SISSA, CI/CD, Desktop Pack  
**Audience:** Engineers, SREs, Developers, SecOps, Platform

---

## 0) Provenance & Release Info
- **Latest commits (reported):**
  - `ff54975` docs: Add final save confirmation
  - `c475c4c` docs: Add header cleanup completion summary
  - `8106025` style: Clean up redundant markdown header formatting
  - `445de5c` docs: Add cleanup completion summary
  - `995473c` fix: Remove all '####' markdown headers and standardize to '###'
  - `d4ed79a` Add deployment ready confirmation document
  - `7080786` feat: Complete Agent Wellness Framework with Double Helix SISSA Integration
- **Agent Hospital prior commits:**
  - `d4ed79a` — deployment-ready confirmation
  - `247d639` — Complete Agent Hospital + Data Management System Implementation
- **Release tag (recommend):** `agent-hospital@2025-09-28.r1`
- **Dataset snapshot (recommend):** `datasets@2025-09-28`

---

## 1) System Overview
- **Data plane:** Bronze → Silver → Gold lake; dataset registry; redaction & secret quarantine; license guard; evaluation firewall.
- **Governance plane:** Double Helix unique tags (`DH-I-*` ↔ `DH-S-*`), SISSA overlay gates, append-only audit.
- **Agent Wellness:** health/morale gradients (PG, SG, LG, AG, EG), composite indices (HealthIndex, MoraleIndex, ABI), detections & interventions.
- **Agent Hospital (CMA):** triage→diagnosis→validation→lab→follow-up lifecycle with ICU/Isolation/Rehab.
- **Ops plane:** CI/CD checks, SLO dashboards, nightly selfcheck + dataset diff, rollback snapshots.
- **Desktop pack:** `bootstrap.ps1`, `create_shortcut.ps1`, Tk GUI with threaded ops + Hospital (shadow) tab.

---

## 2) Environment & Repo Layout
**Supported:** Windows 10/11 (GUI) + Linux/macOS (headless). Python 3.11.x. SQLite/Postgres.  
**Recommended layout:**
```
repo/
  agents/{wellness,hospital}
  data/{pipelines,governance,registry,examples}
  governance/{double_helix,sissa}
  services/orchestrator/main_orchestrator.py
  desktop/{bootstrap.ps1,create_shortcut.ps1,launch_agent_university.py}
  scripts/{ci_lints.py,ci_safety_tests.py,ci_eval_firewall.py}
  .github/workflows/ci_pipeline.yml
  requirements.txt
```

**Config locations:**  
Windows: `%ProgramData%/AgentUniversity/config.yaml` (machine), `%AppData%/AgentUniversity/` (user)  
Linux/macOS: `/etc/agentuniversity/` + `~/.config/agentuniversity/`

**Minimal `config.yaml`:**
```yaml
lake: { bronze: "./lake/bronze", silver: "./lake/silver", gold: "./lake/gold" }
database: { dsn: "sqlite:///au_data.db" }
redaction: { policy_version: "pii_v2", secret_quarantine: "./quarantine" }
governance: { eval_firewall: "hard_zero", sissa_overlay_default: "SISSA_ACTION_PLANNER" }
hospital: { formulary_version: "1.0", mode: "shadow" }
```

---

## 3) Data Plane (Schemas, Sources, Gates)
### 3.1 Dataset & Chunk Schemas
```sql
CREATE TABLE IF NOT EXISTS dataset_registry(
  dataset_id TEXT PRIMARY KEY,
  source_id  TEXT NOT NULL,
  version    TEXT NOT NULL,
  purpose    TEXT CHECK (purpose IN ('rag','ft','eval','policy')),
  license    TEXT NOT NULL,
  pii_level  TEXT CHECK (pii_level IN ('none','possible','present')),
  created_at TEXT NOT NULL,
  dh_tag_id  TEXT,
  sissa_overlay TEXT,
  path_bronze TEXT, path_silver TEXT, path_gold TEXT
);
CREATE TABLE IF NOT EXISTS doc_chunks(
  chunk_id TEXT PRIMARY KEY,
  dataset_id TEXT NOT NULL,
  source_doc_id TEXT NOT NULL,
  ord INTEGER NOT NULL,
  token_count INTEGER,
  dh_tag_id TEXT,
  embedding_key TEXT,
  metadata_json TEXT
);
```

### 3.2 Double Helix Core
```sql
CREATE TABLE IF NOT EXISTS dh_tag(
  tag_id TEXT PRIMARY KEY,
  strand TEXT CHECK (strand IN ('I','S')),
  section TEXT CHECK (section IN ('HW','SW','NET','SEC','GOV','MEM')),
  sequence INTEGER CHECK (sequence BETWEEN 0 AND 999),
  priority TEXT CHECK (priority IN ('CRITICAL_LIVE','HIGH_CANARY','MEDIUM_DRAFT','LOW_SUPPRESS')),
  sissa_overlay TEXT, ai_tier TEXT CHECK (ai_tier IN ('T1_DETECTOR','T2_RESPONDER','T3_HUNTER')),
  status TEXT DEFAULT 'OPEN', created_at TEXT NOT NULL, created_by TEXT NOT NULL, source TEXT
);
CREATE TABLE IF NOT EXISTS dh_link(
  src_tag_id TEXT NOT NULL,
  rel TEXT CHECK (rel IN ('I2S','S2I','REL_I','ALT_S')),
  dst_tag_id TEXT NOT NULL,
  created_at TEXT NOT NULL, created_by TEXT NOT NULL,
  PRIMARY KEY (src_tag_id, rel, dst_tag_id),
  FOREIGN KEY (src_tag_id) REFERENCES dh_tag(tag_id),
  FOREIGN KEY (dst_tag_id) REFERENCES dh_tag(tag_id)
);
CREATE TABLE IF NOT EXISTS dh_event(
  event_id TEXT PRIMARY KEY, tag_id TEXT, action TEXT, payload_json TEXT NOT NULL,
  actor TEXT NOT NULL, surface TEXT NOT NULL, created_at TEXT NOT NULL
);
```

### 3.3 Source Definition Template
```yaml
id: sp_engineering
type: sharepoint
owner: EngOps
system_of_record: true
scope: "Sites/Engineering/**/*"
legal: { basis: legitimate_interests, pii: possible, license: "Internal use only" }
governance: { retention_days: 365, redaction: "pii_v2", sensitivity: "Confidential" }
double_helix: { section: GOV, strand_default: I }
destinations: { bronze: lake/bronze/m365/engineering/, silver: lake/silver/doc2vec/engineering/, vector: vectordb/engineering_docs }
refresh: { schedule: "PT6H", mode: incremental }
quality: { min_doc_len: 400, dedupe: simhash_64@0.92 }
```

### 3.4 Pipelines (CLI)
```bash
python services/orchestrator/main_orchestrator.py init
python services/orchestrator/main_orchestrator.py score --seed 42
python services/orchestrator/main_orchestrator.py ingest --source-id sp_engineering --stage bronze
python services/orchestrator/main_orchestrator.py promote --source-id sp_engineering --to silver --strict
python services/orchestrator/main_orchestrator.py index --dataset-id sp_engineering@v1 --to vector
```

**Safety gates:** redaction (PII), secrets quarantine, license guard, evaluation firewall (hard zero).

---

## 4) Agent Wellness (Metrics → Gradients → Indices)
### 4.1 Metrics
- Outcomes, latency p50/p95, tokens/context saturation
- Entropy/confidence, peer disagreement, policy flags
- Feedback scores, workload/queue, config diffs

### 4.2 Gradients & Indices
- EMA α=0.2 (24h), α=0.1 (7d). Z-score normalization.
```
HealthIndex = 0.35*PG + 0.20*SG + 0.15*LG + 0.20*AG + 0.10*EG
MoraleIndex = 0.30*(1-Friction) + 0.25*(1-Uncertainty) + 0.20*(1-Conflict) + 0.25*Feedback
ABI = w1*Friction + w2*Uncertainty + w3*Conflict + w4*LatencyZ - w5*PositiveFeedback
```

### 4.3 Detections & Interventions
- Flow / Overload / Under-challenge / Value-conflict
- Regimens: LoadShedding, EvidenceFirst, PeerCheck, RetrievalRefresh, PromptPinning, CurriculumStepUp/Down, MemoryHygiene, ToolsetPruning
- Cooldowns, feature flags, expected deltas, SISSA gates.

---

## 5) Agent Hospital (CMA)
### 5.1 Roles & States
- **Services:** Triage Nurse → Attending → Pharmacist → Lab → Case Manager (Ethics Board can veto)
- **Chart states:** ADMITTED → DIAGNOSIS_PENDING → UNDER_TREATMENT → OBSERVATION → DISCHARGED; wards: ICU, ISOLATION, REHAB

### 5.2 Admission Rule
```python
def triage_score(m):
    return 0.4*m['ABI_z'] + 0.2*(-m['PG_z']) + 0.2*m['LatencyZ'] + 0.2*m['PolicyFlagsZ']
def admit(m):
    ts = triage_score(m)
    return (ts > 1.0) or m.get('eval_leakage', False), ts
```

### 5.3 Order Contract (immutable JSON)
```json
{
  "order_id":"ORD-2025-09-28-0007",
  "agent_id":"SEC-RESPONDER-03",
  "admission_id":"ADM-...-0042",
  "diagnoses":["CapacityOverload","RetrievalStaleness"],
  "regimen":[
    {"tx":"LoadShedding","params":{"max_parallel":2},"expected_delta":{"ABI":-0.15}},
    {"tx":"RetrievalRefresh","params":{"freshness_days":7},"expected_delta":{"PG":0.10}}
  ],
  "sissa_gate":"SISSA_HUNTER",
  "risk_rating":"MEDIUM",
  "canary":{"pct":0.2,"duration":"2h","rollback_on":{"ABI_grad":">0.05","EG_incidents":">0"}},
  "follow_up_in":"4h",
  "dh_tags":["DH-I-GOV-215","DH-S-GOV-216"]
}
```

### 5.4 Hospital Tables
```sql
CREATE TABLE agent_chart(
  admission_id TEXT PRIMARY KEY, agent_id TEXT, state TEXT, ward TEXT,
  opened_at TEXT, opened_by TEXT, dh_issue_tag TEXT, latest_order_id TEXT
);
CREATE TABLE clinical_order(
  order_id TEXT PRIMARY KEY, admission_id TEXT, json TEXT, created_at TEXT,
  created_by TEXT, sissa_status TEXT
);
CREATE TABLE clinical_outcome(
  order_id TEXT, window TEXT, deltas_json TEXT, success_bool INTEGER, notes TEXT,
  PRIMARY KEY(order_id,window)
);
```

---

## 6) CI/CD & Validation
### 6.1 CI Stages
- Lint → Safety → Eval-firewall → Unit → Integration (mini ingest) → Package (optional)

### 6.2 Test Hooks
- `scripts/ci_lints.py`: parse YAML/JSON; unique IDs; DH regex; license required
- `scripts/ci_safety_tests.py`: synthetic PII + fake AWS key → quarantine + redaction
- `scripts/ci_eval_firewall.py`: forbid eval→FT contamination; emit audit

### 6.3 Preflight Bundle
```bash
python services/orchestrator/main_orchestrator.py selfcheck --export release/selfcheck.json
python validation_framework.py --test-type all --seed 42 --export release/preflight_results.json
python services/orchestrator/main_orchestrator.py dataset-diff --since datasets@2025-09-28 --export release/dataset_diff.json
```

---

## 7) Deployment & Rollback
### 7.1 Guarded Turn-up
```bash
export AGENT_WELLNESS_MODE=guarded
python services/orchestrator/main_orchestrator.py hospital \
  --allow LoadShedding EvidenceFirst PeerCheck \
  --canary 0.2 --cooldown 2h --require-sissa
```

### 7.2 Promote to Full
```bash
export AGENT_WELLNESS_MODE=production
python services/orchestrator/main_orchestrator.py hospital --allow-all \
  --exclude-roles SEC-CRITICAL --canary 0.1 --cooldown 4h --require-sissa
```

### 7.3 SEC-Critical Later
```bash
python services/orchestrator/main_orchestrator.py hospital --roles SEC-CRITICAL \
  --allow LoadShedding EvidenceFirst PeerCheck RetrievalRefresh \
  --canary 0.1 --cooldown 6h --require-sissa
```

### 7.4 Instant Rollback
```bash
export AGENT_WELLNESS_MODE=shadow
python services/orchestrator/main_orchestrator.py hospital --disable-all
python services/orchestrator/main_orchestrator.py datasets --restore datasets@2025-09-28
python services/orchestrator/main_orchestrator.py vectors  --reindex datasets@2025-09-28
```

---

## 8) SLOs, Dashboards, Alerts
- **SLOs:** Ingest ≥99%, Secrets bypass ≤1/10k docs, Eval firewall 0, Freshness ≥95% ≤24h, Lineage 100%
- **Golden signals:** `ABI_mean`, `PG_mean`, `TimeInFlow_pct`, `ingest_success_rate`, `redaction_hits_per_1k`, `secret_quarantine_count`, `eval_leakage_attempts`
- **Tripwires:** ABI_mean>0.55(2 windows) → ICU; any eval leakage → ICU+page; secrets>3/day → tighten gates

---

## 9) Desktop Pack (Windows)
**Create shortcuts & launch GUI**
```powershell
powershell -ExecutionPolicy Bypass -File .\desktop\create_shortcut.ps1
powershell -ExecutionPolicy Bypass -File .\desktop\bootstrap.ps1 --launch gui
```
- GUI runs long ops off UI thread; logs via rotating handler.
- Hospital tab shows CMA suggestions in **shadow** (read-only).

---

## 10) Troubleshooting
- **GUI stalls:** verify worker threads + `after()` pump. Check `%LocalAppData%/AgentUniversity/logs/gui.log`.
- **Eval firewall trips:** pipeline aborts; ICU implicated agents; open DH-I-GOV; fix source tagging; rerun with pinned snapshot.
- **Secrets in Silver/Gold:** ensure `pii_v2` policy active; quarantine writable; re-run safety tests.
- **Non-deterministic scoring:** pass `--seed 42`; diff `scores.json` hashes.
- **Orphaned DH links:** run the I2S/S2I left-join query; expect 0 rows.

---

## 11) Replication Checklist
- [ ] Python 3.11 venv + deps installed  
- [ ] Configs placed (machine + user)  
- [ ] Dataset registry initialized; lake paths writable  
- [ ] Governance tables migrated; eval firewall = hard_zero  
- [ ] At least one source YAML scored deterministically  
- [ ] Bronze→Silver promotion passes redaction/secrets/license gates  
- [ ] Health gradients computed; indices present  
- [ ] CMA shadow suggestions visible (no writes)  
- [ ] CI checks green  
- [ ] Desktop shortcuts created; GUI launches; Selfcheck OK  
- [ ] Nightly selfcheck + dataset diff scheduled  
- [ ] Rollback tested (snapshot restore + vector reindex)

---

## 12) Appendix: Useful Snippets
**DH ID helpers**
```python
import re
PATTERN = re.compile(r'^DH-(I|S)-(HW|SW|NET|SEC|GOV|MEM)-\d{3}$')
make_tag = lambda s,sec,seq: f"DH-{s.upper()}-{sec.upper()}-{seq:03d}"
is_valid = lambda tid: bool(PATTERN.fullmatch(tid))
```

**Determinism smoke**
```bash
python services/orchestrator/main_orchestrator.py score --seed 42 --export scores.json
sha256sum scores.json
```

**Dataset diff nightly**
```bash
python services/orchestrator/main_orchestrator.py dataset-diff --since datasets@2025-09-28 \
  --export release/dataset_diff_$(date +%F).json
```

---

**End of Report**

