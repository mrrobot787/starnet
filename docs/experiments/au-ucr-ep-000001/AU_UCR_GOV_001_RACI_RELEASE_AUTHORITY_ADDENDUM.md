# AU-UCR-GOV-001: RACI and release-authority addendum

## Authority and scope

- Work item: `AU-UCR-GOV-001`
- Experiment: `AU-UCR-EP-000001`
- Canonical Sprint 0 SHA: `cdc793ba738c688ef2493fcd196043bfb3fddd77`
- Canonical Sprint 0 state: `PUBLISHED_AWAITING_REVIEW`

This separately versioned addendum governs role assignment, decisions, and
release authority after publication of the canonical Sprint 0 package. It does
not amend that package or its evidence. The canonical package remains
`PUBLISHED_AWAITING_REVIEW`; publication is not acceptance and is not
authorization to execute UCR-001 or Sprint 1.

This addendum supersedes **only** these two earlier release-authority rows,
wherever they are reproduced:

| Superseded release row | Accountable and responsible authority |
| --- | --- |
| Release UCR-001 | Coordinator/Architect (`A/R`) |
| Release UCR-002/003/004 | Coordinator/Architect (`A/R`) |

No other row, artifact, evidence receipt, dependency, acceptance criterion, or
Sprint 0 statement is superseded. In particular, the Decision Chair owns only
the governance outcomes `ACCEPTED`, `REVISE`, and `REJECTED`; the Decision
Chair does not publish artifacts, issue execution releases, implement work, or
certify evidence.

## Mandatory role assignments and separation

Before a person acts in any governed role, the assignment register must contain
all of these fields:

1. experiment ID and work-item or release scope;
2. role name;
3. assignee's name and stable identity;
4. organization and implementation lane, if any;
5. assignment authority and assignment timestamp in UTC;
6. effective-from and, when ended, effective-through timestamps;
7. explicit duties and limits;
8. independence and conflict-of-interest declaration; and
9. acknowledgement by the assignee.

Blank, generic, shared, or role-only identities such as `unassigned_role_only`
do not authorize action. A receipt is invalid when its signer did not have an
effective assignment for that action.

Self-certification is prohibited. No person may approve, independently review,
QA-certify, or make the governance decision for their own implementation,
evidence preparation, publication action, or execution-release action. The
Independent Reviewer and Decision Chair must be different people from each
other and from the Coordinator/Architect, Publication Custodian, relevant
implementation role, Security/Governance Agent, and QA/Evidence Agent. The
QA/Evidence Agent must be independent of the implementation being validated.
Delegation does not combine incompatible roles or transfer accountability.

## Role authority boundaries

- **Publication Custodian** performs the mechanical publication of immutable,
  commit-addressed artifacts and emits the publication receipt. The custodian
  does not accept governance, approve evidence, or release execution.
- **Coordinator/Architect** owns dependency integrity and is both accountable
  and responsible for the two execution-release rows above. The coordinator
  verifies prerequisites and emits execution-release or execution-block
  receipts, but cannot create an `ACCEPTED`, `REVISE`, or `REJECTED` outcome.
- **QA/Evidence Agent** validates tests, provenance, completeness, and receipt
  integrity independently of implementation. QA reports findings and may block
  a release for unmet evidence requirements, but cannot accept governance or
  issue an execution release.
- **Independent Reviewer** evaluates the published package and QA record,
  records findings, conflicts, and an acknowledgement, and recommends a
  disposition. The reviewer cannot publish, implement, decide governance, or
  issue an execution release.
- **Decision Chair** alone records the governance outcome `ACCEPTED`, `REVISE`,
  or `REJECTED`, based on the independent record. The chair cannot publish,
  implement, QA-certify, independently review, or issue an execution release.
- **Contract Agent, Runtime Agent, and Campus/UI Agent** are implementation
  roles responsible only for their assigned lane changes and implementation
  evidence. They cannot certify their own work, decide governance, or release
  execution.
- **Security/Governance Agent** implements and assesses capability, permission,
  consent, policy, and threat-control requirements within its assigned scope.
  It may raise a security/governance block and provide specialist findings, but
  cannot self-certify those changes, substitute for the Independent Reviewer
  or Decision Chair, or publish or issue execution releases.

## RACI

`A` means accountable, `R` responsible, `C` consulted, and `I` informed.

| Governed activity | Publication Custodian | Coordinator/ Architect | QA/ Evidence Agent | Independent Reviewer | Decision Chair | Relevant implementation role | Security/ Governance Agent |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Prepare lane implementation and implementation evidence | I | A | C | I | I | R | R/C when security or governance scope applies |
| Validate tests, evidence, and provenance | I | C | A/R | C | I | C | C |
| Publish a commit-addressed review package | A/R | C | C | I | I | I | I |
| Independently review and acknowledge UCR-001 | I | C | C | A/R | I | I | C |
| Decide `ACCEPTED`, `REVISE`, or `REJECTED` | I | C | C | C | A/R | I | C |
| Release UCR-001 execution | I | A/R | C | I | I | I | C |
| Release UCR-002/003/004 execution | I | A/R | C | I | I | I | C |
| Raise a material-contradiction block | C | R | R | R | A | C | R |

An `A/R` entry identifies one role's accountability and operational
responsibility; it does not waive the separation-of-duties rules.

## Separate state machines and required receipts

Publication release, governance decision, and execution release are distinct
state machines. A transition in one does not imply a transition in another.
Every transition is append-only and must have its own receipt.

### Publication release

`DRAFT -> PUBLISHED_AWAITING_REVIEW`

Only the Publication Custodian may make this transition. The publication
receipt must identify the experiment and work item, artifact URI or manifest,
exact commit SHA, content digest, previous and next state, custodian identity,
role-assignment reference, and UTC timestamp. Republishing corrected content
requires a new commit, digest, and receipt; it does not overwrite prior
evidence or grant governance or execution authority.

For canonical Sprint 0, this state remains `PUBLISHED_AWAITING_REVIEW`.

### Governance decision

`PUBLISHED_AWAITING_REVIEW -> ACCEPTED | REVISE | REJECTED`

Only the Decision Chair may make this transition. The decision receipt must
identify the exact reviewed commit and publication receipt, QA receipt,
Independent Reviewer acknowledgement, resolved and unresolved findings,
outcome, rationale, chair identity, role-assignment reference, and UTC
timestamp. `REVISE` requires a new revision and review cycle. `REJECTED`
terminates the candidate unless a newly published candidate begins a new
review. An `ACCEPTED` outcome is necessary but not sufficient for execution.

### Execution release

`BLOCKED -> EXECUTION_RELEASED` or
`EXECUTION_RELEASED -> BLOCKED`

Only the Coordinator/Architect may issue either transition. The execution
receipt must identify the release row, exact implementation and governance
commit SHAs, governing `ACCEPTED` decision receipt, all prerequisite receipts,
dependency and feature-flag state, coordinator identity, role-assignment
reference, previous and next state, UTC timestamp, and rollback target.

UCR-001 execution release additionally requires a commit-specific
acknowledgement receipt from the assigned Independent Reviewer. That receipt
must state that the reviewer examined the publication and QA findings, list
open findings and conflicts, and confirm whether any material contradiction
remains. An acknowledgement is not a chair decision and cannot itself release
execution.

UCR-002/003/004 may be execution-released only after the UCR-001 acceptance and
dependency requirements in the canonical Sprint 0 package are satisfied and
their own prerequisites are recorded.

## Current gate and rollback

At adoption of this addendum:

- Sprint 0 remains `PUBLISHED_AWAITING_REVIEW`.
- UCR-001 and Sprint 1 execution remain `BLOCKED`.
- Neither may move to `EXECUTION_RELEASED` until the Decision Chair has issued
  a commit-specific `ACCEPTED` receipt **and** the Coordinator/Architect has
  subsequently issued the corresponding execution-release receipt.
- For UCR-001, the Independent Reviewer acknowledgement described above is an
  additional mandatory prerequisite to the coordinator's receipt.

If review, QA, security analysis, implementation, or later evidence exposes a
material contradiction with the accepted package, safety boundary, evidence,
or release premise, every affected execution release is immediately blocked.
The discoverer records an escalation receipt; the Coordinator/Architect emits
an `EXECUTION_RELEASED -> BLOCKED` receipt and invokes the recorded rollback
target; and the Decision Chair moves the governance disposition to `REVISE`
with a new decision receipt. Work resumes only through a newly published,
independently reviewed, `ACCEPTED`, and separately execution-released revision.
Prior receipts and evidence remain immutable.
