# Stack d’efficacité de contexte Codex (Windows)

Stack pratique pour réduire le contexte inutile, économiser le quota Codex et garder une vérification déterministe.

> Mise à jour du 27 octobre 2026 : **GPT‑6.1 Terra** devient un palier intermédiaire entre Luna et Sol. Luna reste le défaut endurance ; Sol/Astra restent les escalades complexes.

## Architecture recommandée

```text
DEMANDE
   |
   v
THREAD CODEX PRINCIPAL (Luna orchestrateur uniquement)
   |
   +-- RTK / CRG / skills / contexte borné
   |
   +-- luna-low       petites modifications mécaniques
   +-- luna-medium    développement normal
   +-- luna-high      raisonnement borné, priorité économie
   +-- terra-medium    correctifs bornés / UI / computer-use
   +-- terra-high      implémentation/debug difficile mais borné
   +-- sol-high       GPT-6.1 Sol / high
   +-- sol-xhigh      GPT-6.1 Sol / xhigh
   `-- astra-high     ultime escalade
           |
           v
 VERIFICATION DETERMINISTE
 tests / build / lint / types / diff
```

Règle centrale :

> **Si un logiciel peut prouver le résultat, exécutez ce logiciel. Utilisez le jugement d’un modèle uniquement pour ce qui reste incertain.**

## Pourquoi GPT‑6.1 Sol

OpenAI annonce GPT‑6.1 Sol comme une amélioration majeure de GPT‑6 Sol pour le coding agentique. Le tarif API standard reste à **$2/M input et $10/M output**, tandis que le cached input passe de **$0,20/M à $0,10/M**. OpenAI indique aussi +6,4 points sur DeepSWE v1.1 face au meilleur score de GPT‑6 Sol, à effort/coût inférieurs.

Le coût API n’est pas une mesure directe du quota Plus/Pro. Pour cette raison, le dépôt conserve `sol6-legacy-high` afin de faire des A/B réels sur quota, latence, retries et réussite.

## Routing

| Travail | Lane |
| --- | --- |
| doc, typo, rename évident, petite config | `luna-low` |
| feature normale, tests, bug localisé, SQL ordinaire | `luna-medium` |
| raisonnement borné où Luna reste suffisant | `luna-high` |
| correctif code borné, UI, visual/computer-use | `terra-medium` |
| implémentation/debug difficile mais borné | `terra-high` |
| code complexe, architecture, sécurité, migration risquée | `sol-high` |
| Sol High insuffisant mais problème toujours borné | `sol-xhigh` |
| difficulté end-to-end exceptionnelle | `astra-high` |
| benchmark/fallback GPT‑6 Sol | `sol6-legacy-high` |

Séquence recommandée :

```text
Luna Medium
 -> vérification
 -> retry localisé
 -> Luna High ou Terra Medium selon la tâche
 -> Terra High si toujours borné
 -> GPT-6.1 Sol High
 -> vérification
 -> GPT-6.1 Sol XHigh
 -> vérification
 -> Astra High seulement si nécessaire
```

## Documentation et outils complémentaires

Voir l'[index documentaire](docs/README.md) et le [guide des intégrations facultatives](docs/OPTIONAL_INTEGRATIONS.md).

- **GitHub Spec Kit** : spécifications, planification et découpage en tâches pour les nouveaux projets ou fonctionnalités structurées ; activation **par projet**, non globale.
- **Anthropic frontend-design** : skill Apache 2.0 inclus dans `.agents/skills/frontend-design/`. Pour tous les projets Codex de l'utilisateur, exécuter explicitement `.\scripts\install-frontend-design.ps1`.
- **Shannon** : pentest actif uniquement sur environnement de test autorisé et isolé ; aucun lancement automatique.
- **HatchZip** : utilitaire séparé pour extraire avec peu d'espace disque ; consomme progressivement l'archive originale, donc usage manuel.

Ces outils ne remplacent ni RTK, ni Code Review Graph, ni les vérifications déterministes. L'installateur global ne les active pas silencieusement.

## Déclenchement automatique des skills UI

L'orchestrateur Luna confie automatiquement les demandes visuelles (dashboard, site, composants, style, responsive) à `ui-implementer` sur **GPT-6.1 Terra Medium**. Ce worker charge le skill `frontend-design` s'il est installé, même lorsque le prompt ne cite pas le skill.

Sur le PC principal, après `git pull` et l'installation du stack, installer une seule fois le skill globalement :

```powershell
.\scripts\install-frontend-design.ps1
```

Aucune dépendance Node.js, Python, uv, Docker ou API payante n'est nécessaire pour frontend-design. L'installation ne prouve pas l'usage réel : vérifier le rôle et le skill dans le rapport du sous-agent. [Détails et limites](docs/OPTIONAL_INTEGRATIONS.md).

## Gestion des sous-agents et limites de threads

Luna reste orchestrateur, mais gere maintenant explicitement le cycle de vie des workers : inspection avant nouvelle vague, reutilisation d'un agent compatible, collecte des preuves, fermeture **uniquement si `close_agent` existe** (V1) et recuperation bornee lorsque `agent thread limit reached` apparait. En V2, les workers termines sont normalement evinces par le runtime; `interrupt_agent` ne libere pas un emplacement.

Ce protocole **ne modifie pas la limite des threads**, ne tente pas de tuer des processus, et ne permet jamais a Luna de remplacer un worker bloque. En cas de saturation persistante, une reprise dans une nouvelle conversation avec un checkpoint est privilegiee.

Controle statique, sans lancer de workers :

```powershell
.\scripts\Test-SubagentLifecyclePolicy.ps1
```

Ce test confirme la presence des regles, pas le fonctionnement interne de Codex. Voir [routage et reprise sur saturation](docs/MODEL_ROUTING_V4.md#subagent-lifecycle-version-aware-operational-policy).

## Reprise automatique, navigation et sécurité

Quatre extensions sont prévues pour les sous-agents :

- **Reprise du projet :** au premier travail de reprise, Luna délègue un diagnostic Git/état existant à un worker Luna en lecture seule ; le worker réconcilie les worktrees, PR, tests, `STATE.md` et `PLANS.md` avant toute modification. Un script compact `scripts/Get-ProjectResume.ps1` est fourni.
- **Playwright MCP :** sur une interface web possédée ou de test, le worker `ui-implementer` peut réaliser les contrôles navigateur (interactions, responsive, accessibilité) avec une session isolée.
- **Context7 MCP :** consultation ciblée de documentation **publique** versionnée par les workers, seulement lorsqu'une API externe le justifie.
- **Gitleaks :** contrôle local des secrets, avec sortie masquée, avant publication d'une PR significative et après changement sensible. `scripts/Test-SecretGate.ps1` est fourni.

Les extensions Playwright/Context7/Gitleaks requièrent une **installation facultative sur chaque PC** ; elles ne sont pas activées par `git pull`. **Shannon reste en pause** (accès cyber non autorisé), sans intégration automatique.

Voir les [commandes Windows et tests d'acceptation](docs/DEVELOPER_EXTENSIONS.md). Installation facultative en une commande après `git pull` :

```powershell
.\scripts\Install-DevExtensions.ps1 -WhatIf
.\scripts\Install-DevExtensions.ps1
```

 Une règle `AGENTS.md` guide les sous-agents mais ne prouve pas que les MCP seront utilisés.

## Vérification de syntaxe PowerShell

Avant d'exécuter le vérificateur, analyser en lecture seule **tous** les scripts PowerShell du stack avec le parseur Windows PowerShell 5.1 :

```powershell
.\scripts\Test-PowerShellSyntax.ps1
.\scripts\verify-stack.ps1
```

Ce contrôle a été ajouté après une erreur de génération dans `verify-stack.ps1` sur la PR #10 ; il prévient les mêmes erreurs de syntaxe à l'avenir, mais ne remplace pas les tests fonctionnels. Sous **Windows PowerShell 5.1**, les scripts UTF-8 sans BOM contenant des caractères non ASCII peuvent être lus comme du texte ANSI et provoquer des erreurs de guillemets. Le contrôle rejette désormais ces encodages non sûrs ; une CI Windows PowerShell 5.1 applique la même vérification sur les PR.

## Mise à jour globale Windows

Après `git pull` :

```powershell
cd C:\Dev\codex-context-efficiency-stack
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\update-codex-global.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify-stack.ps1
```

Le script :

- sauvegarde les fichiers globaux modifiés sous `~/.codex/backups/` ;
- met à jour `~/.codex/AGENTS.md` ;
- installe les rôles Luna / GPT‑6.1 Terra / GPT‑6.1 Sol / Astra ;
- ajoute `sol-xhigh` et la lane legacy si besoin ;
- rafraîchit le profil opt-in `context-efficiency` ;
- **ne modifie pas les `.codex/config.toml` des projets**.

Redémarrez Codex ensuite pour charger les nouveaux rôles.

## Héritage projet

Les instructions globales `~/.codex/AGENTS.md` s’appliquent aux projets. Un `AGENTS.md` de dépôt ajoute des règles spécifiques. En revanche, un `.codex/config.toml` local peut surcharger le routing global.

Audit rapide depuis un projet :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Dev\codex-context-efficiency-stack\scripts\audit-project-inheritance.ps1
```

C’est la commande à utiliser avant de migrer un projet à routing spécifique comme CryptoLab.

## RTK et Code Review Graph

RTK réduit les sorties terminal conservées dans le contexte :

```powershell
rtk init -g --codex
rtk gain
```

CRG sert à réduire le périmètre à lire avant les lectures larges :

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform codex
code-review-graph build
```

Le code source et les tests restent toujours autoritaires si le graphe est incomplet ou obsolète.

## Nouveautés DevDay intégrées ou suivies

- **GPT‑6.1 Sol** : intégré maintenant dans le routing.
- **`/agents`** : utile pour suivre les sous-agents, aucune config spéciale requise.
- **Environnements cloud réutilisables** : complémentaires, pas nécessaires au stack Windows local.
- **Code Review / Security Cloud** : complémentaires, pas de duplication systématique des reviews locales.
- **Decisions API** : intéressante pour un futur routeur borné, mais pas dépendance du stack tant que la disponibilité/évaluation n’est pas suffisante.
- **GPT‑6.1 Sol Ultrafast** : non utilisé par défaut ; objectif vitesse, pas endurance quota.

Voir [`docs/DEVDAY_2026_UPDATE.md`](docs/DEVDAY_2026_UPDATE.md) et [`docs/MODEL_ROUTING_V4.md`](docs/MODEL_ROUTING_V4.md).

## Raccourcis Codex 0.164 et mesure opt-in

Codex CLI 0.164.0 prend en charge dix emplacements `/presets` pour les prompts et commandes courants. Six modeles de presets sont documentes pour la reprise de projet, le statut, les tests, les PR, les UI et les comparaisons A/B dans [le guide 0.164](docs/CODEX_0164_PRESETS.md). **Aucun emplacement n'est installe ou ecrase automatiquement** : leur creation se fait par le menu CLI `/presets`, si disponible. La disponibilite du menu dans Codex Desktop n'est pas etablie.

Un [rapport de metriques](docs/MEASUREMENT.md#optional-csv-metrics-aggregation-codex-cli-0164) permet de consolider des taches anonymisees sans lire les conversations ni inventer des chiffres de quota :

```powershell
.\scripts\Test-CodexRunMetrics.ps1
.\scripts\Get-CodexRunMetrics.ps1 -InputPath C:\Path\To\codex-runs.csv
```

Ce suivi est opt-in et base sur des observations declarees ; ce n'est **pas** une telemetrie automatique.

## Collecte des tokens CLI sans historiques prives

Le filtre opt-in `scripts/Convert-CodexExecUsage.ps1` prend uniquement les evenements JSONL d'une **nouvelle** execution `codex exec --json`, puis renvoie des compteurs de tokens agreges. Il ne lit ni anciennes conversations ni donnees Codex Desktop. Aucun export automatique ni acces aux fichiers de sessions : voir [le guide et ses limites](docs/CODEX_EXEC_USAGE.md).

Test local sans lancer Codex :

```powershell
.\scripts\Test-CodexExecUsage.ps1
```

## Diagnostic local du contexte sans quota

Le test du 27 octobre a affiche **108 273 tokens d'entree, dont 80 384 en cache**. Ce total ne peut pas etre attribue au seul AGENTS.md. Notre [audit statique du contexte](docs/CODEX_STATIC_CONTEXT_AUDIT.md) explique les limites des chiffres et inclut une commande sans lancement de Codex :

```powershell
.\scripts\Test-CodexContextFootprint.ps1
.\scripts\Get-CodexContextFootprint.ps1 -ProjectDirectory C:\Dev\codex-context-efficiency-stack -AsJson
```

Le script ne divulgue aucun contenu de config, nom de serveur MCP, secret ou historique de conversation. L'optimisation AGENTS.md de la PR #14 reste experimentale et non installee.

## Audit securise des 9 configurations MCP

L'inventaire du 27 octobre a compte **9 serveurs MCP declares**, sans prouver qu'ils soient demarres, accessibles ou exposes au modele. Le [diagnostic des politiques MCP](docs/CODEX_MCP_AUDIT.md) examine les indicateurs d'activation, types de transport, allowlists et denylists sans lancer Codex, ni imprimer identifiants ou secrets.

```powershell
python .\\scripts\\Test-CodexMcpPolicyAudit.py
python .\\scripts\\Get-CodexMcpPolicyAudit.py
```

Python >= 3.11 suffit (3.13 est deja installe). Aucune commande n'edite `config.toml`; l'audit ne prouve pas les economies de tokens. L'optimisation du contexte global en PR #14 reste independante.

## Profils MCP par tache (facultatifs)

Quatre MCP sont declares sur le PC : code-review-graph, context7, node_repl et playwright. Le lanceur [a apercu sans quota](docs/CODEX_MCP_SCOPES.md) permet de les limiter par appel CLI en conservant intacte la configuration globale :

```powershell
.\scripts\Test-CodexScopedMcp.ps1
.\scripts\Invoke-CodexScopedMcp.ps1 -Scope git -AsJson
```

Seul l'ajout explicite de `-Run -Prompt "..."` lance Codex et consomme du quota. Par defaut, le mode `git` desactive les quatre MCP **pour cet appel uniquement**, tandis que le mode `ui` les conserve. Aucune economie de tokens n'est encore prouvee.

## Vérification et mesure

```powershell
.\scripts\verify-stack.ps1
rtk gain
code-review-graph status
```

Mesurez surtout : tâches terminées par lane, retries, escalades, échecs de validation, latence et consommation de quota visible. La métrique utile reste le **travail logiciel correctement terminé par unité de quota/coût**.

## Stack recommandé

```text
Codex principal
+ Luna Low / Medium / High
+ GPT-6.1 Terra Medium / High
+ GPT-6.1 Sol High / XHigh
+ Astra High en dernier recours
+ GPT-6 Sol legacy uniquement pour A/B
+ RTK
+ AGENTS.md concis
+ skills / progressive disclosure
+ tool_output_token_limit = 4000
+ Code Review Graph quand pertinent
+ tests/build/lint/types/diff déterministes
```

Le dépôt contient aussi une couche Claude Pro séparée documentée dans [`CLAUDE_PRO.md`](CLAUDE_PRO.md). Le futur dual-stack sera traité séparément afin de ne pas mélanger son scheduler avec le cœur Codex.

### Correction du comptage MCP

Le rapport TOML a confirme **4 serveurs MCP declares et actives** (tous `stdio`), au lieu des 9 en-tetes comptes precedemment. Les sous-sections `[mcp_servers.nom.env]` ne sont pas des serveurs supplementaires. `Get-CodexContextFootprint.ps1` distingue desormais les serveurs et les en-tetes, avec test de regression. Le Python TOML fait autorite sur la structure.
