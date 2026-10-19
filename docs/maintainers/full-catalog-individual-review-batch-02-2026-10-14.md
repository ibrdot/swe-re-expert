# Revisione individuale del catalogo — lotto 2

Perimetro invariato: tutte le 2689 skill del report originale. Questo lotto aggiunge nove alberi letti integralmente, sei correzioni e tre mantenuti. Non conclude l’audit. Le 90 revisioni precedenti richiedono ancora riconciliazione individuale del report; 2582 alberi restano da leggere.

## `ai-agent-tool-routing`

Complete sole entrypoint and immutable upstream PR1752 source compared. Original generic Web3 register confirmed, not lost richer guidance. Replace with tool/principal/schema/authorization/runtime/retry contracts, consistent string IDs and actual draft JSON-schema example. No router deployment or authentication proof claimed.

Segnalazioni originali: registro web3/Stellar (RPC, relayer, smart contract) in una skill generica "AI agent tool routing"; esempi e note fuori dominio

## `ai-code-generation-guardrails`

Complete sole entrypoint and immutable PR1753 source compared byte-identical to base. Replace irrelevant reentrancy/CEI/RPC boilerplate and impossible zero-day claims with language/tool coverage, source-bound checks and bounded actual AST teaching helper. Static no-match remains review-required; unsupported/invalid inputs incomplete. Declared attribution unchanged.

Segnalazioni originali: boilerplate di registro web3/Soroban; esempi fuori dominio (firma transazioni, RPC on-chain) per un tema AST Python/Rust generico

## `ai-prompt-regression-testing`

Complete sole entrypoint/upstream PR1752 source compared. Replace blockchain boilerplate, closed stale model enum, unexplained similarity thresholds and unobservable private-reasoning verification. Actual fixed-case regression helper rejects incomplete/duplicate/unexpected outcomes and retains known failures; no provider/judge execution claimed.

Segnalazioni originali: boilerplate web3/Soroban (firma transazioni, RPC on-chain) per un tema prompt-regression; modelli datati

## `build`

Read both entire entrypoint and 16600-byte detailed guide before edits; inspect full resulting diff. Original nested-frontmatter issue already fixed on base. Repair additional tool-specific/repeated questioning, unsafe feature-path construction and false completion from artifact presence. Preserve workflow/templates and attached plans; actual validation required.

Segnalazioni originali: la description contiene un secondo blocco frontmatter annidato (name/description duplicati) al posto della descrizione

## `django-access-review`

Read entire sole entrypoint. Original nested-description issue already fixed on base. Repair claimed universal access impossibility and incomplete permission example: actual imports, authenticated context before lookup, owner-scoped query and explicit tenant/shared-policy limits. Only authorized staging negative requests; no complete Django app/runtime test claimed.

Segnalazioni originali: titolo/description duplicati: frontmatter contiene un secondo blocco "--- name: django-access-review ... --- LICENSE" incorporato nella description

## `score-eval`

Read entire sole entrypoint. Original imported placeholder/thin workflow already fixed on base; classify critical manually for optional supplied-code execution and report mutation, preserving origin. Add fixture review/isolation/no implicit production action boundaries; caller rubric remains authoritative.

Segnalazioni originali: skill importata con description placeholder ('Imported skill... from upstream source'), risk: unknown, 35L

## `aws-skills`

Complete sole entrypoint read. Original near-empty stub already replaced on current main with actual planning/input/inventory/IAM/network/cost/rollback flow. Verified upstream repository still exists; explicit external selected workflow/prerequisite, authorized cloud scope and real vs simulated checks preserved. No cloud deployment proof claimed.

Segnalazioni originali: contenuto quasi vuoto/templato; descrive se stesso e rimanda alla repo, nessuna procedura reale

## `skill-seekers`

Complete sole entrypoint read. Original duplicate placeholder import already corrected on base. Concrete source/license/scope/tool-help/conversion/full-support-review/target validation sequence; explicit untrusted-source and separate install boundaries. Upstream repository exists; no fabricated conversion flags or executed conversion claimed.

Segnalazioni originali: description e body sono la description upstream ripetuta con trattino iniziale; 'When to Use' malformato; 34L

## `superpowers-lab`

Complete sole entrypoint read. Original thin import already repaired on base. Actual matched baseline/experimental fixture protocol, fixed configuration/permissions/budget, evidence/confounders and separate adoption boundary. Verified original repository exists; no experiment performance claim.

Segnalazioni originali: 34L, description 'Lab environment for Claude superpowers', When to Use generico

## Verifica e limiti

Sette regressioni esercitano gli esempi effettivi: schema dei parametri, input AST incompleti, nessuna approvazione da semplice parsing, inventario mancante/duplicato e fallimenti visibili. Non chiamano modelli, router, AWS o altri servizi. Le fonti originarie dei tre registri AI sono state recuperate da head immutabili delle PR1752/1753: contenevano già gli stessi problemi, quindi non sono state copiate alla cieca. Gli ID, autore e source_repo restano invariati. Le copie generate sono riservate al merge canonico protetto. CI/revisione semantica e attestazione dell’esatto head sono ancora necessarie prima del merge.

Le due funzioni Python degli esempi vengono eseguite nei test soltanto quando i loro byte corrispondono alla revisione esplicita registrata. Una nuova definizione inserita nel Markdown richiede nuova revisione prima dell’esecuzione; un caso negativo verifica il rifiuto prima che venga valutata. Il test continua a usare le funzioni effettive, non una copia o un punteggio euristico.
