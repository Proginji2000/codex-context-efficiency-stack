# P1.1 — H1.2 préparation : contrôle déclaratif de `thread/start` hors modèle

## Résultat H1.1 réel — 29 octobre 2026

Sur le PC Windows de l'opérateur, Codex CLI isolé **0.165.0**, commit du dépôt `9a64f8a7c6ea98fba91e44ad615c123c1fac36bb` : 22/22 tests synthétiques PASS ; **`ISOLATED_STDIO_HANDSHAKE_PASS_UNATTESTED`** et `P1_1_H1_INITIALIZE_PREFLIGHT_PASS`. Le client n'a envoyé que `initialize` puis `initialized`, avec `thread_start_sent=false`, `turn_start_sent=false`, `model_calls_made=0`. Le profil temporaire a été supprimé selon la sortie du programme.

**Bornes de preuve** : `sandbox_mxc_effectiveness_verified=false`, `network_isolation_verified=false`, `worker_delegation_independently_verified=false`, `child_tree_cleanup_independently_attested=false`. La réussite de H1.1 démontre un protocole d'initialisation valide, pas les permissions effectives d'exécution.

## H1.2 : étape contractuelle, sans serveur réel

Le script `scripts/Check-CodexAB-H12ThreadPolicy.py` est **exclusivement hors modèle** : aucun subprocess, socket, thread Codex, accès au profil normal, fichier créé ou modèle démarré. Il fournit par défaut un plan et avec `--simulate` valide une réponse **fabriquée** de `thread/start`.

Le validateur accepte seulement :

- requête `thread/start` avec modèle `gpt-6-luna`, `approvalPolicy=never`, `sandbox=workspace-write`, `windows.sandbox=mxc`, effort `medium`, `ephemeral=true` et workspace explicitement désigné ;
- réponse de même ID, modèle et effort attendus, `approvalPolicy=never`, `sandbox.type=workspaceWrite`, `networkAccess=false` (champ déclaratif), workspace identique, racines d'écriture **strictement** bornées au workspace jetable et éventuellement au CODEX_HOME jetable ;
- thread `ephemeral=true` sans tour, sources d'instructions uniquement sous le workspace ou le profil jetable. Aucun ID, chemin personnel, commande, message de session ou contenu worker n'est imprimé.

Tout désaccord entraîne STOP, sans assouplir de politique ni contourner MXC. Le résultat `SYNTHETIC_THREAD_POLICY_ECHO_PASS` ne signifie **jamais** que le véritable app-server a créé un thread ou que le sandbox Windows empêche effectivement des accès hors périmètre.

### Commandes sûres de validation hors modèle

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B '.\scripts\Test-Check-CodexAB-H12ThreadPolicy.py'
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.2 offline tests failed' }
& 'C:\Dev\Python31314\python.exe' -B '.\scripts\Check-CodexAB-H12ThreadPolicy.py' --simulate
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.2 synthetic policy failed' }
```

## Gate H1.2 réel — non exécuté et non autorisé par cet outil

Concevoir **séparément** un client à profil CODEX_HOME et workspace jetables neufs, non-admin, Codex CLI exactement 0.165.0, transport stdio conforme sans champ `jsonrpc` obligatoire. Après H1.1 du même processus, il pourrait envoyer **un seul** `thread/start` éphémère avec politique verrouillée, jamais `turn/start`, puis vérifier la réponse avec les mêmes contrôles. L'opérateur devra autoriser explicitement cette action et conserver un diagnostic anonymisé. Le serveur peut créer du stockage temporaire, consulter sa configuration et effectuer des I/O au lancement, indépendamment de tout tour modèle.

Une réponse du type `workspaceWrite` constitue **une déclaration de politique**, pas une preuve de l'effectivité MXC sous Windows. Les tests négatifs runtime, la preuve des workers et les benchmarks A/B représentent des gates distincts. Ne pas fusionner la PR #14 ni lancer les 12 essais théoriques dans ce chantier.

## Références figées

- [ThreadStartParams.ts — Codex rust-v0.165.0](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartParams.ts)
- [ThreadStartResponse.ts — Codex rust-v0.165.0](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/ThreadStartResponse.ts)
- [SandboxPolicy.ts — Codex rust-v0.165.0](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/schema/typescript/v2/SandboxPolicy.ts)
- [Protocole sans champ JSON-RPC obligatoire](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/app-server-protocol/src/rpc.rs)

Suivi : issues #61 et #34 ; PR #14 ouverte.
