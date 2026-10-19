# Report skill repairs, source batch one — 2026-10-14

Protected base `d5ee36be322269c7c1250ba315d1435bfe97be08`. This source batch fixes the unresolved implementation and safety defects found during direct individual review of the setup, expansion and consolidation reports. It does not alter plugin membership or publish a release. The remaining cohort and complete 90-tree receipt follow in batch two; this document does not claim the whole task is already merged.

| Skill | Concrete repair |
| --- | --- |
| `agent-memory-systems` | Replace invented MemoryStore, tenantless extraction and destructive consolidation; preserve originals, namespace identity and conflicts; model migration uses separate collection and source recovery. |
| `ai-security-hardening` | Regex is advisory; verify JWT issuer/audience/expiry and complete signed model inventory instead of invented aggregate hashes. |
| `ai-sre-incident-response` | Remove direct push rollback, unenforced freeze claims, production-as-offline evaluation, shared private caches and production chaos examples. |
| `alerting-oncall` | Close broken fence; remove generic PostgreSQL pod deletion; actual on-call infrastructure remains a prerequisite. |
| `api-testing-observability-api-mock` | Add complete isolated fixture resolver; fix synchronous await and documentation generator syntax; no credential-header recording; remaining framework adapters explicitly not bundled. |
| `audit-logging` | Remove fictional standards retention minima, raw exception logs, automatic alerts and checksum-as-immutability claims; declare privileged Linux scope correctly. |
| `beautiful-prose` | Remove nonexistent test-case fixture dependency; retain English style scope and inline examples. |
| `billing-automation` | Replace unsafe incomplete charging skeleton with stable tenant/invoice/action keys, Decimal proration, actual billing anchors, unknown-tax rejection and reconciliation contract. |
| `ci-cd-and-automation` | Shell rollback input moved to validated environment value; deployment token quoted; define locked tools, protected environments and untrusted-PR boundary. |
| `copy-editing` | Synthetic numeric copy must be supported before publication; retained evidence-first editing workflow. |
| `database-design` | Missing/unsupported/regex-only schema inspection exits nonzero and never certifies validity; correct stale PlanetScale/Prisma comparisons; all eight files inspected. |
| `database-migrations-sql-migrations` | Backfill real verification evidence before defaults; remove arbitrary identifier/query interpolation and automatic snapshot restoration; concurrent indexes outside transactions; no invented plugins. |
| `dependency-management-deps-audit` | Remove forced updates and user lockfile restoration; remove fake universal license matrix/clean provider failures; document incomplete scanning, locked CI and opt-in notifications. |
| `deployment-pipeline-design` | Remove missing template promises and broken multi-job scaffold; route Service through selectors; delayed execution is not approval; missing metrics cannot imply healthy deployment. |
| `deprecation-and-migration` | Preserve archived migration notices instead of deleting guidance users still need. |
| `error-handling-patterns` | Replay-safe classified retries; half-open failure reopens circuit; remove raw error logs, arbitrary financial-rate fallback and unsafe payment skeleton; no phantom support files. |
| `frontend-api-integration-patterns` | Mutations do not retry by default; classified transient errors only; captured request identity prevents stale result publication. |
| `frontend-data-contracts` | Runtime JSON parsing and branded types are distinct; document real adapters and error handling, repair truncated trigger. |
| `gitlab-ci-patterns` | TLS CA file replaces insecure skip, quoted password stdin, blocking security scan and actual inline prerequisites. |
| `incident-runbook-templates` | Fix invalid duration alias and nested fences; remove unscoped termination and emergency VACUUM FULL, bind recovery to exact authorized target. |
| `mcp-server-security` | Realpath containment rejects sibling/link escapes and returns canonical path; fixed query IDs bind values; stderr audit omits payload values, URL origin checks distinguish DNS/redirect enforcement; incomplete namespace sandbox removed. |
| `native-data-fetching` | Authenticate and authorize before balance fetch, verify outbound origin before sending token, bound replay-safe retries/cancellation; recover four screen states from current Expo source and distinguish SDK 55–57 from 58+ loaders. |
| `on-call-handoff-patterns` | Fix nested Markdown fence; preserve handoff evidence and explicit responder ownership. |
| `page-cro` | Remove mandatory fake 0–100 readiness gate before context; evidence-driven assessment and bounded experiment inputs, close malformed fence. |
| `presentation-deck` | Self-contained intake instead of mandatory external shared contract/Notion routing; repair nested relative link and distinguish templates from workspace writes. |
| `python-testing-patterns` | Import os in marker example, skip intentionally unimplemented test skeletons rather than report them passed; retain repaired async/negative fixtures. |
| `security-compliance-compliance-check` | Unknown evidence register instead of fictional dashboard; digest not tamper-proof storage; no erasure completion before all destinations, no missing-factor MFA, no invented DPO or universal PCI deadlines. |
| `security-requirement-extraction` | Unknown threat ratings fail instead of guessed priority; mapping counts never certify control coverage; framework edition/applicability still needs qualified evidence. |
| `supply-chain-security` | Remove unpinned global installs/actions, implicit RULES/tool-index dependency and unsourced percentage; uploads/monitoring opt-in with actual scope. |
| `testing-patterns` | Incomplete Jest scaffolds use it.todo; missing waitFor import supplied, existing negative cases retained. |
| `workflow-orchestration-patterns` | Replace invented Python get_version with SDK-bound patched guidance; missing orchestration resources no longer promised. |

The ten inert regressions in `tools/scripts/tests/test_report_skill_repairs.py` consume actual canonical examples. Required validation, references, security, warning budget, source credits, full unsharded tests, truthful semantic review and exact-head maintainer attestation remain mandatory. Canonical mirrors and registries are generated for evidence, then excluded from this source PR. Original provenance/risk declarations are preserved; upstream MCP/memory defects were confirmed and locally repaired rather than blindly reimported. No actual payment/provider/cloud operations were executed.
