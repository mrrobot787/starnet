from pathlib import Path
import json, subprocess, sys

TRIAGE = Path(__file__).resolve().parents[1] / "scripts" / "agents_university_triage.py"
REQUEST = Path(__file__).resolve().parents[1] / "scripts" / "request_university_next_steps.py"


def run_triage(tmp: Path, args=None):
    args = args or []
    proc = subprocess.run([sys.executable, str(TRIAGE), *args], cwd=str(tmp), capture_output=True, text=True)
    return proc


def run_request(tmp: Path):
    proc = subprocess.run([sys.executable, str(REQUEST)], cwd=str(tmp), capture_output=True, text=True)
    return proc


def test_triage_no_request_writes_minimal(tmp_path: Path):
    proc = run_triage(tmp_path)
    assert proc.returncode == 0
    out = tmp_path / ".mm-out" / "agents" / "triage" / "university_next_steps_analysis.json"
    ev = tmp_path / ".mm-out" / "agents" / "evidence.jsonl"
    assert out.exists() and ev.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data.get("status") == "no_request"
    assert isinstance(data.get("recommendations"), list) and len(data["recommendations"]) == 0


def test_triage_with_request_produces_recommendations(tmp_path: Path):
    # Seed minimal signals to reduce recommendations variability
    (tmp_path / ".mm-out" / "nlp").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".mm-out" / "nlp" / "evidence.jsonl").write_text("{}\n")
    (tmp_path / "docs" / "badges").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "badges" / "promotion.json").write_text(json.dumps({"message": "FAILED"}))

    # Create the request
    pr = run_request(tmp_path)
    assert pr.returncode == 0

    # Run triage
    pt = run_triage(tmp_path, ["--originator", "pytest"])
    assert pt.returncode == 0

    out = tmp_path / ".mm-out" / "agents" / "triage" / "university_next_steps_analysis.json"
    data = json.loads(out.read_text(encoding="utf-8"))
    recs = data.get("recommendations")
    assert data.get("status") == "ok"
    assert isinstance(recs, list) and len(recs) >= 1
    # Top recommendation should be about promotion gaps when promotion != PASSED
    assert any("promotion" in (r.get("id") or "") for r in recs)
