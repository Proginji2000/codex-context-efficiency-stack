# Stack d’efficacité de contexte Codex (Windows)

Stack pratique pour réduire le contexte inutile, économiser le quota Codex et garder une vérification déterministe.

> Mise à jour DevDay du 29 septembre 2026 : le chemin d’escalade normal utilise désormais **GPT‑6.1 Sol**, avec **Sol High → Sol XHigh → Astra High**. GPT‑6 Sol reste uniquement comme lane legacy de benchmark/fallback.

## Architecture recommandée

```text
DEMANDE
   |
   v
THREAD CODEX PRINCIPAL
   |
   +-- RTK / CRG / skills / contexte borné
   |
   +-- luna-low       petites modifications mécaniques
   +-- luna-medium    développement normal
   +-- luna-high      debug/refactor complexe mais borné
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
| debug complexe, état subtil, gros refactor borné | `luna-high` |
| architecture, sécurité, migration risquée, échecs Luna | `sol-high` |
| Sol High insuffisant mais problème toujours borné | `sol-xhigh` |
| difficulté end-to-end exceptionnelle | `astra-high` |
| benchmark/fallback GPT‑6 Sol | `sol6-legacy-high` |

Séquence recommandée :

```text
Luna Medium
 -> vérification
 -> retry localisé
 -> Luna High
 -> vérification
 -> GPT-6.1 Sol High
 -> vérification
 -> GPT-6.1 Sol XHigh
 -> vérification
 -> Astra High seulement si nécessaire
```

## Mise à jour globale Windows

Après `git pull` :

```powershell
cd C:\Dev\codex-context-efficiency-stack
pwsh -ExecutionPolicy Bypass -File .\scripts\update-codex-global-devday-2026.ps1
pwsh -ExecutionPolicy Bypass -File .\scripts\verify-stack.ps1
```

Le script :

- sauvegarde les fichiers globaux modifiés sous `~/.codex/backups/` ;
- met à jour `~/.codex/AGENTS.md` ;
- installe les rôles Luna / GPT‑6.1 Sol / Astra ;
- ajoute `sol-xhigh` et la lane legacy si besoin ;
- rafraîchit le profil opt-in `context-efficiency` ;
- **ne modifie pas les `.codex/config.toml` des projets**.

Redémarrez Codex ensuite pour charger les nouveaux rôles.

## Héritage projet

Les instructions globales `~/.codex/AGENTS.md` s’appliquent aux projets. Un `AGENTS.md` de dépôt ajoute des règles spécifiques. En revanche, un `.codex/config.toml` local peut surcharger le routing global.

Audit rapide depuis un projet :

```powershell
pwsh -ExecutionPolicy Bypass -File C:\Dev\codex-context-efficiency-stack\scripts\audit-project-inheritance.ps1
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

Voir [`docs/DEVDAY_2026_UPDATE.md`](docs/DEVDAY_2026_UPDATE.md) et [`docs/MODEL_ROUTING_V2.md`](docs/MODEL_ROUTING_V2.md).

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
