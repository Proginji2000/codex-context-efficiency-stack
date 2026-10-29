# P1.1 — App-server v2 : enquête offline sur les événements workers (Codex 0.165.0)

**Statut : outil d'analyse expérimental, pas une attestation de l'exécution du TUI V3.** Aucun modèle ou session réelle n'est lancé, lu, exporté ou modifié par cet outil.

## Référentiel épinglé (pas `main` amont)

Schémas officiels de **openai/codex** au tag `rust-v0.165.0` :

- [`ThreadItem.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadItem.ts) : `collabAgentToolCall` contient `tool`, `status`, `receiverThreadIds`; `subAgentActivity` expose `kind` et `agentThreadId`.
- [`CollabAgentTool.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/CollabAgentTool.ts) : `spawnAgent`, `sendInput`, `resumeAgent`, `wait`, `closeAgent`, etc.
- [`ItemStartedNotification.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ItemStartedNotification.ts) et [`ItemCompletedNotification.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ItemCompletedNotification.ts).
- [`ThreadTokenUsageUpdatedNotification.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadTokenUsageUpdatedNotification.ts), [`TokenUsageBreakdown.ts`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/TokenUsageBreakdown.ts) : `totalTokens`, `inputTokens`, `cachedInputTokens`, `outputTokens` et compteurs additionnels.

Le protocole **définit** ces données. Cela ne prouve pas qu'elles sont exposées à un abonné TUI indépendant dans le pilote Windows 0.165.0 ; l'ancien wrapper TUI n'enregistre pas les événements.

## Script

`scripts/Audit-CodexAppServer-Events.py` : entrée obligatoire et explicite `--input` vers un export JSONL **préparé et volontairement fourni par l'opérateur**, jamais un dossier de sessions ni le `CODEX_HOME`. Le script ne contacte pas app-server, ne lance pas Codex, ne découvre aucun fichier privé, ne crée aucun rapport sur disque et ne journalise pas l'entrée.

Seuls quatre types d'événements sont analysés : `item/started`, `item/completed`, `thread/tokenUsage/updated` et `turn/completed`. Les autres types sont ignorés. Aucun contenu `prompt`, `threadId`, `agentThreadId`, commande, chemin, texte de worker ou erreur brute n'est affiché. Les IDs sont utilisés **uniquement en mémoire** pour corréler des événements, puis oubliés.

Les contrôles fail-closed couvrent : duplications, valeurs et statuts invalides, succès de `spawnAgent` sans récepteur, incohérences de cache, compteur régressif, événement ou entrée trop volumineux. `subagent_started_and_completed_observed` signifie seulement que **les deux marqueurs figurent dans le fichier fourni**, pas que le TUI a réellement exposé ces événements, ni qu'un worker a été observé indépendamment. Les compteurs de tokens par threads peuvent se recouvrir et ne sont pas des coûts ni du quota.

## Tests synthétiques (sans modèle)

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Audit-CodexAppServer-Events.py
if ($LASTEXITCODE -ne 0) { throw 'Offline synthetic tests failed' }
```

Le test ne prend pas de session réelle, n'utilise pas d'authentification Codex et n'interroge pas le réseau. Les CI exécutent ces tests sous Windows et Ubuntu.

## Étape suivante avant toute vraie collecte

Déterminer si un **client app-server autonome** peut s'abonner à un TUI existant sans modifier le profil, sans reprendre les sessions privées ni déclencher de nouveaux tours IA. **Ne pas** supposer que le protocole d'app-server expose directement les événements du TUI déjà lancé : une preuve de coexistence et de provenance est nécessaire.

Si aucun flux autonome n'existe dans le CLI 0.165.0, garder `runtime_event_availability_in_pinned_cli_verified=false` et ne pas déclarer une attestation indépendante. Étudier alors un harness contrôlé pour de futurs benchmarks, avec protocole et consentement séparés, sans mélanger les résultats V2/V3.

Rattachements : issue #61, suivi #34, PR #14 OPEN ; données historiques V3 archivées dans `docs/P1_1_V3_RESULTS_2026-10-29.md`.
