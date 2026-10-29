# P1.1 — H1.2 réel : lecture de la politique d'un thread éphémère (0 modèle)

**Date : 29 octobre 2026.** H1.2 hors modèle a été validé sur Windows par l'opérateur : **19/19 tests**, `SYNTHETIC_THREAD_POLICY_ECHO_PASS`, `P1_1_H12_OFFLINE_POLICY_PASS`, commit `f211026f40b5f1be0361e4e777a4623398435b06`. Le vrai app-server **H1.1** a également passé l'initialisation `initialize` / `initialized` dans un `CODEX_HOME` neuf (rapport non attesté OS).

## Nouveau composant

`scripts/Probe-CodexAB-H12RealThread.py` est le client **H1.2 réel**, conçu d'après les schémas officiels du tag [`openai/codex rust-v0.165.0`](https://github.com/openai/codex/tree/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2) et l'enveloppe JSON-RPC *sans* champ `jsonrpc` obligatoire. Il a deux modes stricts :

- **Par défaut** : affiche un plan JSON sans lancer de processus ni créer de fichiers.
- **`--execute-local-thread-probe`** : uniquement sur Windows **non administrateur**, vérifie le binaire Codex CLI 0.165.0 épinglé, crée un `CODEX_HOME` et un workspace temporaires et vides, démarre un seul `codex app-server --stdio` avec environnement restreint, puis envoie **exactement** `initialize`, `initialized` et **un** `thread/start` avec `ephemeral=true`, `approvalPolicy=never`, `sandbox=workspace-write`, `windows.sandbox=mxc`, modèle `gpt-6-luna` et effort `medium`. **Il n'envoie pas `turn/start`, aucun prompt, aucune tâche, aucun appel modèle, aucun outil.**

La réponse passe le vérificateur H1.2 strict déjà fusionné (`Check-CodexAB-H12ThreadPolicy.py`) : permissions et réseau **annoncés**, modèle/effort, cwd, limites des racines d'écriture, thread éphémère sans tours et sources d'instructions bornées aux deux dossiers temporaires. En cas de divergence, STOP et **aucun élargissement des permissions**. Seule une catégorie d'erreur fixe (sans noms de fichiers, IDs, logs de serveur ou identifiants privés) est affichée. `stderr` du serveur n'est pas publié.

## Incident local : notification non reconnue — 29/10/2026

L'opérateur a obtenu `GIT_VERIFIED`, **19/19 tests H1.2 policy PASS**, **18/18 tests du faux serveur PASS**, puis **`STOP: H12_REAL_THREAD_PROBE_FAILED:THREAD_NOTIFICATION_UNEXPECTED`** à la création réelle du premier thread. **Aucun thread réel ou contrôle MXC n'est validé par cet essai** : le retour n'est pas une réponse `thread/start` acceptée.

Source figée : [Codex `rust-v0.165.0`, enum `ServerNotification`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/protocol/common.rs). Avant une réponse `thread/start`, des notifications telles que `skills/changed`, `mcpServer/startupStatus/updated`, `account/updated`, `account/rateLimits/updated` ou `app/list/updated` peuvent être diffusées. Le filtre initial acceptait uniquement les notifications de thread et quelques messages génériques ; l'exacte méthode reçue lors de cet essai **n'a pas été enregistrée** pour préserver la confidentialité. **Ne pas supposer qu'il s'agissait de l'un de ces événements.**

Le correctif introduit une **liste bornée et explicite d'événements passifs**, sans afficher ni conserver leurs paramètres, mais maintient le refus des messages inconnus, requêtes serveur imprévues, réponses ID divergentes et flux excessifs. Les notifications de risque font **STOP avec code fixe** : `windows/worldWritableWarning` (`THREAD_WARNING_WINDOWS_WORLD_WRITABLE`), `configWarning`, `warning`, `guardianWarning`, `error`, `deprecationNotice`, `windowsSandbox/setupCompleted`, `thread/settings/updated`, `model/verification`. En particulier, **on ne passe jamais outre un avertissement de répertoire accessible en écriture à tous** pour valider MXC.

La CI teste les notifications synthétiques passives et les avertissements à ne pas ignorer ; le vrai app-server n'est **jamais exécuté en CI**. Après fusion et une seule nouvelle tentative explicite, un éventuel `STOP` peut être un avertissement de sécurité et exige une analyse ciblée, sans élargissement des permissions ni contournement de sandbox.

## Deuxième échec réel — préflight H1.2 du 29/10/2026

L'opérateur a de nouveau validé **19/19 tests de politique** et **22/22 tests de transport**, puis a reçu `STOP: H12_REAL_THREAD_PROBE_FAILED:THREAD_NOTIFICATION_UNEXPECTED`. Le correctif de la PR #71 n'a donc **pas** permis de qualifier la politique d'un thread réel. La méthode exacte demeure inconnue ; **ne pas élargir l'allowlist sans identification**.

Le correctif de diagnostic suivant **ne modifie aucune permission, aucune notification admise et aucune politique MXC**. Pour toute notification encore inconnue, il conserve le STOP mais affiche une **empreinte SHA-256 tronquée à 12 caractères hexadécimaux** portant uniquement sur la chaîne du champ `method`. Le code est du type `THREAD_NOTIFICATION_UNEXPECTED:METHOD_SHA256_XXXXXXXXXXXX`. Il n'imprime **ni méthode brute, ni `params`, ni chemin, ni identifiant, ni stderr/stdout brut du serveur**. Toute empreinte mal formée est supprimée du diagnostic.

Une empreinte n'est pas une attestation cryptographique de la provenance du serveur et peut théoriquement être rapprochée d'une liste publique de méthodes ; son seul objet est de comparer l'événement à l'énumération publique [`ServerNotification`, version rust-v0.165.0](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/protocol/common.rs) **hors ligne**, après un essai local explicitement initié. Aucun hash du message entier ou de données d'authentification n'est calculé. Les avertissements `windows/worldWritableWarning` et autres signaux de sécurité conservent leurs codes d'arrêt fixes.

En cas de nouvel échec : rapporter le code et **STOP** sans nouvelle relance, puis confronter l'empreinte aux méthodes officiellement déclarées avant toute décision. Si l'empreinte ne correspond pas à une méthode officielle, l'événement reste inconnu et refusé.

## Empreinte identifiée : notification de contrôle distant (29/10/2026)

Le troisième essai local réel H1.2 (main `e6725ad52330ed8f2fc90c39c1aa46c5291bd362`) a confirmé : 19/19 tests de politique PASS, 26/26 tests de transport PASS, mais `THREAD_NOTIFICATION_UNEXPECTED:METHOD_SHA256_FC90BE8D31A9`. H1.2 réel **n'est pas encore PASS**.

Une comparaison **hors modèle** avec les chaînes exactes des méthodes du fichier officiel [`app-server-protocol/src/protocol/common.rs` au tag `rust-v0.165.0`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/protocol/common.rs) donne **une correspondance exacte** : SHA-256 tronqué de `remoteControl/status/changed` = `FC90BE8D31A9`.

Selon le schéma [`v2/remote_control.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/protocol/v2/remote_control.rs), son champ `params.status` est l'une des quatre valeurs `disabled`, `connecting`, `connected`, `errored`. **L'empreinte de méthode ne renseigne pas le statut de contrôle à distance observé sur le PC.** Ne pas inférer que la fonction est activée ou désactivée sur cette base.

Le correctif accepte ce seul événement comme passif **si et seulement si** `params.status == "disabled"`. Les trois autres valeurs entraînent `STOP: THREAD_REMOTE_CONTROL_NOT_DISABLED`. Une valeur absente, invalide ou un `params` mal formé entraîne `STOP: THREAD_REMOTE_CONTROL_STATE_INVALID`. Les identifiants `installationId`, `environmentId` et `serverName` ne sont ni copiés dans le rapport ni imprimés. Les avertissements Windows, les notifications inconnues et la limitation du nombre de messages conservent leurs protections précédentes.

Une réponse validée pourrait encore ne prouver **que** la politique déclarée par le thread. Il reste à démontrer séparément MXC réel, réseau, cycle worker et nettoyage complet de l'arbre de processus. Aucun tour IA et aucun benchmark A/B n'est lancé par la CI.

## Premier échec de validation du vrai retour de politique — 29 octobre 2026

Après PR #73, l'opérateur a vérifié `GIT_VERIFIED`, **19/19** tests de politique et **30/30** tests de transport. Le vrai app-server a émis la réponse RPC `thread/start` attendue, après traitement de la notification `remoteControl/status/changed`, mais la validation stricte a échoué avec `STOP: H12_REAL_THREAD_PROBE_FAILED:THREAD_ECHO_VALIDATION_FAILED`.

**C'est une progression de protocole, pas un PASS de sécurité.** Le code ne connaissait pas l'assertion précise ayant échoué, car il ramenait volontairement les erreurs au même code. Il ne faut pas conclure que l'écho de sandbox, les racines d'écriture, l'absence de réseau, le modèle ou le caractère éphémère sont conformes.

Les schémas officiels [`ThreadStartResponse`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartResponse.ts), [`Thread`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/Thread.ts) et [`SandboxPolicy`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/SandboxPolicy.ts) confirment qu'une réponse réelle comporte un `thread.ephemeral`, un `thread.turns` et un `sandbox` typé, entre autres. Une structure valide n'implique pas que ses valeurs correspondent à notre profil de sécurité.

**Correction diagnostique uniquement :** si `policy.validate` échoue, le préflight conserve le STOP et ajoute une seule catégorie issue d'une **liste fermée de codes de notre validateur local** (par ex. `SANDBOX_NETWORK_UNPROVEN`, `WRITABLE_ROOTS_MISMATCH`, `UNEXPECTED_WRITABLE_ROOT`, `THREAD_NOT_EPHEMERAL`, `POLICY_ECHO_MISMATCH`). Ex. `THREAD_ECHO_VALIDATION_FAILED:SANDBOX_NETWORK_UNPROVEN`. Aucun texte d'exception arbitraire, aucune valeur réelle renvoyée, aucun chemin, ID, secret ou source d'instruction n'est imprimé. Les codes inconnus deviennent `OTHER_POLICY_VALIDATION_FAILURE`.

**Interdit de faire passer ce gate en assouplissant les critères avant d'avoir examiné la catégorie exacte et sa pertinence par rapport au protocole officiel.** Un échec de sécurité (réseau, racines, sandbox, approval) doit rester bloquant. La CI reste un faux app-server et n'appelle jamais un modèle.

## Limites de preuve

- Un `THREAD_START_DECLARED_POLICY_PASS_UNATTESTED` confirme que **le vrai app-server a créé un thread et renvoyé la politique attendue**. Il **ne** prouve **pas** que le sandbox MXC applique la protection au niveau OS.
- La sécurité réseau, la terminaison complète de tous les processus descendants, l'identité/runtime du worker et la délégation ne sont **pas attestées**. Ces vérifications sont des étapes distinctes après H1.2. Le démarrage du serveur peut effectuer des I/O internes même en l'absence de tours.
- Le profil est neuf et non authentifié ; la demande `thread/start` peut être refusée au démarrage. Cela sera classé `THREAD_RPC_REJECTED`, **sans** copier d'`auth.json`, connecter des secrets ou élever les droits.
- Le script ne réutilise jamais les sessions historiques V2/V3, ne modifie pas les fichiers globaux de Codex, n'accepte aucune exécution A/B, n'autorise pas la fusion de PR #14.

## Vérification offline et CI

La CI Windows et Ubuntu utilise **seulement un faux app-server Python**. Elle vérifie le transport, le handshake, les refus de réponses incohérentes, de notification imprévue, d'erreur serveur, de délais dépassés et d'élargissement de politique. Les tests du validateur strict H1.2 sont également conservés dans le dépôt.

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Probe-CodexAB-H12RealThread.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.2 fake-server tests failed' }
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Probe-CodexAB-H12RealThread.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.2 plan failed' }
```

Le premier essai réel est déclenché uniquement par un **appel séparé et explicite** à `--execute-local-thread-probe` après les tests et un contrôle Git/pinning. En cas d'échec, ne pas relancer en boucle ; transmettre uniquement le code `STOP: H12_REAL_THREAD_PROBE_FAILED:<CATEGORY>`.

Suivi : [issue #61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61) ; [issue #34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34) ; [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14) non fusionnée.
