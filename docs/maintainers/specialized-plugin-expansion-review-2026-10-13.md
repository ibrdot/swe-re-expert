# Specialized plugin expansion review — 2026-10-13

Protected base: `cb30121a2dfd007531bd2fbefb56f68de927da6a`. Package version: 19.5.0. No release is part of this source refresh.

## Scope and selection

Inventoried metadata for all 2,687 baseline canonical skill entries (2,688 after the new skill) and the 58 editorial bundles. Reviewed the purpose and membership of all 21 specialized packs. The full corpus inventory is discovery evidence, not a manual certification of all 2,687 procedures. Keyword retrieval helped locate candidates; it did not decide quality, safety, eligibility or ordering in AAS Core.

Manual review of the selected addition cohort covers 34 complete canonical skill trees, including tracked support files, provenance declarations, risk, scope and limitations. Repaired trees also include the canonical maintainer skill. Existing selected members retain their earlier reviews; this pass does not claim a fresh complete semantic review of every existing member. No inspected scripts, payment examples, cloud commands or external automations were executed.

All 21 plugin IDs and existing members remain stable. Add 48 memberships using 34 canonical skills: 33 existing and one new self-authored `api-contract-testing` skill; no third-party import. Compositions now have 6–13 skills. The editorial guard allows 5–20 distinct members and rejects oversized packs or duplicate filler. Both host target declarations remain required.

## Composition decisions

| Plugin | Before → after | Added workflow skills |
| --- | ---: | --- |
| AAS Web App Builder | 10 → 13 | `build-ui`, `ui-states`, `frontend-api-integration-patterns` |
| AAS Product Design Studio | 10 → 13 | `write-design-md`, `ui-from-screenshot`, `ui-states` |
| AAS Security Engineer | 10 → 12 | `threat-modeling-expert`, `skill-security-audit` |
| AAS Secure App Builder | 9 → 11 | `security-requirement-extraction`, `threat-modeling-expert` |
| AAS Documents & Presentations | 9 → 11 | `doc-coauthoring`, `copy-editing` |
| AAS Data Analytics | 10 → 12 | `sql-optimization-patterns`, `data-storytelling` |
| AAS Agent & MCP Builder | 10 → 13 | `skill-security-audit`, `agent-harness-fault-injection`, `agent-evaluation-reporting` |
| AAS QA & Test Automation | 10 → 13 | `testing-patterns`, `api-contract-testing`, `python-testing-patterns` |
| AAS DevOps & Cloud | 10 → 11 | `secrets-management` |
| AAS Marketing, SEO & Growth | 10 → 13 | `product-marketing-context`, `copy-editing`, `content-strategy` |
| AAS Automation Builder | 10 → 12 | `api-integration`, `api-rate-limit-handler` |
| AAS Observability IR | 10 → 12 | `on-call-handoff-patterns`, `ai-sre-incident-response` |
| AAS Python API Builder | 10 → 13 | `api-security-best-practices`, `sql-optimization-patterns`, `api-rate-limit-handler` |
| AAS Mobile App Builder | 10 → 12 | `ios-screens`, `frontend-api-integration-patterns` |
| AAS Accessibility & Inclusive UX | 8 → 10 | `wcag-audit-patterns`, `ui-states` |
| AAS API Platform Builder | 10 → 13 | `api-contract-testing`, `api-rate-limit-handler`, `deprecation-and-migration` |
| AAS SaaS Launch & Revenue | 10 → 13 | `usage-based-pricing`, `onboarding-cro`, `product-marketing-context` |
| AAS AI Product & Evaluation Ops | 10 → 13 | `advanced-evaluation`, `skill-security-audit`, `agent-evaluation-reporting` |
| AAS Data Engineering Platform | 10 → 11 | `warehouse` |
| AAS Privacy & Compliance Engineering | 5 → 6 | `data-privacy-controls` |
| AAS Localization & International Growth | 10 → 12 | `copy-editing`, `seo-content-refresher` |

Each addition has its own workflow summary in `data/editorial-bundles.json`. Updated purpose statements and starter prompts name the new coverage. Multi-framework packs use only the current project stack; privacy templates do not claim compliance, security testing still requires target scope, and office/automation skills do not provision connectors or credentials.

## Selected-tree byte inventory

Digests below bind ordered relative file paths and SHA-256 file digests in the reviewed source tree. They are reproducible review receipts, not upstream license or tool-execution proof. An exact PR-head attestation is still required by the merge gate.

| Skill | Tracked files | Review tree SHA-256 |
| --- | ---: | --- |
| `advanced-evaluation` | 1 | `511e90aef99c1aefcc8d17b1c0762d3bd974a4b8d11ef6fa21a4f2653743f147` |
| `agent-evaluation-reporting` | 1 | `9af818fb4104f3c50fce508c8fa07ed8eb217edf8a658bdaaf7532056df877ce` |
| `agent-harness-fault-injection` | 1 | `814364560f021181b430a331b1ee08ff9924e7cf28f2cd10b50100c720d09cda` |
| `ai-sre-incident-response` | 1 | `1c4817b87392712c269f87ff2b8ede2b4cfbc143371f80d400c4eaac3bade097` |
| `api-contract-testing` | 1 | `6193ce01d89928589a6e59e6ce78a32eeeb29666dff438c135205d762ce652e9` |
| `api-integration` | 1 | `bce77afc5715f6511db03b0dfd95817ada00f0ae609c4210447ed27f112d8be2` |
| `api-rate-limit-handler` | 1 | `e53831e4027ef5933dbf449b08975cd293ed037f0056a3efda3bbf65b46da7c8` |
| `api-security-best-practices` | 1 | `74257e552344383ab89e3138d99cefad6918f78d0eec99e2f5846c537418e925` |
| `build-ui` | 1 | `dc98d1374289f6cfe9f927552608802c68a60895ed3d38a086d6263dfd8d5ee5` |
| `content-strategy` | 3 | `a570f8fb6f890940895bf1e99bda823f914dcca96b2645b83bb1363a5f4e356b` |
| `copy-editing` | 1 | `99b4e7f763439bdbca2b932d08f6a90fe8a8beb51b52d16b165738285db86599` |
| `data-privacy-controls` | 1 | `905e3a237936e4540e497585fa9341b23121ce399b0825e4d1fa494f59a4e1a0` |
| `data-storytelling` | 1 | `06307450756573626ead11ff4adf1e8fda7fd24d4f5999902287a63336b58f17` |
| `deprecation-and-migration` | 1 | `f7eff6e94338719ced0d3db679bda1c1f12f792aecd7bdc600e4291a5439239d` |
| `doc-coauthoring` | 1 | `1a1df9d62908b6031f315f8d1a81c3aa17e182abc64cc5f3d9a8751a4ea93daf` |
| `frontend-api-integration-patterns` | 1 | `1850adda2a37b048c6e8f28f40d52b2ea2170ffb239dc13c110f57cf1f68d732` |
| `ios-screens` | 1 | `e3683f6a912e5d1f6d7337e5d8f1b8d782e5392b07c7208f8cac765182d6fe6f` |
| `on-call-handoff-patterns` | 1 | `72f7c07761f1e09977eef777a576a58fb3bb2ec61736ba4b6ac478764ce77f4b` |
| `onboarding-cro` | 1 | `ef944eef08563d9995912ca8e7ce5bea616ac4cb0288421d114b0577eb258397` |
| `product-marketing-context` | 2 | `1187f815887214f889e02a1f84c78f968eb73d55ae9eecc29f85503ec23a9f25` |
| `python-testing-patterns` | 2 | `53658bac4ec17b531b2609d121466a2ddf5d9def8d8358c94c288e1e74fc0880` |
| `secrets-management` | 3 | `8e6d870407521dec0b5d35093136b6c978bd76d595c22f7b067459fc6585cbb0` |
| `security-requirement-extraction` | 2 | `117283b566b3e330255a05899aaa22a9de33341c23fccbaada5472620e223738` |
| `seo-content-refresher` | 1 | `ea8d703cf36dac0130b70ce545c8e98f091c51eae7f17642bfe57019044c6b11` |
| `skill-security-audit` | 1 | `22429ed7637790d8c59bbd70f4cd10efedf2c87b00d40c1c882516bea2a8d6dc` |
| `sql-optimization-patterns` | 2 | `5460d1aa5be2295b6832bf5480c5018bade9bd85f40d0725d3e3c91181016d61` |
| `testing-patterns` | 1 | `11f61de2a52ebd0d28ce6b048a565eda014cdabda15f56179ce6c4caef9a67f8` |
| `threat-modeling-expert` | 1 | `c23668310bca3732cf000e82135c07c3b314f5522bc0767d03f6f2e6bf6558d9` |
| `ui-from-screenshot` | 1 | `f62d1541450cf413e750f1b94217b62811bbdd39f8cb1216a6921c41c0a22673` |
| `ui-states` | 1 | `287685f7ea94c67194236777c0db67e454130e4672ebd81ebdeaf55ba69710d5` |
| `usage-based-pricing` | 3 | `bb33d50c6ef8ba3b435b691c4128167b0fab14127c1c340359acf7374d9d7cef` |
| `warehouse` | 1 | `1ba9fe666a286d6829c565c843cfa022f2ef381ac4c85b4ea8444625c4a4926d` |
| `wcag-audit-patterns` | 2 | `fa5e3b2258274ec260b07fee10fa4e111be64d58a861233216856a53d02f953f` |
| `write-design-md` | 1 | `454bb08bcd5709df78e1a51e9ef75cd0666e169dc411f867f4c4e753f6ae824b` |

## Content repairs

The reviewed cohort needed concrete repairs before promotion: correct async assertions and Python negative fixtures; explicit webhook rejection even under Python optimization; bounded retry classification and unshortened provider waits; per-minute cost units; real contrast colors; weighted totals and savings arithmetic; valid evaluator JSON and measured confidence; self-contained local templates and truthful refresh dates. Removed unavailable support-file pointers and promotional routing. Current provider prices are verified inputs, not assumed constants.

The HTTP wait guidance follows [RFC 9110 §10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3). The contrast regression uses [WCAG contrast guidance](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Pure example tests execute published snippets with fake responses and inert values; they do not prove live provider integration or full accessibility conformance.

Changed canonical trees: `advanced-evaluation`, `ai-sre-incident-response`, `antigravity-maintainer-batch-release`, `api-contract-testing`, `api-integration`, `api-rate-limit-handler`, `content-strategy`, `data-privacy-controls`, `data-storytelling`, `deprecation-and-migration`, `on-call-handoff-patterns`, `onboarding-cro`, `python-testing-patterns`, `seo-content-refresher`, `testing-patterns`, `usage-based-pricing`, `wcag-audit-patterns`.

## Candidates deferred or intentionally omitted

These observations justify not adding a candidate to another focused pack. They are not a repository-wide vulnerability assessment. Overlap and external prerequisites also justify omission. The candidates remain canonical and independently selectable.

- `supply-chain-security`: Unpinned executable install/action examples, implicit tool-index/RULES dependency, unsourced reachability percentage, uploads/monitoring without scoped approval. Not promoted into a new focused bundle.
- `dependency-management-deps-audit`: Remediation example uses npm audit fix --force and unscoped git checkout of user lockfile; defer until hardened.
- `audit-logging`: Privileged Linux-specific examples contradict no-privileged-tool compatibility, retention table needs independent standards review, example logs raw exception text and emits external webhook alerts without explicit boundary.
- `swiftui-ui-patterns`: Existing ios-developer plus new ios-screens covers the requested native-screen workflow; avoid adding another overlapping 32-file platform guide.
- `accessibility-compliance-accessibility-audit`: Prefer the concrete WCAG criteria playbook alongside current audit tools; do not add two broad audit personas.
- `mcp-server-security`: Path helper realpath check accepts sibling-prefix escapes; SQL keyword blacklist is not a read-only security boundary; sample emits audit events to stdio stdout. Use scoped skill-security-audit instead.
- `extract-document-data`: Useful grounded extraction, but hosted upload/credits are unnecessary for the generic office bundle; prefer the reviewed coauthoring and editing workflow.
- `deployment-pipeline-design`: Promised playbook, approval-gate template and orchestration reference are absent; retain existing delivery coverage.
- `presentation-deck`: Mandatory SME shared execution contract and brand/Notion module routing outside the document pack; nested relative reference is unresolved. Do not broaden the pack with this dependency chain.
- `ci-cd-and-automation`: Deployment/rollback example interpolates GitHub input into shell; retain existing GH templates.
- `beautiful-prose`: English literary style contract plus missing test-cases resource; not a neutral default for the general office plugin.
- `agent-memory-systems`: Unverified LangMem/SDK API samples and hosted-memory operations; background examples omit tenant identity and consolidation deletes originals. Not promoted into a new starter bundle.
- `api-testing-observability-api-mock`: Large illustrative scaffold with unimplemented helpers and malformed nested documentation snippet; prefer the bounded contract-propagation audit for QA expansion.
- `page-cro`: Uncalibrated readiness score is mandatory before context; arbitrary score threshold blocks experimentation, and tail contains unmatched fence. Prefer content-strategy with actual audience evidence.
- `gitlab-ci-patterns`: Missing promised files, insecure-skip-tls-verify, password on command line and allow-failure security scan; retain current delivery skills and add only secrets-management.
- `incident-runbook-templates`: Missing playbook and unsafe generic production examples including invalid duration alias and unscoped backend termination; do not promote as production-ready.
- `alerting-oncall`: Prerequisite services and privileged remediation templates broaden the new pack unnecessarily; choose the scoped handoff guide for continuity instead.
- `database-design`: Prisma/Drizzle helper returns passed for missing or unsupported schemas and always exits success; provider comparisons are stale, and this is not the strongest Python-focused addition. Use reviewed SQL optimization instead.
- `error-handling-patterns`: Detailed playbook promises six unbundled resources and includes broad retries/raw exception logging; use the reviewed bounded API retry guide for the Python pack.
- `native-data-fetching`: Web loader example fetches and serializes Stripe balance before verifying a session, using cookie presence as authentication. Use framework-neutral reviewed frontend integration patterns; defer native guide until hardened.
- `billing-automation`: Legacy non-idempotent charge example, fixed 30/365-day billing intervals, unknown jurisdiction treated as zero tax, and eight promised support resources absent. Use usage-based-pricing plus existing Stripe integration instead.
- `llm-evaluation`: Missing playbook and eight support files, invented EvaluationSuite quick start, overwritten boolean-key kappa interpretation and incomplete regression comparisons; prefer advanced-evaluation and reporting.
- `ai-security-hardening`: Input/output regex examples cannot establish an injection or SQL/XSS security boundary; JWT example lacks issuer/audience requirements and model hash example does not bind verified model identity. Prefer scoped skill-security-audit.
- `workflow-orchestration-patterns`: Missing playbook and SDK-specific versioning advice without host/version binding; retain existing automation guidance and add focused API retries.
- `database-migrations-sql-migrations`: Backfill selects NULL after adding DEFAULT FALSE and equates presence of confirmation token with verified email; rollback interpolates identifiers and bulk index recreation runs CONCURRENTLY inside DO. Defer production migration guide.
- `security-compliance-compliance-check`: Support guide labels scaffold as compliant, supplies fixed fictional dashboard metrics and claims tamper-proof storage from a checksum with unimplemented storage; prefer empty control-register templates.
- `cross-platform-contract-propagation-audit`: Useful reviewed audit, but qualified Codex names exceed the 64-character guard in QA/API packs. Retain canonical ID and add a self-contained api-contract-testing workflow instead.
- `frontend-data-contracts`: Reviewed as a possible shorter substitute; its React/React Native client discipline does not cover the generic provider/consumer QA job. Keep separate instead of forcing it into backend testing.

## Verification and publication boundary

Required validation, references, documentation security, warning budget, source credits, complete unsharded script tests, web coverage/build, specialized source/packaging/resource tests and compatibility checks run on this branch. Their exact outcomes are recorded in the PR after completion. New negative tests reject oversized/duplicate membership, premature/unsafe API retries, invalid webhook signatures, missing async UI outcomes and malformed evaluator JSON. Arithmetic and contrast tests consume the published examples.

Regenerate mirrors and marketplaces for local inspection, but commit editorial sources and canonical repairs only. The protected canonical-sync PR owns generated files and final byte parity. This change does not bump package versions, publish npm, update installed plugins/MCP hosts or authorize a Pages deployment. Verify resulting protected main CI and CodeQL after synchronization; release-bound catalog links continue to point at the published version until a release is requested.

### Review follow-up

Tessl returned 71/80 on the first advanced-evaluation revision and stopped before subsequent trees. Concrete feedback was addressed with an explicit held-out human-calibration workflow, compact pipeline, direct description and removal of ambiguous internal references. Final automated results and any manual exact-head attestation are recorded in the PR.

The first static advisory report inspected 17 trees: eleven reported complete, five were partial, and the maintainer guide had a nonzero result with partial coverage. Inspected all 22 findings individually: documented endpoints, mocked calls/temp-file examples, HTML good/bad comments, warning descriptions and maintainer scanner-reference limitations were contextual. Two unpinned accessibility CLI invocations were actionable; replaced them with existing project-local binaries on an authorized local/test target and added a negative regression. No baseline or suppression was introduced. The final report must be bound to the final PR head before merge.
