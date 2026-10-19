# Revisione individuale dell’intero catalogo AAS

## Perimetro e stato

Base iniziale: `119af813d0ee0571d7c6e1fb5d0aa342ec4ee9f0`. L’inventario comprende **2.689 entrypoint canonici e 8.617 file tracciati sotto skills/**. La revisione precedente copriva solo 90 skill, non l’intero catalogo. Il nuovo obiettivo resta aperto finché ogni skill e tutti i file di supporto non hanno un esito individuale verificabile.

I 90 alberi della revisione precedente sono stati confrontati con il contenuto della base attuale: stessi file, modalità Git e hash. I risultati sono riutilizzabili tramite il [registro precedente](individual-skill-review-2026-10-14.md). Non si considerano esiti delle altre 2.599 skill.

## Report originale recuperato

Il report Atlas era basato su `af9e67a3c276096ea0787319cecf9a6bd01f5782` e conteneva 2.689 righe: 1.707 ok e 982 da sistemare, di cui 14 major. Tutti i percorsi corrispondono al catalogo attuale. Ogni segnalazione va confrontata con main: alcune sono già corrette, altre descrivono prerequisiti esterni o preferenze di lingua; non vanno applicate automaticamente. Anche i 90 alberi già revisionati richiedono la riconciliazione individuale delle segnalazioni originali.

## Primo lotto aggiuntivo

Sono stati letti integralmente otto alberi, ciascuno con un singolo SKILL.md. Quattro richiedono correzioni e quattro sono mantenuti. Le correzioni in questa PR devono ancora superare i controlli e il merge protetto; questo documento non dichiara conclusa la revisione del catalogo. Dopo questi otto alberi, restano 2.591 skill da esaminare.

### `00-andruia-consultant`

Stato: repair-prepared.

Read sole full entrypoint: diagnosis useful; corrected unconditional file overwrites/language override, unverified skill IDs and prompt-only mixed-language example. Source-only change awaiting gates.

### `10-andruia-skill-smith`

Stato: repair-prepared.

Read sole full entrypoint: practical authoring flow retained; concrete activation/example/output, repo-specific names, no mandatory private reasoning, publication boundary and truthful limitations corrected. Awaiting gates.

### `20-andruia-niche-intelligence`

Stato: repair-prepared.

Read sole full entrypoint: useful niche dossier retained; removed duplicate usage heading, simulated credentials and private-reasoning demand; jurisdiction/source/applicability distinctions plus dental worked example. Awaiting gates.

### `aas-compose-stack`

Stato: reviewed-retained.

Read full sole entrypoint and confirmed native-plugin packager supplies runtime/aas-core.cjs and complete catalog. Agent-owned exact IDs, project-declaration limits, preview-only planning, same-session evidence and secrets boundary are accurate. Requires local native plugin, does not perform installation.

### `aas-discover`

Stato: reviewed-retained.

Read full sole entrypoint: explicit-task discovery, pagination and supporting-file inspection, metadata not eligibility, no invented scoring or automatic execution. Verified three native entrypoints versus full MCP bundled catalog in packager.

### `aas-review-stack`

Stato: reviewed-retained.

Read full sole entrypoint and actual server/packager Workbench paths: local session artefacts, in-memory import/digest checks distinguished from semantic validity; correct fallback and apply/upload boundary. No source defect identified.

### `3d-web-experience`

Stato: repair-prepared.

Read complete sole entrypoint. Correct missing Canvas/useRef imports and meaningless mesh/fallback placeholders; actual Canvas fallback and project error-boundary requirement; register GSAP plugin with mount/cleanup context; pinned local tooling rather than global mutable install; triangle/transfer/FPS budgets illustrative, actual device testing and accessible DOM/reduced motion required. Verified primary R3F Canvas and glTF Transform docs. No live GPU test claimed.

### `ab-test-setup`

Stato: reviewed-retained.

Read complete sole entrypoint. Experiment hypothesis, alpha/power/MDE, sampling unit, SRM/tracking and fixed-horizon vs sequential distinction coherent. Executed literal Python math-only example, observed 14745 per variant as documented. No live experiment/analytics or causal certainty claimed; no defect found.

## Verifica e limiti

L’esempio Python di ab-test-setup è stato eseguito con il suo codice effettivo: 14745 osservazioni per variante. Le API Canvas/fallback sono state confrontate con la documentazione primaria. La revisione non equivale a un collaudo GPU, a un esperimento reale né a una certificazione di conformità. I controlli obbligatori e gli esiti Tessl/manual-review devono essere legati all’esatto head della PR prima del merge.

Le modifiche sono nei sorgenti; le copie Codex/Claude, i bundle e gli indici sono rigenerati per verifica e pubblicati in repository esclusivamente tramite la sincronizzazione canonica protetta. Nessun rilascio o deploy è incluso.

## Esito di ogni segnalazione del primo lotto

### `00-andruia-consultant`

- `meta_source`: source_type is optional in exact-base validator; source: personal remains historical attribution, not replaced with invented ownership. Added immutable earliest AAS copy and explicit lack of independently verified upstream origin/license.
- `lang`: Spanish is the intended Andru.ia audience, not a semantic defect. Preserve it and honor user language overrides; replace the mixed-language prompt with an actual Spanish output example.

### `10-andruia-skill-smith`

- `placeholder_when`: Fixed in this batch with concrete authoring trigger.
- `hardcoded_path`: Already removed on current main; procedure resolves repository root rather than a personal Windows path.
- `wrong_artifact`: Already corrected on current main: canonical SKILL.md, source-only PR and generated-sync boundary. Concrete worked design added.

### `20-andruia-niche-intelligence`

- `dup_when_section`: Removed duplicate usage section. Retained the existing activation-before-title arrangement; heading placement alone does not break a skill. Added explicit legal applicability and evidence workflow.

### `aas-compose-stack`

- `-`: Original ok verdict confirmed by direct full-entrypoint review; native-runtime packager or actual sample-size example independently checked.

### `aas-discover`

- `-`: Original ok verdict confirmed by direct full-entrypoint review; native-runtime packager or actual sample-size example independently checked.

### `aas-review-stack`

- `-`: Original ok verdict confirmed by direct full-entrypoint review; native-runtime packager or actual sample-size example independently checked.

### `3d-web-experience`

- `templated_triggers`: Replaced keyword template with actual product-configurator, performance-diagnosis, stack-choice and accessible scroll-scene tasks; also corrected all documented snippet imports/fallback placeholders.

### `ab-test-setup`

- `-`: Original ok verdict confirmed by direct full-entrypoint review; native-runtime packager or actual sample-size example independently checked.

## Controlli locali

- Suite completa: 139 gruppi passati. Un primo tentativo era fallito per la rigenerazione concurrente durante il packaging; la ripetizione con generatori terminati è passata senza modificare i test.
- L’esempio statistico effettivo produce 14745; i sette blocchi JSX/JavaScript della guida 3D sono stati analizzati sintatticamente. Questo non prova un rendering reale.
- Validazione di sorgenti, riferimenti e sicurezza documentale richiesta prima del commit; CI e revisione semantica devono essere ricontrollate sull’esatto head pubblicato.
