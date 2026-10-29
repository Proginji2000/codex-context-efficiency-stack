# P1.1 — Agrégation A/B interactive TUI, phase instrumentation 1

Cet outil **hors modèle**, en lecture seule, traite les rapports `sanitized-tui-result.json` des sorties jetables existantes. Il ne lance ni Codex, ni restauration, ni commande dans d'autres projets, ni session worker.

## Pourquoi un outil séparé

`Compare-CodexAB.py` utilise les événements structurés de `codex exec --json`, tandis que les canaries TUI V3 disposent de rapports fonctionnels et de lignes de console `Token usage`. Le compteur `(+ ... cached)` du TUI n'est **pas** assimilable à `cached_input_tokens` des événements JSONL. Le script ne mélange jamais les contrats.

Le script `scripts/Summarize-CodexAB-TUI-Repeats.py` vérifie les quatre rapports, le contrat V3, la réussite de chaque garde-fou, les attributs demandés de politique et l'ordre pair04 candidate→baseline, pair05 baseline→candidate. Il refuse FAIL/BLOCKED, sorties manquantes, doublons, données invalides et contrats mélangés.

## Première exécution Windows, aucun modèle

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Summarize-CodexAB-TUI-Repeats.py
if ($LASTEXITCODE -ne 0) { throw 'Tests offline failed' }
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Summarize-CodexAB-TUI-Repeats.py --output-base 'C:\Dev\codex-ab-tui-mxc-v5-0165-v3' --start-pair 4 --pairs 2 --recheck
if ($LASTEXITCODE -ne 0) { throw 'Offline inspection failed' }
```

`--recheck` exécute uniquement les contrôles Python/Git indépendants des workspaces déjà présents puis compare leurs résultats aux rapports. Il ne prétend pas capturer les événements du TUI ou attester la sandbox effective. Sans `--recheck`, seuls les rapports enregistrés sont lus.

## Tokens facultatifs sans recopier quatre compteurs à la main

Quand l'opérateur dispose déjà d'une capture terminal **locale**, il peut ajouter `--terminal-log 'C:\chemin\vers\capture-locale.txt'`. L'outil accepte uniquement les lignes `BEGIN_INTERACTIVE_CANARY`, `Token usage` et `INDEPENDENT_CANARY_PASS` dans l'ordre attendu, extrait en mémoire les métriques numériques et vérifie `total = input + output`. **Aucun texte brut, session ID, mot de passe, prompt ou chemin privé n'est recopié dans le résultat ni persisté.** Une capture expurgée est préférable et ne doit pas être commitée.

En l'absence de capture, les métriques de tokens ne sont pas inventées (`null`) ; la synthèse des validations reste disponible. Les résultats utilisent `candidate_combined_token_delta_pct_descriptive_only` et `merge_authorized: false`, sans conclure à une économie de quota ou de facturation.

## Limites

- `worker_delegation_independently_verified=false` et `policy_effectiveness=not_runtime_attested` restent vrais : la preuve du TUI n'est pas capturée automatiquement.
- Une capture terminal fournie par l'opérateur n'a pas de provenance cryptographique : le rapprochement par paire/bras ne constitue pas une preuve d'authenticité.
- Les durées du lanceur comprennent le temps humain. Deux paires V3 ne démontrent pas un gain statistiquement reproductible ; ne pas fusionner la PR #14 sur cette base.
- La phase suivante devra étudier un flux d'événements natif **avec champs strictement autorisés**, sans collecte de messages privés, puis un benchmark avec tâches représentatives et nouveau contrat expérimental.

Historique : `docs/P1_1_V3_RESULTS_2026-10-29.md` ; les anciens essais V2/V3 et leurs preuves ne sont jamais modifiés par cet outil.
