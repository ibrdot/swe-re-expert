# Revisione individuale del catalogo — lotto 3

La revisione dell’intero report resta attiva. Questo lotto riguarda eas-workflows e tutti i quattro file del suo albero, compreso il nuovo package.json locale che rende esplicito il caricamento ES-module dello script senza modificare il package radice. Restano 2581 alberi da leggere e la riconciliazione del report per le 90 revisioni precedenti.

## Esito delle segnalazioni

La separazione di version/license dal campo allowed-tools era già corretta sulla base corrente. Sono stati corretti i trigger generici e classificato il rischio in base alle azioni effettive. I permessi descritti corrispondono al recupero di riferimenti dal helper installato e alla validazione CLI locale, senza autorizzare download di eseguibili mobili o feedback esterni.

## Correzioni aggiuntive

Il recupero reale dello schema ufficiale conferma l’envelope data, jobs obbligatorio e on opzionale. Il nome del singolo run e i contesti delle espressioni vengono distinti dai contesti dei job; eliminata l’alternativa jobs.* non documentata. Costi e requisiti degli store sono distinti da semplici modifiche YAML o letture pubbliche. L’esempio è una bozza concreta, non una build eseguita.

Lo script originale accettava URL arbitrari e risposte senza limite. La correzione accetta solo i tre riferimenti pubblici documentati, rifiuta redirect, impone deadline e dimensione massima, controlla errori/UTF-8, conserva una cache locale esterna al bundle con TTL limitato, no-store e scrittura atomica; non segue link per leggere la cache. Nessuna credenziale Expo è necessaria per questi riferimenti.

## Verifiche effettive e limiti

Undici test verificano i confini sullo script reale con risposte sintetiche esplicitamente limitate al test; il recupero reale dello schema tramite lo script corretto è riuscito (233142 caratteri). La bozza e il caso senza on passano il controllo strutturale dello schema corrente; la mancanza di jobs fallisce. Non sono stati configurati i formati URI del validatore locale, e gli esempi non li usano: non è una validazione completa di ogni campo possibile.

La sorgente corrente di expo/eas-cli workflow/validate.ts conferma il contesto autenticato/collegato e la validazione server. Nessuna CLI autenticata, build, submission, job a pagamento o feedback è stata eseguita. Suite locale completa140 gruppi, riferimenti e sicurezza documentale passati; CI/revisione semantica e attestazione dell’esatto head sono necessarie prima del merge. Gli hash e le modalità dei quattro file sono nel JSON del lotto.
