# P1.1 — Contrat de harness app-server simulé (phase H0, sans modèle)

État : **phase de développement hors modèle**, nouvelle méthode distincte des canaries TUI V2/V3. Ne pas considérer ce document comme une autorisation d'exécution d'agents.

## Objectif

Le protocole app-server de Codex **0.165.0** possède des messages `initialize` / `initialized`, `thread/start`, `turn/start` ainsi que des notifications `item/started`, `item/completed`, `turn/completed`. Nous avons examiné les définitions **épinglées** au tag `rust-v0.165.0`, pas une version future non qualifiée. Le lanceur V3 utilisant un backend TUI intégré ne peut pas être observé rétroactivement depuis un second processus autonome.

Le nouveau script `scripts/Plan-CodexAB-AppServerHarness.py` construit des requêtes **proposées**, puis peut les exercer sur un **serveur fictif purement en mémoire**. Le simulateur vérifie la séquence initialize -> initialized -> thread/start -> turn/start, les refus de politique, les événements synthétiques du worker, la présence de la fin de tour et les écarts de config. Le résultat est un compteur anonymisé : jamais des prompts, des identifiants worker, un historique de sessions, des fichiers d'authentification ou un flux TUI réel.

## Plan A/B non autorisé : trois classes × deux répétitions × deux bras

Le plan contient **12 essais futurs théoriques** : chaque scénario `arith-control`, `device-reconcile` et `python-fallback-policy` est apparié baseline/candidate avec alternance d'ordre *au sein du même scénario*. Ce nombre définit seulement le plafond de la proposition, **pas un quota de modèles autorisé**. Aucun des douze essais n'est lancé ni approuvé par l'exécution de l'outil.

Le contrat est `p1.1-appserver-instrumented-harness-design-v1`, distinct des contrats TUI V2, V3 et du générateur de fixtures `p1.1-representative-fixtures-design-v1`. Les empreintes des profils, les tests de sécurité effectifs et les résultats de la campagne payante restent à établir.

## Exécution locale sûre, hors modèle

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B '.\scripts\Test-Plan-CodexAB-AppServerHarness.py'
if ($LASTEXITCODE -ne 0) { throw 'STOP: Harness synthetic tests failed' }
& 'C:\Dev\Python31314\python.exe' -B '.\scripts\Plan-CodexAB-AppServerHarness.py'
if ($LASTEXITCODE -ne 0) { throw 'STOP: Harness plan failed' }
& 'C:\Dev\Python31314\python.exe' -B '.\scripts\Plan-CodexAB-AppServerHarness.py' --simulate device-reconcile
if ($LASTEXITCODE -ne 0) { throw 'STOP: Harness mock simulation failed' }
```

Le script n'a **aucun** `--execute`, aucun accès réseau, aucune ouverture d'app-server, aucun subprocess Codex, aucune connexion à `CODEX_HOME` et aucune écriture. Un transport non simulé est refusé. La simulation ne confirme **pas** la parité des autorisations réelles, du sandbox MXC ou de l'orchestration ; les événements sont fabriqués exclusivement pour tester le contrat et l'instrumentation.

## Gate H1 (à développer, séparément)

1. Implémenter un client **app-server dédié et isolé**, démarré sur un profil jetable sous politique réseau maîtrisée. Ne jamais observer les anciennes sessions privées ni réutiliser les CODEX_HOME V2/V3.
2. Réaliser une connexion locale de préflight **sans `turn/start`**, puis recueillir les réponses de policy dans un schéma allowlist. Aucune information brute d'identité, de chemin personnel, de secret ou de conversation ne peut figurer dans les preuves archivées.
3. Démontrer le contrôle Windows MXC **effectif** par des essais négatifs sur environnement jetable, pas uniquement par l'écho JSON `sandbox: workspaceWrite`; vérifier aussi l'absence de demandes UAC/approbation. Si la parité n'est pas démontrée : STOP.
4. Ajouter des contrôles indépendants des fixtures et une preuve worker issue du transport **du même serveur**, pas d'un export non attesté ou d'un second serveur.
5. Présenter un plan verrouillé (version Codex, modèle/effort, profils, prompts, budgets, ordre, essais, stop) et demander une **autorisation distincte** avant le premier véritable appel IA.

## Sources de schéma

- [ClientNotification.ts (`initialized`)](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/ClientNotification.ts)
- [InitializeParams.ts](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/InitializeParams.ts)
- [ThreadStartParams.ts](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartParams.ts)
- [ThreadStartResponse.ts](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartResponse.ts)
- [TurnStartParams.ts](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/TurnStartParams.ts)
- [ThreadItem.ts](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadItem.ts)

Suivi : issue #61, issue #34 ; PR #14 conservée **OPEN, non fusionnée**. Aucun nouveau modèle n'est autorisé par cette phase.
