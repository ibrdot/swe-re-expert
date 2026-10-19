# Confirmed skill documentation repairs

This batch repairs a reviewed subset of the October 2026 skill audit. It does not adopt the audit’s language, risk, template-style, or brevity judgments as automatic defects.

## Scope and validation boundaries

- Only canonical SKILL.md files are source changes. Generated indexes, plugin mirrors, and bundle content remain owned by canonical synchronization.
- Names, risk classifications, source identity, source repositories, source type, and introduction dates are preserved.
- Malformed descriptions, repeated trigger phrases, duplicate imported body metadata, broken documentation links, and obligatory vendor promotions are corrected.
- Four stub entries now describe concrete, bounded workflows with explicit external inputs rather than repeating a repository description.
- Optional references to absent implementation-playbook.md files are removed while preserving inline instructions.
- Other absent supporting materials are explicitly external prerequisites. This repair does not claim to reconstruct or bundle upstream helper scripts: dependent steps stop until the required material has been located and reviewed.
- Example-only application paths are excluded. Rechecking also excluded eas-simulator and platform-engineering: neither has the defect attributed by the original verification report.
- No upstream helper, cloud operation, installation into a user agent, or integration service was executed. Runtime behavior of external tools remains outside this documentation batch.
- internal-comms uses the Apache-2.0 license in its bundled LICENSE.txt. django-perf-review uses Apache-2.0 verified in the upstream skill’s own LICENSE. The unavailable hugging-face-jobs snapshot’s non-SPDX placeholder is omitted instead of guessing its license.

## Canonical entries changed

| Skill | Repair |
|---|---|
| `10-andruia-skill-smith` | correct AAS artifact and relative repository path |
| `agent-framework-azure-ai-py` | declare exact missing external prerequisites and guard dependent steps |
| `agentic-actions-auditor` | declare exact missing external prerequisites and guard dependent steps |
| `ai-analyzer` | declare exact missing external prerequisites and guard dependent steps |
| `ai-studio-image` | declare exact missing external prerequisites and guard dependent steps |
| `alpha-vantage` | remove mandatory vendor upsell |
| `angular-migration` | declare exact missing external prerequisites and guard dependent steps |
| `anti-reversing-techniques` | repair discovery description |
| `api-analyzer` | remove mandatory commercial follow-up |
| `api-designer` | declare exact missing external prerequisites and guard dependent steps |
| `api-sdk-generator` | remove mandatory commercial follow-up |
| `apk-reverse` | declare exact missing external prerequisites and guard dependent steps |
| `architecture-review` | repair malformed documentation links |
| `arm-cortex-expert` | remove unavailable optional playbook pointer |
| `automated-triage` | declare exact missing external prerequisites and guard dependent steps |
| `aws-cdk-development` | declare exact missing external prerequisites and guard dependent steps |
| `aws-sst-development` | declare exact missing external prerequisites and guard dependent steps |
| `azure-ai-projects-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-ai-voicelive-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-cosmos-db-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-cosmos-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-eventhub-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-mgmt-apimanagement-dotnet` | declare exact missing external prerequisites and guard dependent steps |
| `azure-resource-manager-cosmosdb-dotnet` | declare exact missing external prerequisites and guard dependent steps |
| `azure-resource-manager-sql-dotnet` | declare exact missing external prerequisites and guard dependent steps |
| `azure-search-documents-dotnet` | declare exact missing external prerequisites and guard dependent steps |
| `azure-servicebus-py` | declare exact missing external prerequisites and guard dependent steps |
| `azure-speech-to-text-rest-py` | declare exact missing external prerequisites and guard dependent steps |
| `bazel-build-optimization` | remove unavailable optional playbook pointer |
| `beautiful-prose` | declare exact missing external prerequisites and guard dependent steps |
| `binary-analysis-patterns` | remove unavailable optional playbook pointer |
| `biopython` | declare exact missing external prerequisites and guard dependent steps |
| `blockchain-developer` | remove unavailable optional playbook pointer |
| `brand-growth-system-builder` | declare exact missing external prerequisites and guard dependent steps |
| `build` | repair discovery description; remove upstream duplicate body metadata |
| `burpsuite-project-parser` | declare exact missing external prerequisites and guard dependent steps |
| `c-pro` | remove unavailable optional playbook pointer |
| `c4-architecture-c4-architecture` | remove unavailable optional playbook pointer |
| `c4-code` | remove unavailable optional playbook pointer |
| `c4-component` | remove unavailable optional playbook pointer |
| `c4-container` | remove unavailable optional playbook pointer |
| `c4-context` | remove unavailable optional playbook pointer |
| `cirq` | declare exact missing external prerequisites and guard dependent steps |
| `cline-pilot` | declare exact missing external prerequisites and guard dependent steps |
| `cloud-architect` | remove unavailable optional playbook pointer |
| `cmux` | declare exact missing external prerequisites and guard dependent steps |
| `code-review-ai-ai-review` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `code-review-and-quality` | declare exact missing external prerequisites and guard dependent steps |
| `code-reviewer` | remove unavailable optional playbook pointer |
| `comprehensive-review-full-review` | remove unavailable optional playbook pointer |
| `conductor-implement` | remove unavailable optional playbook pointer |
| `conductor-new-track` | remove unavailable optional playbook pointer |
| `conductor-revert` | remove unavailable optional playbook pointer |
| `conductor-status` | remove unavailable optional playbook pointer |
| `constant-time-analysis` | declare exact missing external prerequisites and guard dependent steps |
| `content-marketer` | remove unavailable optional playbook pointer |
| `context-kit` | declare exact missing external prerequisites and guard dependent steps |
| `context-management-context-save` | remove unavailable optional playbook pointer |
| `context-manager` | remove unavailable optional playbook pointer |
| `cost-optimization` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `cowork-to-code-bridge` | declare exact missing external prerequisites and guard dependent steps |
| `crossframe-suite` | declare exact missing external prerequisites and guard dependent steps |
| `crypto-bd-agent` | repair discovery description; remove null tags |
| `csharp-pro` | remove unavailable optional playbook pointer |
| `csv-manual-export` | declare exact missing external prerequisites and guard dependent steps |
| `customer-support` | remove unavailable optional playbook pointer |
| `data-engineering-data-driven-feature` | remove unavailable optional playbook pointer |
| `database-admin` | remove unavailable optional playbook pointer |
| `database-migration` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `database-optimizer` | remove unavailable optional playbook pointer |
| `debug-buttercup` | declare exact missing external prerequisites and guard dependent steps |
| `debugger` | remove unavailable optional playbook pointer |
| `debugging-toolkit-smart-debug` | remove unavailable optional playbook pointer |
| `defi-protocol-templates` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `dependency-upgrade` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `deployment-pipeline-design` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `deployment-validation-config-validate` | repair discovery description |
| `devcontainer-setup` | declare exact missing external prerequisites and guard dependent steps |
| `diagram-generator` | declare exact missing external prerequisites and guard dependent steps |
| `django-access-review` | repair discovery description; remove upstream duplicate body metadata |
| `django-perf-review` | use bundled SPDX license or omit unverified placeholder |
| `docs-architect` | remove unavailable optional playbook pointer |
| `docs-generator` | declare exact missing external prerequisites and guard dependent steps |
| `dotnet-architect` | remove unavailable optional playbook pointer |
| `doubt-driven-development` | declare exact missing external prerequisites and guard dependent steps |
| `dx-optimizer` | remove unavailable optional playbook pointer |
| `eas-workflows` | separate version/license from allowed tools |
| `elixir-pro` | remove unavailable optional playbook pointer |
| `error-detective` | remove unavailable optional playbook pointer |
| `error-diagnostics-smart-debug` | remove unavailable optional playbook pointer |
| `fastapi-router-py` | declare exact missing external prerequisites and guard dependent steps |
| `file-organizer` | repair discovery description |
| `firmware-analyst` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `framework-migration-legacy-modernize` | remove unavailable optional playbook pointer |
| `free-design-resources` | declare exact missing external prerequisites and guard dependent steps |
| `frontend-mobile-development-component-scaffold` | repair discovery description |
| `frontend-mobile-security-xss-scan` | repair discovery description |
| `frontend-slides-frontend-slides` | declare exact missing external prerequisites and guard dependent steps |
| `frontend-ui-engineering` | declare exact missing external prerequisites and guard dependent steps |
| `full-stack-orchestration-full-stack-feature` | remove unavailable optional playbook pointer |
| `gha-security-review` | declare exact missing external prerequisites and guard dependent steps |
| `git-pr-workflows-onboard` | remove unavailable optional playbook pointer |
| `git-pr-workflows-pr-enhance` | repair discovery description |
| `gitlab-ci-patterns` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `gmail-automation` | declare exact missing external prerequisites and guard dependent steps |
| `google-drive-automation` | declare exact missing external prerequisites and guard dependent steps |
| `graphql-architect` | remove unavailable optional playbook pointer |
| `haskell-pro` | remove unavailable optional playbook pointer |
| `hr-pro` | remove unavailable optional playbook pointer |
| `hugging-face-jobs` | use bundled SPDX license or omit unverified placeholder |
| `hugging-face-tool-builder` | declare exact missing external prerequisites and guard dependent steps |
| `hybrid-cloud-architect` | remove unavailable optional playbook pointer |
| `hybrid-cloud-networking` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `hyperexecute-skill` | declare exact missing external prerequisites and guard dependent steps |
| `ida-reverse` | declare exact missing external prerequisites and guard dependent steps |
| `incident-response-incident-response` | remove unavailable optional playbook pointer |
| `incident-response-smart-fix` | repair discovery description |
| `incident-runbook-templates` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `incremental-implementation` | declare exact missing external prerequisites and guard dependent steps |
| `internal-comms` | use bundled SPDX license or omit unverified placeholder |
| `istio-traffic-management` | remove unavailable optional playbook pointer |
| `iterate-pr` | declare exact missing external prerequisites and guard dependent steps |
| `java-pro` | remove unavailable optional playbook pointer |
| `javascript-typescript-typescript-scaffold` | repair discovery description |
| `julia-pro` | remove unavailable optional playbook pointer |
| `k8s-security-policies` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `langchain-architecture` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `legacy-modernizer` | remove unavailable optional playbook pointer |
| `legal-advisor` | remove unavailable optional playbook pointer |
| `linkerd-patterns` | remove unavailable optional playbook pointer |
| `llm-application-dev-ai-assistant` | repair discovery description |
| `llm-application-dev-langchain-agent` | remove unavailable optional playbook pointer |
| `llm-application-dev-prompt-optimize` | repair discovery description |
| `logic-review` | declare exact missing external prerequisites and guard dependent steps |
| `longbridge-content` | declare exact missing external prerequisites and guard dependent steps |
| `longbridge-fundamentals` | declare exact missing external prerequisites and guard dependent steps |
| `longbridge-market-data` | declare exact missing external prerequisites and guard dependent steps |
| `m365-agents-dotnet` | declare exact missing external prerequisites and guard dependent steps |
| `m365-agents-py` | declare exact missing external prerequisites and guard dependent steps |
| `m365-agents-ts` | declare exact missing external prerequisites and guard dependent steps |
| `machine-learning-ops-ml-pipeline` | remove unavailable optional playbook pointer |
| `makepad-basics` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-deployment` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-event-action` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-layout` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-shaders` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-widgets` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-animation` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-dsl` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-font` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-platform` | declare exact missing external prerequisites and guard dependent steps |
| `makepad-splash` | declare exact missing external prerequisites and guard dependent steps |
| `matplotlib` | declare exact missing external prerequisites and guard dependent steps |
| `memory-forensics` | remove unavailable optional playbook pointer |
| `mermaid-expert` | remove unavailable optional playbook pointer |
| `minecraft-bukkit-pro` | remove unavailable optional playbook pointer |
| `ml-engineer` | remove unavailable optional playbook pointer |
| `ml-pipeline-workflow` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `mlops-engineer` | remove unavailable optional playbook pointer |
| `mobile-security-coder` | remove unavailable optional playbook pointer |
| `monopoly` | declare exact missing external prerequisites and guard dependent steps |
| `monorepo-architect` | remove unavailable optional playbook pointer |
| `monte-carlo-analyze-root-cause` | declare exact missing external prerequisites and guard dependent steps |
| `monte-carlo-asset-health` | declare exact missing external prerequisites and guard dependent steps |
| `monte-carlo-monitoring-advisor` | declare exact missing external prerequisites and guard dependent steps |
| `monte-carlo-performance-diagnosis` | declare exact missing external prerequisites and guard dependent steps |
| `monte-carlo-remediation` | declare exact missing external prerequisites and guard dependent steps |
| `monte-carlo-storage-cost-analysis` | declare exact missing external prerequisites and guard dependent steps |
| `mtls-configuration` | remove unavailable optional playbook pointer |
| `multi-cloud-architecture` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `network-engineer` | remove unavailable optional playbook pointer |
| `networkx` | declare exact missing external prerequisites and guard dependent steps |
| `nft-standards` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `nsfw-ai-spicyapi` | declare exact missing external prerequisites and guard dependent steps |
| `nx-workspace-patterns` | remove unavailable optional playbook pointer |
| `observability-monitoring-monitor-setup` | repair discovery description |
| `odw` | declare exact missing external prerequisites and guard dependent steps |
| `offensive-osint` | declare exact missing external prerequisites and guard dependent steps |
| `offers` | remove duplicated trigger phrase |
| `onboarding` | remove duplicated trigger phrase |
| `payment-integration` | remove unavailable optional playbook pointer |
| `paypal-integration` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `pentest-tools/src-hunter` | declare exact missing external prerequisites and guard dependent steps |
| `performance-engineer` | repair discovery description |
| `performance-optimization` | declare exact missing external prerequisites and guard dependent steps |
| `power-user-cultivation` | remove duplicated trigger phrase |
| `product-marketing` | remove duplicated trigger phrase |
| `qiskit` | declare exact missing external prerequisites and guard dependent steps |
| `quant-analyst` | remove unavailable optional playbook pointer |
| `radare2` | declare exact missing external prerequisites and guard dependent steps |
| `react-flow-node-ts` | declare exact missing external prerequisites and guard dependent steps |
| `react-state-management` | remove unavailable optional playbook pointer |
| `risk-manager` | remove unavailable optional playbook pointer |
| `robius-app-architecture` | declare exact missing external prerequisites and guard dependent steps |
| `robius-event-action` | declare exact missing external prerequisites and guard dependent steps |
| `robius-matrix-integration` | declare exact missing external prerequisites and guard dependent steps |
| `robius-state-management` | declare exact missing external prerequisites and guard dependent steps |
| `robius-widget-patterns` | declare exact missing external prerequisites and guard dependent steps |
| `ruby-pro` | remove unavailable optional playbook pointer |
| `scala-pro` | remove unavailable optional playbook pointer |
| `scanpy` | declare exact missing external prerequisites and guard dependent steps |
| `search-specialist` | remove unavailable optional playbook pointer |
| `security-bluebook-builder` | declare exact missing external prerequisites and guard dependent steps |
| `sharp-edges` | declare exact missing external prerequisites and guard dependent steps |
| `shellcheck-configuration` | remove unavailable optional playbook pointer |
| `shipping-and-launch` | declare exact missing external prerequisites and guard dependent steps |
| `skill-scanner` | declare exact missing external prerequisites and guard dependent steps |
| `speckit-updater` | declare exact missing external prerequisites and guard dependent steps |
| `sred-project-organizer` | declare exact missing external prerequisites and guard dependent steps |
| `startup-analyst` | remove unavailable optional playbook pointer |
| `startup-business-analyst-business-case` | remove unavailable optional playbook pointer |
| `startup-business-analyst-financial-projections` | remove unavailable optional playbook pointer |
| `startup-business-analyst-market-opportunity` | remove unavailable optional playbook pointer |
| `tdd-orchestrator` | remove unavailable optional playbook pointer |
| `team-composition-analysis` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `technical-tutorials` | remove duplicated trigger phrase |
| `temporal-python-pro` | remove unavailable optional playbook pointer |
| `temporal-python-testing` | remove unavailable optional playbook pointer |
| `terraform-module-library` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `test-automator` | remove unavailable optional playbook pointer |
| `tune-monitor` | declare exact missing external prerequisites and guard dependent steps |
| `turborepo-caching` | remove unavailable optional playbook pointer |
| `tutorial-engineer` | remove unavailable optional playbook pointer |
| `ui-ux-designer` | remove unavailable optional playbook pointer |
| `ui-visual-validator` | remove unavailable optional playbook pointer |
| `uniprot-database` | declare exact missing external prerequisites and guard dependent steps |
| `unity-developer` | remove unavailable optional playbook pointer |
| `using-agent-skills` | declare exact missing external prerequisites and guard dependent steps |
| `using-neon` | declare exact missing external prerequisites and guard dependent steps |
| `variant-analysis` | declare exact missing external prerequisites and guard dependent steps |
| `vexor-cli` | declare exact missing external prerequisites and guard dependent steps |
| `video-content-extractor` | declare exact missing external prerequisites and guard dependent steps |
| `web3-testing` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `open-source-marketing` | remove duplicated trigger phrase |
| `performance-testing-review-ai-review` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `php-pro` | remove unavailable optional playbook pointer |
| `planning-and-task-breakdown` | declare exact missing external prerequisites and guard dependent steps |
| `playwright-java` | declare exact missing external prerequisites and guard dependent steps |
| `podcast-generation` | declare exact missing external prerequisites and guard dependent steps |
| `polars` | declare exact missing external prerequisites and guard dependent steps |
| `polis-protocol-a-self-optimizing-city-of-agents` | declare exact missing external prerequisites and guard dependent steps |
| `posix-shell-pro` | remove unavailable optional playbook pointer |
| `prometheus-configuration` | remove unavailable optional playbook pointer; declare exact missing external prerequisites and guard dependent steps |
| `prompt-engineering-patterns` | remove unavailable optional playbook pointer |
| `pubmed-database` | declare exact missing external prerequisites and guard dependent steps |
| `recsys-pipeline-architect` | declare exact missing external prerequisites and guard dependent steps |
| `reference-builder` | remove unavailable optional playbook pointer |
| `seo-authority-builder` | remove unavailable optional playbook pointer |
| `seo-content` | declare exact missing external prerequisites and guard dependent steps |
| `seo-directory-backlinks` | declare exact missing external prerequisites and guard dependent steps |
| `seo-image-gen` | declare exact missing external prerequisites and guard dependent steps |
| `seo-keyword-strategist` | remove unavailable optional playbook pointer |
| `seo-meta-optimizer` | remove unavailable optional playbook pointer |
| `seo-schema` | declare exact missing external prerequisites and guard dependent steps |
| `seo-snippet-hunter` | remove unavailable optional playbook pointer |
| `service-mesh-expert` | remove unavailable optional playbook pointer |
| `service-mesh-observability` | remove unavailable optional playbook pointer |
| `slideops` | declare exact missing external prerequisites and guard dependent steps |
| `spark-optimization` | remove unavailable optional playbook pointer |
| `workflow-orchestration-patterns` | remove unavailable optional playbook pointer |
| `zeroize-audit` | declare exact missing external prerequisites and guard dependent steps |
| `pricing` | remove duplicate when |
| `public-relations` | remove duplicate when |
| `aws-skills` | replace empty/stub workflow with concrete scoped procedure and explicit external inputs |
| `skill-seekers` | replace empty/stub workflow with concrete scoped procedure and explicit external inputs |
| `superpowers-lab` | replace empty/stub workflow with concrete scoped procedure and explicit external inputs |
| `score-eval` | replace empty/stub workflow with concrete scoped procedure and explicit external inputs |
