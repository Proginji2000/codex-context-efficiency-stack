# P1.1 — H1.3 : qualification de la protection Windows MXC, sans appel modèle

**État : conception et critères synthétiques uniquement — 29 octobre 2026.** Cette étape ne réalise pas encore de test de sécurité OS. L'autorisation d'un test réel local nécessite une option séparée dans un lanceur futur.

## H1.2 réel : gate de politique déclarée ACCEPTÉ

L'opérateur a vérifié sous Windows non administrateur, sur main `e7649c965c56f63504a4dedb9165889f61a56089` : **24/24 tests de politique** et **36/36 tests de transport synthétiques** PASS. Le vrai Codex CLI 0.165.0 a renvoyé `THREAD_START_DECLARED_POLICY_PASS_UNATTESTED` et `P1_1_H12_REAL_THREAD_ECHO_PASS`. Le rapport déclare une connexion au vrai app-server, un thread réel éphémère, `approval_echo=never`, `sandbox_echo=workspaceWrite`, `network_access_echo=false`, `reasoning_effort_echo=medium`, **0 racines supplémentaires**, **0 sources d'instructions**, `turn_start_sent=false`, `model_calls_made=0` et la suppression du profil/workspace jetables.

**Ce que H1.2 ne prouve toujours pas :** isolation réelle MXC, trafic réseau impossible, nettoyage attesté de chaque descendant, identité et cycle de vie des workers. L'écho de la configuration n'est pas une attestation OS. La PR #14 reste OPEN, les 12 futurs essais A/B non autorisés.

## Pourquoi un H1.3 autonome sans modèle est possible

Le CLI officiel épinglé [`openai/codex rust-v0.165.0`, `cli/src/main.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/main.rs) expose `codex sandbox`. Sur Windows, la sous-commande utilise [`WindowsCommand` dans `cli/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/lib.rs) pour lancer une commande de test sous token restreint. Le code [`cli/src/debug_sandbox.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/debug_sandbox.rs) sélectionne explicitement `WindowsMxc` selon la configuration et refuse l'activation MXC si le backend natif n'est pas disponible. **Aucun tour IA n'est requis pour ce chemin CLI standalone.**

ATTENTION : `codex sandbox` et le chemin de sandbox d'une exécution app-server `turn/start` sont des chemins d'exécution distincts. Une réussite standalone ne prouve **pas** l'équivalence de leurs paramètres ni l'effectivité de MXC sur de futurs tours IA.

## Plan de test négatif futur H1.3a (lanceur réel NON implémenté)

1. Refuser toute session administrateur ; vérifier la version figée `codex-cli 0.165.0` et les permissions Windows sans élever les droits ou modifier les réglages globaux.
2. Créer uniquement de nouveaux emplacements temporaires dédiés : un `CODEX_HOME` vide, un workspace synthétique et un répertoire sentinelle hors workspace. Ne pas charger de sessions, tokens, AGENTS, projets utilisateur ou fichiers V2/V3.
3. Exécuter **avant le sandbox** un contrôle positif : le même utilisateur peut écrire puis supprimer un marqueur factice dans le répertoire sentinelle. Sinon, aucun refus ultérieur n'est probant.
4. Lancer une seule commande Python **sans modèle** sous `codex sandbox` avec `windows.sandbox=mxc` et des permissions workspace-write à réseau désactivé. Interdire l'installation, la mise en place du sandbox, la demande UAC, les élévations, les modifications de configuration et les relances silencieuses.
5. Observer dans le processus enfant : écriture factice **autorisée** dans le workspace et tentative d'écriture **refusée** dans la sentinelle située hors workspace. Il est essentiel de conserver une validation indépendante par le parent que cette dernière reste inchangée.
6. Borner la durée de tous les processus et vérifier leur arrêt. Émettre seulement des booléens et des codes fixes, jamais chemins, stderr bruts, secrets, identifiants ni contenu de dossier. Toute exception, timeout, création interdite de fichier extérieur, politique non vérifiable ou UAC => STOP.
7. Qualifier exclusivement **la contrainte d'écriture OS du CLI standalone**, si les contrôles confirment la bonne invocation MXC. Ne pas marquer le réseau, les workers ou le chemin `turn/start` comme attestés.

Le lieu de la sentinelle doit être choisi pour ne pas appartenir aux éventuelles racines implicites autorisées (notamment les répertoires temporaires). La vérification positive pré-sandbox et l'absence de modification après test sont obligatoires pour éviter une fausse preuve.

## Contrôles H1.3b / H1.3c / H1.3d restants

- **H1.3b** : prouver la correspondance de sécurité entre le CLI standalone et un vrai `turn/start` app-server. Ce test **pourrait nécessiter un appel modèle réel**, donc son implémentation et sa facturation restent explicitement **non autorisées** à ce stade.
- **H1.3c** : attestation indépendante des descendants/processus et des workers, y compris provenance, durée de vie et cleanup.
- **H1.3d** : test réseau négatif indépendant, avec un service témoin local dédié et une validation du blocage ; un simple flag `networkAccess=false` ou une variable d'environnement ne suffit pas.

## Artefacts livrés maintenant (sans OS ni modèle)

`scripts/Plan-CodexAB-H13MXC.py` affiche un contrat **plan-only**. Avec `--simulate`, il évalue une matrice d'observations toutes **fabriquées** ; le résultat `SYNTHETIC_H13_MATRIX_PASS_NOT_RUNTIME` ne confirme aucune propriété du système Windows. `scripts/Test-Plan-CodexAB-H13MXC.py` vérifie les critères requis (preuve positive interne, refus négatif externe, sentinelle inchangée, bonne provenance, interdiction de l'admin et des appels modèles, absence de mutations globales). La CI ne démarre aucun vrai Codex.

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Plan-CodexAB-H13MXC.py
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.3 offline tests failed' }
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Plan-CodexAB-H13MXC.py --simulate
if ($LASTEXITCODE -ne 0) { throw 'STOP: H1.3 synthetic matrix failed' }
```

**La PR #76 était exclusivement hors modèle et sans lanceur réel.** Elle n'autorisait aucune exécution OS. Suivi [#61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61), [#34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34), [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14).

## H1.3a — lanceur réel opt-in ajouté séparément (non exécuté)

`scripts/Probe-CodexAB-H13MXC.py` est le premier lanceur **standalone CLI sandbox**. Le mode par défaut affiche un plan sans processus. L'option **distincte** `--execute-local-mxc-probe` (Windows non-administrateur uniquement) :

- Vérifie le chemin du CLI épinglé et exige exactement `codex-cli 0.165.0`.
- Crée un nouveau `CODEX_HOME`, un workspace et un script Python **uniquement factices** dans une arborescence temporaire ; crée en parallèle un répertoire sentinelle neuf directement sous le profil utilisateur (hors `%TEMP%` pour éviter les droits temporaires implicites), sans lire ni modifier de fichier utilisateur existant.
- Confirme **avant le sandbox** que l'utilisateur non privilégié peut écrire puis lire un fichier témoin dans la sentinelle et le supprimer ; faute de quoi toute preuve de refus serait invalide.
- Lance une unique sous-commande `codex -c windows.sandbox="mxc" -c sandbox_mode="workspace-write" sandbox ...`, pour exécuter le script Python factice ; **aucun modèle, aucune commande de setup/uninstall, aucun `turn/start` ni `thread/start`**.
- Exige que le fils écrive une marque fixe **dans le workspace**, que sa tentative de création d'un fichier **hors workspace** soit refusée, et que le parent vérifie ensuite l'existence du témoin interne ainsi que l'absence du fichier extérieur. Tout écart, stdout imprévu, stderr non vide (y compris un avertissement de sécurité), exit code non nul ou timeout => **STOP**.
- Arrête le processus lancé avec une tentative de nettoyage ciblé. Les dossiers de test jetables sont supprimés par leurs gestionnaires de contexte. Cette opération ne prouve **pas** la terminaison indépendante de tous les descendants.
- Renvoie uniquement des marqueurs booléens et codes de résultat fixés : aucun contenu brut, chemin, nom de compte, ID, journal, texte de sandbox ni secret n'est répercuté.

**Limites** : un succès `STANDALONE_MXC_FILESYSTEM_NEGATIVE_PASS_NOT_APPSERVER` constitue une preuve négative d'écriture pour **cette seule invocation standalone**, sous le backend MXC **demandé**. Il ne constitue pas une attestation indépendante complète de la provenance interne du backend, de la sécurité réseau, de l'usage MXC par le vrai chemin app-server `turn/start`, du confinement du worker ou du nettoyage intégral du process-tree. Le backend peut être indisponible et doit alors échouer sans demander d'élévation ni de changement des protections.

**Tests CI** : `scripts/Test-Probe-CodexAB-H13MXC.py` teste uniquement la construction de la commande et des preuves **fabriquées** et des STOP (écriture extérieure permise, échec d'écriture interne, altération de sentinelle, stderr, sortie invalide), sous Windows et Ubuntu. Il n'invoque jamais le vrai CLI sandbox. Le déclenchement réel demeure une décision locale et séparée.
