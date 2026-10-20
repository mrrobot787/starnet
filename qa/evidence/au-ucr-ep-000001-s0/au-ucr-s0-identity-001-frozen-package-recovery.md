# AU-UCR-S0-IDENTITY-001 frozen package recovery note

- `experiment_id`: `AU-UCR-EP-000001`
- `sprint_id`: `S0`
- `work_item_id`: `AU-UCR-S0-IDENTITY-001`
- `owner_lane`: `unassigned_role_only` (`S0_WORKTREE_LANE_REGISTER.yaml`)
- `branch`: `cursor/ucr-s0-local-001-3141`
- `commit_tested`: `07d9ab53cecdec9a68efd7d25edadeb10db71538`
- `gate_set`: `EV-I01`
- `outcome`: `blocked`
- `reviewer`: `not_run`
- `review_outcome`: `blocked`
- `created_at_utc`: `2026-10-04T18:27:00Z`

## Result

`BLOCKED_FROZEN_PACKAGE_UNAVAILABLE`

The identity receipt references frozen commit
`07d9ab53cecdec9a68efd7d25edadeb10db71538` and local evidence root
`qa/evidence/au-ucr-ep-000001-local/`, but this PR does not contain that evidence tree and the
commit is not recoverable from the fetched origin refs.

## Recovery checks

| Check | Result |
| --- | --- |
| `git fetch origin cursor/split-ucr-s0-publication-evidence-20261004-135428 feat/harness-backend` | completed |
| `git fetch origin --prune "+refs/heads/*:refs/remotes/origin/*"` | completed |
| `git fetch origin 07d9ab53cecdec9a68efd7d25edadeb10db71538` | failed: `upload-pack: not our ref` |
| `git cat-file -t 07d9ab53cecdec9a68efd7d25edadeb10db71538` | missing object |
| `git ls-remote origin` search for `07d9ab53` | no advertised ref |
| `qa/evidence/au-ucr-ep-000001-local/` | absent from this PR |

## Supplied bundle coverage

| Bundle | Advertised tip | Required base |
| --- | --- | --- |
| `au-ucr-s0-recovery-001-canonical-thin.bundle.b64` | `887b1d9586b005606e1d8985e6c47c70a4a2900e` | `0b73cb2fb9c3046fee800c18337100a6fb0f4ac3` |
| `au-ucr-s0-canonical-thin.bundle.b64` | `cdc793ba738c688ef2493fcd196043bfb3fddd77` | `fbddbf992f8e7082196f07c3024781fcf1c276fc` |
| `au-ucr-gov-001-canonical-thin.bundle.b64` | `3f2dd71db76ddc89ff2dabad391665f4a381698c` | `cdc793ba738c688ef2493fcd196043bfb3fddd77` |

None of the supplied bundles advertises `07d9ab53cecdec9a68efd7d25edadeb10db71538`.

## Required custodian action

Before the identity evidence can be treated as final reviewable evidence, supply one of:

- a bundle or ref that advertises `07d9ab53cecdec9a68efd7d25edadeb10db71538` and reconstructs
  `qa/evidence/au-ucr-ep-000001-local/`; or
- the checked-in `qa/evidence/au-ucr-ep-000001-local/` evidence tree containing the 53 referenced
  artifacts.
