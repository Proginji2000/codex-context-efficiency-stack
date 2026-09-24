# Stack d’optimisation de contexte Codex (Windows)

Configuration pratique pour réduire le contexte inutile dans Codex, éviter les escalades de modèle superflues et garder la vérification déterministe.

Le dépôt contient désormais deux couches complémentaires :

1. **Efficacité de contexte** — RTK, `AGENTS.md` concis, `tool_output_token_limit`, Code Review Graph (CRG), lectures ciblées et sorties bornées.
2. **Routing de modèles v2** — workers GPT-6 Luna par défaut, rôles explicites Luna Low/Medium/High, puis GPT-6 Sol High uniquement lorsque la difficulté ou les preuves d’échec le justifient.

## Architecture

```text
DEMANDE
   |
   v
THREAD CODEX PRINCIPAL
   |
   +-- contexte borné / RTK / CRG / skills
   |
   +-- luna-low      petites modifications mécaniques
   +-- luna-medium   travail de développement normal
   +-- luna-high     raisonnement complexe mais borné
   `-- sol-high      architecture / sécurité / migration / échecs répétés
           |
           v
      IMPLEMENTATION
           |
           v
 VERIFICATION DETERMINISTE
 tests / build / lint / types / diff
           |
     +-----+-----+
     |           |
    PASS        FAIL
     |           |
 TERMINE     retry / escalade
```

Règle centrale :

> **Si un logiciel peut prouver le résultat, exécutez ce logiciel. N’utilisez le jugement d’un modèle que pour ce qui reste incertain.**

Le compilateur détermine si le code compile. Le runner de tests détermine si les tests passent. `git diff` établit ce qui a changé. Le modèle sert à choisir l’implémentation, interpréter les échecs et gérer l’ambiguïté.

---

## Installation rapide

### 1. Sauvegarder Codex

Sous Windows, le dossier par défaut est :

```text
%USERPROFILE%\.codex
```

Avant modification :

```powershell
$CodexHome = Join-Path $env:USERPROFILE '.codex'
Copy-Item "$CodexHome\config.toml" "$CodexHome\config.toml.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\AGENTS.md" "$CodexHome\AGENTS.md.backup" -ErrorAction SilentlyContinue
Copy-Item "$CodexHome\hooks.json" "$CodexHome\hooks.json.backup" -ErrorAction SilentlyContinue
```

### 2. Limiter les sorties d’outils conservées

Dans `~/.codex/config.toml` :

```toml
tool_output_token_limit = 4000
```

### 3. Installer le `AGENTS.md` global

Utilisez [`templates/AGENTS.md`](templates/AGENTS.md) comme base de `~/.codex/AGENTS.md`.

Il impose notamment :

- recherche avant lecture massive
- sorties terminal concises
- tests ciblés pendant l’itération
- validation déterministe avant de conclure
- diffs ciblés
- pas de relecture inutile
- contexte borné pour les sous-agents
- escalade Luna -> Sol basée sur les preuves
- CRG en premier lorsqu’un graphe apporte réellement quelque chose

Gardez les conventions spécifiques aux projets dans les `AGENTS.md` des dépôts ou dans des skills, au lieu de faire grossir indéfiniment le fichier global.

### 4. Ajouter le routing Luna/Sol v2

Le dépôt fournit quatre profils :

```text
templates/agents/luna-low.toml
templates/agents/luna-medium.toml
templates/agents/luna-high.toml
templates/agents/sol-high.toml
```

Copiez-les dans :

```text
~/.codex/agents/
```

Puis fusionnez :

```text
templates/config.routing.snippet.toml
```

dans :

```text
~/.codex/config.toml
```

Configuration recommandée :

```text
worker par défaut       -> GPT-6 Luna / medium
petite tâche            -> Luna / low
tâche complexe bornée   -> Luna / high
architecture / sécurité /
migration / échecs      -> Sol / high
```

Redémarrez Codex après modification.

Guide complet : [`docs/MODEL_ROUTING_V2.md`](docs/MODEL_ROUTING_V2.md).

### Limite importante

`AGENTS.md` peut indiquer **quand** utiliser un rôle, mais il ne transforme pas magiquement le modèle du tour principal déjà en cours.

Les rôles fournis permettent à Codex de créer des sous-agents avec un vrai modèle et un vrai niveau de raisonnement configurés. Si les rôles ne sont pas disponibles dans le runtime courant, Codex doit continuer avec le modèle actif et ne jamais prétendre qu’un changement de modèle a eu lieu.

Un routeur externe capable de modifier dynamiquement le modèle du thread principal est une couche d’orchestration distincte, par exemple via l’Agents API.

---

## Politique de routing

Utilisez le niveau le moins coûteux qui reste clairement suffisant.

| Travail | Lane |
| --- | --- |
| doc, typo, rename évident, petite config | Luna Low |
| feature normale, tests, bug localisé, SQL ordinaire | Luna Medium |
| debug complexe, logique d’état subtile, gros refactor borné | Luna High |
| architecture, auth/sécurité, migration risquée, échecs Luna répétés | Sol High |

Ne créez pas un sous-agent ou un appel de décision après chaque lecture ou commande.

Séquence d’escalade pratique :

```text
Luna Medium
 -> vérification
 -> échec localisé : deuxième tentative
 -> vérification
 -> encore difficile : Luna High
 -> vérification
 -> non résolu / risque élevé : Sol High
```

Jev ou un autre modèle de décision reste **optionnel**. Une sortie typée ou un score de confiance n’est pas une preuve de correction.

---

## RTK

RTK compresse les sorties de commandes courantes avant qu’elles n’occupent le contexte du modèle.

Après installation :

```powershell
rtk init -g --codex
rtk --version
rtk gain
```

Sur Windows natif, ne supposez pas que toutes les commandes sont réécrites automatiquement. Le comportement dépend des instructions Codex et des commandes réellement compatibles.

---

## Code Review Graph

Installation :

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform codex
```

Pour chaque dépôt :

```powershell
cd C:\chemin\du\repo
code-review-graph build
code-review-graph status
code-review-graph register C:\chemin\du\repo --alias mon-repo
```

Ensuite, préférez :

```powershell
code-review-graph update
```

CRG sert à réduire le périmètre à lire, pas à remplacer le code source. Si le graphe et le code divergent, le code source gagne.

Les problèmes PATH et hooks Windows sont documentés dans [`docs/WINDOWS_TROUBLESHOOTING.md`](docs/WINDOWS_TROUBLESHOOTING.md).

---

## Progressive disclosure

Évitez un `AGENTS.md` énorme contenant toute la documentation du projet.

Préférez :

```text
AGENTS.md
  -> règles courtes
  -> conditions indiquant quand consulter quoi

.agents/skills/
  -> workflows détaillés
  -> scripts
  -> références
```

Exemple :

```text
Consulter architecture.md pour les changements de frontières de services.
Consulter database.md pour les changements de schéma ou migrations.
Consulter deployment.md uniquement lors d’une préparation de déploiement.
```

Une correction de typo ne doit pas payer le coût de contexte de toute l’architecture du projet.

---

## Gate de fin

Une tâche peut être déclarée terminée lorsque les vérifications applicables sont satisfaites :

```text
comportement demandé implémenté
+ tests pertinents OK
+ build/types/lint OK lorsque nécessaire
+ diff final conforme au périmètre
+ aucun échec connu masqué
= terminé
```

Ne lancez pas une validation démesurée pour une modification triviale si le dépôt ne l’exige pas. À l’inverse, ne sautez pas une validation obligatoire simplement pour économiser du quota.

---

## Git et CRG

Un `.gitignore` propre réduit fortement le bruit visible par CRG et par les agents.

Exemples fréquents :

```gitignore
__pycache__/
*.py[cod]
.pytest_cache/
.venv/
node_modules/
.code-review-graph/
logs/
*.log
build/
dist/
coverage/
.cache/
.env
.env.*
!.env.example
*.secret
*.pem
```

Adaptez la liste au dépôt ; ne masquez pas des fixtures ou données de test suivies volontairement.

---

## Sessions Codex déjà ouvertes

Après modification des instructions globales, vous pouvez envoyer une fois dans une ancienne session :

```text
Relis maintenant les instructions globales Codex présentes dans ~/.codex/AGENTS.md ainsi que le RTK.md qu'elles référencent. Applique immédiatement leur version actuelle à cette session et à toutes les étapes suivantes.
```

Les nouveaux MCP ou rôles multi-agents peuvent nécessiter un redémarrage de Codex ou un nouveau runtime.

---

## Mesurer

```powershell
rtk gain
code-review-graph status
code-review-graph detect-changes --brief
```

Pour le routing, suivez surtout :

- nombre de tâches par lane
- réussite par lane
- retries
- escalades
- vérifications échouées
- consommation de contexte/quota lorsque visible
- latence réelle

La métrique utile est le **travail logiciel correctement terminé par unité de quota/coût**, pas le nombre brut de tokens.

---

## Stack recommandé

```text
thread Codex principal
        +
workers GPT-6 Luna par défaut
        +
Luna Low / Medium / High
        +
Sol High uniquement sur vraie condition d’escalade
        +
RTK
        +
AGENTS.md concis
        +
skills / progressive disclosure
        +
tool_output_token_limit = 4000
        +
Code Review Graph lorsque pertinent
        +
Git propre
        +
tests/build/lint/types/diff déterministes
```

Puis arrêtez d’ajouter des couches tant qu’une mesure réelle ne montre pas un nouveau goulot d’étranglement.

Les sources et recommandations de sécurité sont dans [`SOURCES.md`](SOURCES.md) et [`SECURITY.md`](SECURITY.md).
