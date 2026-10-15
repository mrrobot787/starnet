# AML University — Agent Registry & Verifier Architecture

## Overview
This document extends the AML University agent registry to support **verification-based inference scaling**. It defines a framework for **multi-attempt reasoning** and **verifier coordination**, allowing agents to produce multiple candidate actions and use internal or external verifiers to evaluate them.

---

## 1. Conceptual Model

Inference scaling with verifiers increases agent reliability by combining:
- **Exploration** — agents generate multiple candidate actions or outputs.
- **Verification** — a verifier (human, AI, or hybrid) selects the best candidate based on confidence or evaluation metrics.

This approach mirrors medical peer review: multiple diagnoses proposed, one verified.

---

## 2. Cognitive Loop Extension

Each agent operates under the core cognitive loop:

```
Memory ↔ Planning ↔ Action ↔ Reflection
```

This architecture is now extended with a verification stage:

```
Memory ↔ Planning ↔ Action ↔ Verification ↔ Reflection
```

The **verification stage** compares candidate outputs against pre-defined KPIs or thresholds.

---

## 3. Schema Extension (JSON)

### Added Fields

```json
"cognitive_loop": {
  "memory": { "short_term_window": 20, "long_term": false },
  "planning": { "strategy": ["subgoal_decomposition", "reflection"], "runbooks_required": true },
  "action": { "tool_use": "constrained-by-tools", "max_steps": 50 },
  "verification": {
    "enabled": true,
    "method": "Bayesian_consensus",
    "pass_k": 3,
    "verifier_agent": "dean-g1"
  },
  "reflection": { "self_critique": true, "report_period_days": 30 }
},
"evaluation": {
  "type": "agent",
  "environment_benchmarks": [
    { "name": "pass@k", "metric": "coverage", "target": 0.9 },
    { "name": "verification_accuracy", "metric": "precision", "target": 0.95 }
  ],
  "methods": ["simulated_hospital_runs", "peer_review", "human-AI_reflection"],
  "review_cycle_days": 30
}
```

---

## 4. Verifier Agent Definition

Example: Governance & Policy Assistant acting as a **Verifier**

```json
{
  "agent_id": "dean-g1",
  "title": "Governance & Policy Assistant (Verifier)",
  "role": "Independent Verifier",
  "environment": { "name": "Admin Office", "runtime": ["policy-engine"] },
  "system_prompt": "You evaluate outputs from peer agents for accuracy, safety, and compliance using Bayesian consensus across multiple attempts.",
  "reasoning_overlays": ["Bayesian", "Deterministic"],
  "autonomy": { "level": 2 },
  "kpis": ["verification_accuracy", "false_positive_rate"],
  "audit": { "logging": ["inputs", "decisions", "rationales"], "retention_days": 90 }
}
```

---

## 5. Pass@K Metric Tracking

Agents log their multi-attempt results in the evaluation subsystem:

```json
"results": {
  "attempts": 3,
  "successful_attempts": 2,
  "pass@3": 0.67,
  "verified_by": "dean-g1",
  "timestamp": "2025-10-07T14:00:00Z"
}
```

The **pass@k** score reflects reliability under multiple trials and can be aggregated into dashboards for ongoing evaluation.

---

## 6. Developer Integration Notes (Cursor IDE)

**Cursor Integration Goals:**
- Validate agent registry JSON schemas automatically on commit.
- Create dev tools for running simulated verification cycles.
- Provide test harnesses for pass@k measurement per agent type.

**Example workflow in Cursor:**
1. Developer commits a new agent JSON definition.
2. CI pipeline runs schema validation.
3. Verification harness triggers sample simulation (multi-attempt).
4. Results (pass@k, verification_accuracy) stored in MLflow / W&B.
5. Feedback integrated into RHL (Reinforcement-Human-Learning) loop.

---

## 7. Future Extensions
- Adaptive k: dynamically scale number of attempts based on historical confidence.
- Federated verification pools: shared verifier network across departments.
- Verifier benchmarking: evaluate verifiers themselves for consistency and fairness.

---

**Maintainer:** AML University – Agent Engineering Division  
**Version:** 1.2.0  
**Date:** 2025-10-07
