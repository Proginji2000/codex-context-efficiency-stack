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

## Diagnostic après premier essai réel non concluant (29/10/2026)

L'opérateur a confirmé `GIT_VERIFIED`, 15/15 tests synthétiques et la planification sans processus. L'exécution réelle s'est arrêtée avec l'ancien message générique `STOP: H1_LOCAL_PREFLIGHT_FAILED` ; **le motif précis n'a pas été enregistré**, et aucun succès de connexion réelle ne doit être déclaré. Cette erreur ne prouve ni un défaut MXC ni un échec de délégation.

La révision suivante conserve les mêmes permissions et messages JSON-RPC mais affiche une **catégorie fixe autorisée**, sans texte d'exception brut ni journal du serveur : `ELEVATED_SESSION_FORBIDDEN`, `PINNED_CLI_MISSING`, `CLI_VERSION_PROBE_FAILED`, `PINNED_VERSION_MISMATCH`, `APP_SERVER_START_FAILED`, `SERVER_EXITED_BEFORE_INITIALIZE`, `INITIALIZE_RESPONSE_TIMEOUT`, `INITIALIZE_RPC_REJECTED`, `ISOLATED_HOME_MISMATCH`, `CHILD_CLEANUP_UNVERIFIED`, etc. Toute erreur non répertoriée devient `OTHER_LOCAL_PREFLIGHT_FAILURE`. Un processus fermé avant `initialize` reçoit désormais un diagnostic distinct du timeout, lorsque son état est observable.

**Aucun modèle réel n'est invoqué pour ce correctif.** Les tests de diagnostic sont entièrement synthétiques. Le démarrage local reste derrière `--execute-local-preflight`, sans élévation, sans désactivation de MXC ni accès aux profils historiques. S'il échoue à nouveau, **ne pas lancer de relance en boucle** : utiliser la catégorie précise pour décider du correctif ciblé.

## Diagnostic H1 confirmé — absence de `jsonrpc` dans le protocole épinglé

Un nouveau préflight local du 29/10/2026 a passé **19/19** tests synthétiques et le plan, puis s'est arrêté sur `H1_LOCAL_PREFLIGHT_FAILED:INVALID_JSONRPC_VERSION`. **La connexion réelle reste non validée** à cette date : ce résultat ne prouve pas une initialisation réussie.

La cause de la **classification d'erreur** a été vérifiée directement dans [le code officiel Codex `rust-v0.165.0` `rpc.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/rpc.rs) : `We do not do true JSON-RPC 2.0, as we neither send nor expect the "jsonrpc": "2.0" field.` Les messages réponse `JSONRPCResponse` ne comportent que `id` et `result`, et les notifications `method` / `params`. L'ancien client exigeait indûment `payload.jsonrpc == "2.0"`.

**Correctif :** l'enveloppe de requête sortante suit désormais le protocole sans `jsonrpc` ; le parseur accepte l'absence du champ dans une réponse, accepte `"jsonrpc":"2.0"` pour rester tolérant et rejette toute valeur contradictoire. Les tests reproduisent ces trois scénarios avec un faux serveur, sous Windows et Ubuntu. Aucun changement de politique MXC, de sandbox, d'autorisation ou de `CODEX_HOME` ; aucun appel modèle et aucune lecture de session historique.

Le prochain essai réel reste une action locale **explicitement autorisée et bornée à une seule tentative**. Ne pas recycler les anciennes sorties ni déclarer H1 validé tant que le véritable serveur n'a pas répondu correctement au handshake complet.

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
