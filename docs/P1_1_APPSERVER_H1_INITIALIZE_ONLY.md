# P1.1 H1 — préflight réel de transport stdio isolé (sans tour IA)

Statut : outil de préflight limité, **non exécuté sur le PC de l'utilisateur tant que la commande `--execute-local-preflight` n'a pas été explicitement lancée**. Les tests GitHub utilisent uniquement un **faux serveur Python**, jamais le vrai Codex.

## Portée et écart par rapport à H0

H0 (PR #64) simule entièrement les réponses app-server. H1 ajoute un client Python à transport local stdio, préparé pour le CLI isolé `codex-cli 0.165.0`, avec **seulement** `initialize` (RPC id 1) et `initialized` (notification). Aucun `thread/start`, `turn/start`, outil, prompt, worker ou modèle n'est lancé par ce client. Le compteur de `model_calls_made=0` est une propriété du **client**, pas une attestation générale des éventuels accès réseau internes au démarrage du serveur.

Références figées : [CLI `AppServerCommand` `--stdio`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/main.rs), [transport à messages JSONL](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-transport/src/transport/stdio.rs), [initialisation](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/InitializeParams.ts) et [réponse](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/InitializeResponse.ts).

## Sécurité et limites exactes

- **Mode par défaut : plan JSON uniquement**, sans processus, sans écriture de fichier ou appel IA. L'exécution réelle exige l'option distincte `--execute-local-preflight` sur Windows **non administrateur**.
- L'exécutable est verrouillé à `C:\Dev\codex-cli-0165\node_modules\.bin\codex.cmd` et sa sortie `--version` doit être exactement `codex-cli 0.165.0`.
- Un **nouveau** `CODEX_HOME` temporaire est créé, jamais celui de la session normale ou des précédentes paires V2/V3 ; aucune configuration TOML ni authentification n'est copiée. L'environnement transmis est strictement limité à quelques variables de fonctionnement et ne transmet pas les variables d'API keys et tokens connus.
- La réponse d'initialisation doit déclarer **exactement** le chemin du profil temporaire. Un autre profil, une plateforme inattendue, un JSON invalide, une réponse erronée ou un timeout font **STOP**.
- Le client ferme l'entrée standard, arrête le processus et tente de gérer son arbre descendant (Windows `taskkill /T /F` ciblé sur son seul PID si le processus ne termine pas). Les tentatives de nettoyage restent **best-effort** et ne sont pas une attestation formelle d'absence de descendants.
- Le vrai serveur peut créer des fichiers temporaires ou réaliser de l'I/O au démarrage. **Aucune absence de trafic réseau ou d'usage de credentials par le serveur n'est démontrée par ce préflight**. Il n'atteste ni l'isolation MXC effective, ni la visibilité des workers, ni les permissions runtime des futurs threads.
- Aucun texte brut issu de `stdout`/`stderr`, aucune clé, aucun identifiant, aucun chemin personnel ni session ID n'est imprimé. La sortie est un petit JSON de résultats fixes. Les tests refusent les réponses invalides et utilisent uniquement des chemins temporaires.

## Contrôle sans vrai Codex : peut être exécuté immédiatement après Git pull

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Probe-CodexAB-AppServerH1.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1 fake-server tests failed' }
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Probe-CodexAB-AppServerH1.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1 plan failed' }
```

## Premier démarrage réel (à autoriser explicitement séparément)

Le programme possède la commande `--execute-local-preflight` ; elle démarre **un vrai app-server** dans un `CODEX_HOME` temporaire, en lui transmettant uniquement les messages d'initialisation. Ce déclenchement n'est pas effectué par la CI, ni par les commandes ci-dessus.

**Ne pas considérer une connexion réussie comme l'autorisation de créer des threads/tours ou d'exécuter les 12 scénarios.** Le gate H1 suivant consiste à qualifier la politique effective des threads et les contraintes Windows MXC par des tests négatifs dans un environnement contrôlé. La PR #14 reste ouverte et les preuves V2/V3 restent intouchées.

Suivi : [issue #61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61), [roadmap](QUALIFICATION_ROADMAP_2026.md), [H0](P1_1_APPSERVER_HARNESS_H0_0165.md).
