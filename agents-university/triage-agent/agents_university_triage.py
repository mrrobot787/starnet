"""
Summary: Read the University "next steps" request and emit a prioritized triage analysis
Contracts:
- Inputs:
  - .mm-out/agents/requests/university_next_steps_request.json (optional)
- Outputs:
  - .mm-out/agents/triage/university_next_steps_analysis.json (analysis with recommendations)
  - .mm-out/agents/evidence.jsonl (append-only; kind: university_next_steps_analyzed)
Side-effects: Append-only evidence; creates output directories as needed; no network calls.
Errors: Never fails hard; on missing inputs, writes a minimal analysis with status=no_request.
Example:
  python scripts/agents_university_triage.py 
  python scripts/agents_university_triage.py --originator CI
Version: 0.1.0
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


BASE = Path.cwd()
AGENTS_OUT = BASE / ".mm-out" / "agents"
REQ_PATH = AGENTS_OUT / "requests" / "university_next_steps_request.json"
TRIAGE_OUT = AGENTS_OUT / "triage" / "university_next_steps_analysis.json"
EVID = AGENTS_OUT / "evidence.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_evidence(kind: str, payload: Dict[str, Any]) -> None:
    EVID.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": now_iso(), "kind": kind, **payload}
    with EVID.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_request(path: Path) -> Dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@dataclass
class Recommendation:
    id: str
    title: str
    priority: int
    rationale: str
    task_label: str | None = None  # Optional VS Code task label

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority,
            "rationale": self.rationale,
            **({"task_label": self.task_label} if self.task_label else {}),
        }


def recs_from_signals(signals: Dict[str, Any]) -> List[Recommendation]:
    recs: List[Recommendation] = []

    badges = (signals.get("badges", {}) or {})
    promo = badges.get("promotion")
    if promo != "PASSED":
        recs.append(Recommendation(
            id="promotion-fill-gaps",
            title="Satisfy promotion minima and rerun gate",
            priority=1,
            rationale="Promotion not yet PASSED; fulfill teach-pack/report evidence and re-check.",
            task_label="badges: update+publish",
        ))

    if not (signals.get("bls", {}) or {}).get("present"):
        recs.append(Recommendation(
            id="bls-ci-safe",
            title="Run BLS ingest (OOH-only) and rebuild thinking tools",
            priority=2,
            rationale="BLS evidence missing; OOH-only ingest is CI-safe and fast.",
            task_label="bls: ingest+verify+manifest (ci-safe)",
        ))
        recs.append(Recommendation(
            id="bls-thinking-tools",
            title="Build BLS thinking tools",
            priority=3,
            rationale="Thinking tools aid analysis and are derived from BLS outputs.",
            task_label="bls: build thinking tools",
        ))

    if not (signals.get("incubator", {}) or {}).get("present"):
        recs.append(Recommendation(
            id="incubator-spawn",
            title="Specialize PROMOTED agents and spawn an incubator cohort",
            priority=4,
            rationale="Incubator enables targeted specialization; not yet present.",
            task_label="incubator: all → specialize+spawn → badges",
        ))

    if not (signals.get("accelerator", {}) or {}).get("present"):
        recs.append(Recommendation(
            id="accelerator-spawn",
            title="Spawn the Accelerator TF cohort and update badges",
            priority=5,
            rationale="Accelerator scales throughput; not yet present.",
            task_label="accelerator: all → spawn → badges",
        ))

    eff = signals.get("efficacy", {}) or {}
    if not eff.get("score"):
        recs.append(Recommendation(
            id="efficacy-check",
            title="Compute efficacy score and publish dashboard",
            priority=6,
            rationale="Efficacy not computed; add score/gradient and dashboard.",
            task_label="efficacy: all → check → badge → dashboard",
        ))

    if not (signals.get("nlp", {}) or {}).get("present"):
        recs.append(Recommendation(
            id="nlp-build",
            title="Build local NLP index and run sample query",
            priority=7,
            rationale="NLP index missing; build TF-IDF and verify with a sample query.",
            task_label="nlp: all → build → sample query",
        ))

    if not (signals.get("shared", {}) or {}).get("tail"):
        recs.append(Recommendation(
            id="share-insight",
            title="Share Ivy 4-D Linguist playbook insight University-wide",
            priority=8,
            rationale="Insight not yet shared; publish to promote knowledge reuse.",
            task_label="university: share insight (Linguist 4-D)",
        ))

    if not recs:
        recs.append(Recommendation(
            id="continuous-improvement",
            title="Review signals and propose next most impactful improvement",
            priority=9,
            rationale="All core signals present; proceed with continuous improvement.",
            task_label="agents: Librarian coverage (report)",
        ))

    # Sort by priority ascending
    recs.sort(key=lambda r: r.priority)
    return recs


def build_analysis(req: Dict[str, Any] | None, originator: str | None) -> Dict[str, Any]:
    if not req:
        return {
            "ts": now_iso(),
            "kind": "university_next_steps_analysis",
            "status": "no_request",
            "originator": originator,
            "recommendations": [],
            "notes": "No request file found; create the request first.",
        }

    signals = req.get("signals", {}) or {}
    recs = [r.to_dict() for r in recs_from_signals(signals)]
    return {
        "ts": now_iso(),
        "kind": "university_next_steps_analysis",
        "status": "ok",
        "originator": originator,
        "recommendations": recs,
        "source_request": {
            "path": str(REQ_PATH),
            "questions": req.get("questions", []),
        },
    }


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", default=str(REQ_PATH), help="Path to next-steps request JSON")
    ap.add_argument("--out", default=str(TRIAGE_OUT), help="Path to write analysis JSON")
    ap.add_argument("--originator", default=None, help="Originator tag for evidence")
    args = ap.parse_args(argv)

    req_path = Path(args.request)
    out_path = Path(args.out)
    originator = args.originator

    req_obj = load_request(req_path)
    analysis = build_analysis(req_obj, originator)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    append_evidence("university_next_steps_analyzed", {
        "request_present": bool(req_obj),
        "analysis_path": str(out_path),
        "originator": originator,
        "status": analysis.get("status"),
        "recommendations": len(analysis.get("recommendations", [])),
    })

    print(f"[OK] University next steps analysis written -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
