# Upstream helper restoration: runtime batch

Restored 83 support files across 26 canonical skill roots. Every upstream file was read as inert data and verified against its original Git blob SHA before copying. Licenses and attribution travel with each installing skill. This batch changes source files only; generated mirrors and indexes belong to canonical sync.

| Skill | Source repository | Pinned commit | Helper license | Files |
| --- | --- | --- | --- | --- |
| `apk-reverse` | `zhaoxuya520/reverse-skill` | `cab634bd855fc287f6e420c1f36fd1a6b9245960` | MIT | 1 |
| `aws-cdk-development` | `zxkane/aws-skills` | `68530c6f296ccd2f5e99c79782f3e0fbf962c51a` | MIT | 2 |
| `azure-ai-projects-py` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 11 |
| `azure-cosmos-db-py` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 8 |
| `azure-eventhub-py` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 3 |
| `azure-servicebus-py` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 3 |
| `diagram-generator` | `zhaoxuya520/reverse-skill` | `cab634bd855fc287f6e420c1f36fd1a6b9245960` | MIT | 1 |
| `docs-generator` | `zhaoxuya520/reverse-skill` | `cab634bd855fc287f6e420c1f36fd1a6b9245960` | MIT | 3 |
| `fastapi-router-py` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 1 |
| `frontend-slides-frontend-slides` | `zarazhangrui/frontend-slides` | `9906a34d640d2111f724544cbc50f7f130569ae1` | MIT | 2 |
| `hyperexecute-skill` | `LambdaTest/agent-skills` | `992638bccbc311f42c0bd8b2b3387a0d1ce6288d` | MIT | 4 |
| `ida-reverse` | `zhaoxuya520/reverse-skill` | `cab634bd855fc287f6e420c1f36fd1a6b9245960` | MIT | 3 |
| `matplotlib` | `K-Dense-AI/scientific-agent-skills` | `0936740e52033a6256085be5fc81e5e56d606110` | MIT | 6 |
| `omp-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `qoder-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `react-flow-node-ts` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 2 |
| `scanpy` | `K-Dense-AI/scientific-agent-skills` | `0936740e52033a6256085be5fc81e5e56d606110` | MIT | 5 |
| `skill-scanner` | `getsentry/skills` | `d18b7aa8ba878354e5c348310230e652f7690f9c` | Apache-2.0 | 4 |
| `vibe-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `warp-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `opencode-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `pi-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |
| `podcast-generation` | `microsoft/skills` | `fc164ba1d7a0c10377dbcc1c9ac07253b9329fdb` | MIT | 3 |
| `polis-protocol-a-self-optimizing-city-of-agents` | `ymxlx/polis-protocol` | `eb7d3a9ca8cca5f719c1b0bd4ee657adb3c13dcd` | MIT | 8 |
| `slideops` | `glukicov/slideops` | `ba43e89bc7936649be36a1796a62203f704f8c60` | MIT | 6 |
| `zcode-delegate` | `amElnagdy/delegate-skills` | `3aa72d681a79e2a9d09bd9a316353003ae1cb4a7` | MIT | 1 |

## Review boundaries

Source identity metadata and existing declared risks are preserved. Scripts are stored as regular non-executable files; they execute only when a user invokes their interpreter. Static review and repository checks do not certify future package downloads or live provider behavior. The frontend slide PDF exporter is adapted to serve a selected deck on loopback with path and Host restrictions, and it requires existing Playwright/Chromium rather than installing them. The PPTX extractor is documented to use a fresh output directory. The docs case initializer refuses an existing case directory, and the Matplotlib style configurator uses exclusive output creation with a separate preview path. Diagram-rendering notes cover local renderer execution and output replacement. The CDK validation script is scoped to the caller-selected project; the Service Bus CLI requires an explicit delete flag. Azure evaluation, Event Hubs, and Cosmos fixture side effects are described on their skill entrypoints. The HyperExecute helper retains its upstream CLI interface and warns that credentials passed as arguments may be visible to local process inspection. AAS-authored regression tests cover the loopback server, Service Bus delete guard, and Matplotlib output behavior. All AAS-authored helper code and regression tests are covered by the repository MIT license, outside the upstream license notices.

## Excluded support

The following original files are not restored unchanged:

- `apk-reverse/scripts/decode.ps1`: requires shared auto-bootstrap that can install downloaded tools without a pinned digest.
- `apk-reverse/scripts/frida-run.ps1`: requires the external shared auto-bootstrap framework.
- `apk-reverse/scripts/rebuild-sign-install.ps1`: requires shared auto-bootstrap and passes custom signing passwords in process arguments.
- `frontend-slides-frontend-slides/scripts/deploy.sh`: unconfined HTML asset paths and predictable temporary-directory rename/cleanup; not safe to redistribute unchanged.
- `ida-reverse/scripts/start.ps1`: requires shared auto-bootstrap and host service setup.
- `ida-reverse/scripts/install-autostart.ps1`: replaces and starts a hidden ten-year scheduled task; depends on the excluded service/bootstrap chain.
- `radare2/scripts/recon.ps1`: requires shared auto-bootstrap that can install downloaded tools without a pinned digest.

Other paths that are absent from a verified source revision, have unverified origin, or lack a redistribution license remain explicit prerequisites. They are not replaced with unrelated same-name files.
