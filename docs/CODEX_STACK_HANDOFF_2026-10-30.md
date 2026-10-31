# Passation — Codex Stack IA & Autonomie — 30 octobre 2026

> **Mise à jour :** la qualification Supermemory a avancé le **31 octobre 2026** (adaptateur local commit `e4fd34e`, sauvegarde à froid, restauration binaire validée, restauration applicative encore bloquée sur les droits possibles du clone). **Pour toute nouvelle reprise, lire d’abord [la passation opérationnelle du 31/10](CODEX_STACK_HANDOFF_2026-10-31.md)**. Cette page du 30/10 reste un historique et ses statuts ne sont pas actualisés rétroactivement.

**Document de reprise après les tests Serena, shadcn et Supermemory Local.** Preuves : sorties Windows PowerShell/TUI communiquées par l'opérateur et état du dépôt GitHub. L'assistant n'a pas inspecté la machine directement. Ancien main : `55fdaa75cfbebfefa850e88c8f739f1d2fd0ce2a` avant la présente documentation ; ne pas figer ce SHA après fusion.

## Priorité du projet

Construire une stack Codex réellement utilisable avec parent Luna orchestrateur uniquement, workers spécialisés, outils MCP/skills, mémoire/contexte, auto-correction légitime et vérifications build/tests/Git. **Prochaine étape : connecter Supermemory Local à Codex de façon opt-in, sans écraser les hooks existants ni capturer toutes les sessions.** Une VM isolée est un objectif éventuel de déploiement, pas le travail prioritaire. Éviter de reprendre les campagnes de canaries sans dépendance fonctionnelle.

## Supermemory Local : validation réelle rapportée du 30/10/2026

| Contrôle | Résultat | Limites |
| --- | --- | --- |
| Docker | Docker Desktop, contexte `desktop-linux`, moteur Linux PASS, Compose `v5.6.1` | Disponible au moment des tests |
| Ollama | Windows `0.40.13` ; `qwen3:8b` (5,2 Go) téléchargé ; `OLLAMA_QWEN3_READY_PASS` | GPU non vérifié |
| Docker vers Ollama | `DOCKER_OLLAMA_QWEN3_PASS`, URL `host.docker.internal:11434/v1/models` | Connexion et modèle visible, pas trace d'inférence |
| Compose release | `server-v0.0.9` ; SHA-256 `1163d88387cc7b2046db53f6f6418a50a03eaef5c105270507f2d446afc941ea` ; configuration PASS | Contrôle de l'opérateur |
| Docker Supermemory | Image `docker.io/supermemory/supermemory:0.0.9`, conteneur `supermemory-supermemory-1` Healthy, `SUPERMEMORY_HEALTH_PASS` | API health seule insuffisante pour attester l'indexation |
| API authentifiée | `SUPERMEMORY_AUTH_PASS`, lecture `GET /v3/projects` | Clé locale utilisée en mémoire uniquement |
| Mémoire fictive | `MEMORY_WRITE_ACCEPTED_PASS`, `POST /ns/codex_smoke_20261030/document`, `dreaming=instant` | Une seule écriture |
| Recherche | `SEMANTIC_MEMORY_RECALL_PASS` via `POST /ns/codex_smoke_20261030/search` ; marqueur fictif `HIBOU-7319` retrouvé **au second essai** | Validation de ce seul flux |
| Hooks Codex | Inchangés | **Aucune capture ou intégration Codex-Supermemory active** |

**Conserver cette installation.** Dossier `C:\Dev\supermemory-local` : `compose.yaml`, `compose.override.yaml` et `.env` ; volume persistant `supermemory_supermemory-data` ; réseau `supermemory_default` ; API bind seulement `127.0.0.1:6767`. Clé API générée stockée dans `/data/api-key` à l'intérieur du conteneur/volume. **Ne jamais publier la clé, les fichiers .env, des logs bruts ou des configurations contenant des secrets.** Ne pas lancer `docker compose down -v`, supprimer un volume, réinstaller dans ce dossier ni effacer le namespace de test sans sauvegarde et décision.

Le Compose override **déclare** `OPENAI_BASE_URL=http://host.docker.internal:11434/v1` ; `OPENAI_MODEL`, `OPENAI_FAST_MODEL`, `OPENAI_TEXT_MODEL=qwen3:8b` ; embeddings `SUPERMEMORY_EMBEDDING_PROVIDER=local`, `SUPERMEMORY_EMBEDDING_MODEL=Xenova/bge-m3`, `SUPERMEMORY_EMBEDDING_DIMENSIONS=1024` ; télémétrie et update check demandés désactivés. **L'utilisation effective du modèle d'embeddings et du fournisseur LLM pour l'ensemble des opérations, l'absence de trafic cloud et la désactivation effective de télémétrie ne sont pas attestées indépendamment.** Aucune sauvegarde/restauration du volume n'est encore prouvée.

## Codex, Serena, shadcn et routage — acquis

- Codex global : `0.164.0` ; notification `0.166.0` observée, pas de mise à jour. Codex pilote `0.165.0` isolé en `C:\Dev\codex-cli-0165\node_modules\.bin\codex.cmd` ; Python `C:\Dev\Python31314\python.exe`. Node/npm/npx/uv/Docker/WSL disponibles ; Bun absent lors du dernier contrôle.
- `~\.codex\config.toml` : MCP **Serena** et **shadcn** enregistrés, tous deux `enabled=false` par défaut, avec sauvegardes. PR **#91 fusionnée** : `scripts/Invoke-CodexScopedMcp.ps1` accepte `-EnableSerena` (scopes code/ui), `-EnableShadcn` (scope ui) et `-Interactive` ; c'est un opt-in **au lancement de la session**, pas une activation automatique pendant un tour.
- Serena `2.1.0` installé/initialisé, backend LSP, 3 tools connectés ; analyse sémantique réelle de `total()` et `average()`. Mémoire `validation_serena_20261029` écrite et relue, fichier `.serena/memories/validation_serena_20261029.md` trouvé sur disque, puis relecture dans une **nouvelle session Codex** sous le même projet temporaire. **Pas de preuve de capture automatique interprojets.**
- shadcn/ui MCP : 7 tools connectés, recherches/consultations réelles `search_items_in_registries` et `view_items_in_registries` pour Button, Card, Dialog, sans installation des composants. Pas de validation d'un produit UI complet.
- PR **#92 fusionnée** : règles conditionnelles Serena/shadcn pour parent AGENTS et worker `ui-implementer`. Opérateur a fait le `git pull` local au commit `55fdaa7`, copié le worker avec backup et ajouté exactement deux lignes au `~\.codex\AGENTS.md` avec backup : `UI_WORKER_UPDATED_PASS` et `AGENT_ROUTING_UPDATED_PASS`. Ne pas écraser ou réappliquer aveuglément ces fichiers.
- Skill `frontend-design` présent ; 10 agents recensés au moment de l'inventaire. Quatre MCP stdio précédents : `code-review-graph`, `context7`, `node_repl`, `playwright` ; `oracle_reflex` rapporté failed dans `/mcp`. `codex_apps` listait 258 outils, ce qui ne prouve pas leur coût réel en tokens par tour.
- **Hooks Codex existants** : `~\.codex\hooks.json`, JSON valide, `SessionStart: 1` et `PostToolUse: 1`. Le contenu et l'effet de ces hooks ne sont pas encore audités. **Ne pas lancer d'installateur Supermemory qui les écrase ; sauvegarder et vérifier un mécanisme de fusion/rollback.**

## P1.1 — historique distinct à préserver

- **PR #14 ouverte, non fusionnée** : optimisation AGENTS expérimentale, bénéfice quota non démontré.
- Contrat V2 : paire 01 baseline/candidate PASS, 13 548 / 12 440 tokens déclarés ; paire 02 candidate PASS 27 395, baseline **BLOCKED/FAIL** 17 645 à cause du fallback PowerShell ; paire 03 jamais démarrée. Ne pas transformer ces échecs historiques en PASS.
- Contrat V3 `p1.1-git-diff-psfallback-v3` avec Codex isolé 0.165.0 : p04 candidate→baseline et p05 baseline→candidate, 4/4 PASS fonctionnels (tests, diff, seul total.py changé). Totaux déclarés : p04 candidate 26 090 / baseline 37 957 ; p05 candidate 23 906 / baseline 15 344. Écart inversé d'une paire à l'autre ; cumul descriptif −6,20 % pour la candidate, **non statistiquement fiable et pas équivalent à une consommation de quota**. Délégation vue dans TUI, non attestée indépendamment par le wrapper.
- MXC : tests standalone filesystem négatif et Job Object contrôlé passés ; ne prouvent ni l'ensemble des permissions app-server ni l'isolation réseau ni le nettoyage automatique de tous les enfants.
- Références : `docs/P1_1_V3_RESULTS_2026-10-29.md`, `docs/P1_1_HANDOFF_2026-10-29.md` (instantané historique, ne pas altérer), issue #34. **Ne pas fusionner PR #14 sans accord et qualification spécifique.**

## Ordre de reprise du prochain chat

1. Lire ce document et `docs/QUALIFICATION_ROADMAP_2026.md` ; contrôler GitHub et l'état du checkout local avant tout `git pull --ff-only`. **Ne pas réinstaller** Ollama, Qwen3, Docker, Supermemory, Serena, shadcn ni refaire leurs smoke tests déjà réussis.
2. Consulter la documentation versionnée **Supermemory Local 0.0.9 / Codex** : distinguer API locale, MCP et intégration par hooks ; documenter champs capturés, déclencheurs, modèle d'autorisation, limites de la version auto-hébergée. Ne pas supposer que les fonctionnalités cloud sont disponibles localement.
3. Vérifier, sans montrer de secrets, le fournisseur réel d'inférence/embeddings et les éventuelles sorties réseau. Prévoir sauvegarde/restauration contrôlée du volume et de la clé avant données non fictives.
4. Préparer une **connexion Codex opt-in réversible**, d'abord sur un projet autorisé et une session isolée, idéalement sans hook global automatique. Préserver le `hooks.json` existant avec `SessionStart` et `PostToolUse` ; ne pas capter globalement conversations, identifiants et projets par défaut.
5. Si le pilote est concluant, valider explicitement règles de namespace par projet, exclusions de secrets, rétention, désactivation et rollback, puis documenter sur GitHub. Ensuite seulement envisager 21st.dev, Chrome DevTools MCP, oracle_reflex, vrai travail UI et la VM éventuelle.

## Commandes de contrôle non destructives (facultatives)

- `git -C C:\Dev\codex-context-efficiency-stack status --short --branch`, puis `git pull --ff-only` seulement si état propre.
- `docker --context desktop-linux compose --project-directory C:\Dev\supermemory-local -f C:\Dev\supermemory-local\compose.yaml -f C:\Dev\supermemory-local\compose.override.yaml ps`.
- `Invoke-RestMethod http://127.0.0.1:6767/v3/health`.

Ces commandes ne font pas de requête de génération et ne modifient pas les données. Ne jamais afficher la clé par un diagnostic brut.

## Prompt court à copier pour le nouveau chat

> Reprends **Codex – Stack IA & Autonomie** depuis `docs/CODEX_STACK_HANDOFF_2026-10-30.md` sur `main` du repo `Proginji2000/codex-context-efficiency-stack`. Supermemory Local 0.0.9 sous Docker avec Ollama 0.40.13/Qwen3 8B : health, API authentifiée, écriture et recherche sémantique d'une mémoire fictive **PASS**, port `127.0.0.1:6767`. **Aucun hook Codex modifié** et Supermemory pas encore relié à Codex. Serena 2.1.0 (LSP + mémoire intersessions) et shadcn (7 tools MCP) validés, PR #91/#92 fusionnées, worker UI et AGENTS global actualisés avec backups. PR #14 ouverte : V3 4/4 PASS fonctionnels, économie de quota non prouvée. Prochaine priorité : **brancher Supermemory sur Codex en mode opt-in, non destructif, sans exposer les clés ni remplacer les hooks SessionStart/PostToolUse** ; vérifier l'effectivité du LLM/embeddings et sauvegarder les données. Ne pas refaire les tests validés ni repartir sur le homelab/VM.
