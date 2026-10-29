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

## Premier essai H1.3a standalone : stderr inattendu — 29 octobre 2026

L'opérateur a exécuté le code épinglé sur main `b450f4a5ea672aa415c28654936f82f97bf02130`. Le dépôt était propre, **11/11 tests de matrice synthétique PASS**, **17/17 tests de probe synthétiques PASS**, mais la première exécution réelle `codex sandbox` s'est arrêtée avec `STOP: H13_STANDALONE_MXC_FAILED:SANDBOX_STDERR_PRESENT`. La sous-commande a émis des données sur `stderr`, dont le contenu exact est inconnu ; il serait incorrect de conclure à un défaut MXC, à une protection effective ou à un simple warning inoffensif. **H1.3a réel reste NON QUALIFIÉ.**

La révision de diagnostic conserve le **STOP obligatoire sur tout `stderr` non vide**. Elle examine seulement des indices fixes dans un échantillon borné de ce canal : erreur de lancement sandbox, avertissement de sécurité, argument CLI refusé, configuration refusée, erreur Python du test, avertissement générique ou sortie non reconnue. Elle ajoute les booléens de présence du marqueur de sortie attendu et l'état zéro/non-zéro du code de sortie, sans publier le texte, la longueur précise, les chemins, les arguments réels, les identifiants ou une empreinte du texte d'erreur. Exemple de catégorie anonymisée : `SANDBOX_STDERR_PRESENT:CLI_USAGE_ERROR:MARKER_ABSENT:EXIT_NONZERO` ; **ce n'est pas un diagnostic réel observé**.

Le code amont épinglé [`debug_sandbox.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/debug_sandbox.rs) démontre que le chemin CLI Windows peut écrire des erreurs de lancement sur stderr, tandis que [`cli/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/lib.rs) expose la commande `sandbox` et ses arguments. La CI simule les catégories seulement ; **aucune nouvelle exécution Windows MXC réelle** n'est automatisée dans GitHub.

Si le résultat est `SECURITY_WARNING` ou `BACKEND_LAUNCH_ERROR`, les protections ne doivent pas être désactivées pour passer le test. S'il est `UNRECOGNIZED_STDERR`, la catégorie demeure incertaine et la prochaine action doit être une analyse prudente du lancement, pas une exception « ignore stderr ». Le test autonome ne démontre ni les permissions du chemin app-server `turn/start`, ni la sécurité réseau, ni le cycle worker, ni le nettoyage de chaque descendant.

## Second H1.3a Windows STOP et vérification préalable de compatibilité officielle (29/10/2026)

Sur main `289f4d51257a41cfc4d5d80d86c944f40ae7777f`, l'utilisateur a obtenu 11/11 tests de matrice PASS, 22/22 tests du lanceur PASS et un échec réel `SANDBOX_STDERR_PRESENT:GENERAL_WARNING:MARKER_ABSENT:EXIT_NONZERO`. Ce rapport signifie : **stderr présent, sortie de test attendue absente et code de sortie non nul**. Le texte n'a pas été conservé : **on ne peut ni confirmer un simple avertissement ni identifier le backend effectivement exécuté**. H1.3a reste NON VALIDÉ.

Une recherche des instructions officielles publiques de Codex Windows a confirmé une commande de compatibilité native MXC pour CLI **0.162.0+**, utilisant l'override explicite `-c windows.sandbox=mxc`, puis `sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK`. Référence : [Windows sandbox — OpenAI](https://learn.chatgpt.com/docs/windows/windows-sandbox) ; le code source figé [`rust-v0.165.0` `cli/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/lib.rs) décrit les arguments `--permission-profile` et `--include-managed-config` et [`cli/src/debug_sandbox.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/debug_sandbox.rs) distingue le mode hérité des profils de permissions.

**Correctif :** le lanceur H1.3a demande désormais **deux commandes autonomes successives, jamais des tours modèles**, dans le même `CODEX_HOME` et workspace jetables :

1. D'abord, la commande de compatibilité officielle avec `cmd.exe /d /c echo MXC_OK`, sans écriture de test. Seule la sortie **exacte** `MXC_OK`, un code 0 et **aucun stderr** permettent de continuer. Toute erreur/avertissement provoque STOP avec diagnostic fixe `COMPAT_STDERR_PRESENT:<CLASS>:<MARKER_FLAG>:<EXIT_FLAG>`, ou `COMPAT_EXIT_NONZERO`, `COMPAT_STDOUT_INVALID`.
2. **Uniquement après réussite** de l'étape précédente, lance le test négatif d'écriture : exactement le **même profil explicite MXC `:workspace`**, avec séparateur `--` et script Python factice. Le contrôle hôte hors sandbox, la sentinelle extérieure, les limites de capture, les refus sur stderr et le nettoyage ciblé demeurent inchangés.

L'option `--include-managed-config` **lit** les exigences de configuration administrées applicables pour le mode recommandé par la documentation ; le lanceur ne les modifie pas, ne désactive pas de règle, et n'autorise pas une élévation. Les critères d'écriture du test restent fail-closed : l'existence d'un seul fichier extérieur créé implique STOP. **Deux processus autonomes peuvent être lancés dans cette nouvelle version**, séquentiellement, sans modèle, plutôt qu'un seul. Le résultat n'atteste pas le chemin app-server `turn/start`, le réseau ou les workers.

En cas d'échec de l'étape de compatibilité, **ne pas lancer le test négatif et ne pas désactiver les avertissements**. Les tests CI couvrent seulement les deux commandes construites et des sorties fictives, jamais le MXC natif.


## Troisième H1.3a STOP — compatibilité MXC réelle non démontrée (29/10/2026)

L'opérateur a exécuté main `b217f4c960d473591355a23610a4ef6263ef6ccb` : **11/11 tests de matrice** et **28/28 tests synthétiques du lanceur** PASS ; la **première commande de compatibilité** a échoué avec :
`COMPAT_STDERR_PRESENT:GENERAL_WARNING:MARKER_ABSENT:EXIT_NONZERO`.

Le lanceur n'a donc **pas** lancé le test d'écriture externe après cet échec. Le préflight standalone MXC reste **BLOCKED**. Comme le classificateur cherche une sous-chaîne « warning » dans tout stderr, ce code n'exclut pas un message d'échec **plus précis** présent dans la même sortie ; aucun stderr brut n'a été conservé.

### Diagnostic OS en lecture seule

La [documentation officielle Windows Sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox) exige sur Windows 11 les capacités MXC introduites dans les builds **26100.9278 (24H2)** ou **26200.9278 (25H2)**. Une version de base `26200` sans numéro de révision (UBR) **ne suffit pas** à déterminer l'éligibilité. Même un build égal/supérieur ne prouve pas que les capacités nécessaires sont installées, activées ou autorisées par la politique de l'appareil.

La nouvelle option **`--check-windows-build`** lit uniquement `CurrentBuildNumber` et `UBR` de `HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion`. Elle ne lance **aucun processus**, ne démarre pas Codex, ne modifie pas le registre et ne fait aucun appel modèle. Elle affiche `DOCUMENTED_BUILD_THRESHOLD_MET`, `BELOW_DOCUMENTED_MINIMUM` ou `OUTSIDE_DOCUMENTED_BUILD_MATRIX`, sans information personnelle. Elle distingue explicitement la compatibilité de version documentée de l'**effectivité du backend MXC**, toujours inconnue.

Le futur lanceur réel H1.3a refuse désormais dès le préflight les builds 26100/26200 dont la révision est inférieure à **9278**, ainsi que les versions hors de la matrice documentée, **sans tenter de lancer MXC**. Pour ces dernières, il ne conclut pas qu'elles sont incompatibles ; il refuse simplement d'extrapoler la documentation.

### Diagnostic stderr non ambigu

Le classificateur traite maintenant les chaînes explicites du code source officiel [`mxc-sandbox/src/windows.rs` (version rust-v0.165.0)](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/windows.rs) et [`mxc-sandbox/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/lib.rs) **avant** de classer tout « warning » générique : `MXC_NATIVE_UNAVAILABLE`, `MXC_LAUNCHER_FAILURE` ou `MXC_POLICY_RESTRICTION`. Ce diagnostic ne publie ni texte d'erreur, ni répertoire, ni HRESULT, ni ID, ni secret ; **tout stderr non vide provoque toujours STOP** et ne peut pas être ignoré.

**Décision actuelle :** avant une nouvelle tentative réelle, exécuter uniquement l'option de lecture de build Windows et analyser le résultat. Aucun fallback de sandbox, installation, UAC, modification de configuration Windows, désactivation MXC, ancien profil Codex, `turn/start` ou modèle IA n'est autorisé.

## Quatrième vérification — build Windows valide, backend natif toujours non qualifié (29/10/2026)

Le dernier rapport de l'opérateur sur main `f5b0895eae38ca2639f39eab0d107daa77f3feca` montre : **36/36** tests synthétiques du lanceur PASS, `mode=READ_ONLY_OS_BUILD_CHECK`, `windows_build=26200`, `windows_revision=9711`, seuil documenté `26200.9278`, `os_threshold_status=DOCUMENTED_BUILD_THRESHOLD_MET`, `processes_launched=0`, `model_calls_made=0`. **Le manque de révision Windows n'explique donc pas la difficulté observée sur ce poste** ; la disponibilité native de `ProcessSecurityEnvironmentApi` ainsi que la permission MXC gérée restent **non démontrées**.

Selon le code épinglé [`codex-rs/mxc-sandbox/src/availability.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/availability.rs), la disponibilité n'est pas un simple test de build : Codex charge l'API native, crée un environnement de sécurité et construit ses attributs de démarrage **sans lancer de processus**. Cela peut échouer même sur un OS dont la version dépasse le seuil documenté.

### Nouveau mode de diagnostic H1.3a : une compatibilité seulement

L'option séparée `--execute-local-mxc-compat-only` du script `scripts/Probe-CodexAB-H13MXC.py` vise à éviter de répéter à l'aveugle le test de confinement complet. Elle :

- vérifie Windows non administrateur, version exacte `codex-cli 0.165.0` et éligibilité du build documenté ;
- crée un `CODEX_HOME` et un workspace temporaires **neufs**, sans recopier sessions, identifiants, projets ni configurations de profil utilisateur ;
- exécute **au maximum une seule** commande standalone de compatibilité `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK` ;
- impose stdout exactement `MXC_OK`, stderr vide, exit code 0 ; toute erreur ou avertissement donne STOP avec catégorie fixe, sans texte brut, chemin ni secret ;
- **ne crée aucune sentinelle extérieure et ne démarre pas le test Python d'écriture**, même si le contrôle de compatibilité réussit. Aucun `thread/start`, `turn/start`, modèle, worker ou benchmark A/B ;
- sépare explicitement une possible réussite de cette commande de toute preuve de confinement de fichiers, sécurité réseau, provenance worker, nettoyage des descendants et parité app-server.

La version affichée par défaut reste `PLAN_ONLY_NO_PROCESS`. Les trois options `--check-windows-build`, `--execute-local-mxc-compat-only` et `--execute-local-mxc-probe` sont mutuellement exclusives. Les tests CI ne lancent pas de vrai Codex, utilisent de faux retours, vérifient l'absence de seconde commande après échec et la confidentialité des diagnostics.

Une réussite du mode compatibilité ne vaudrait **que** `MXC_COMPAT_STANDALONE_ECHO_PASS_NOT_ENFORCEMENT`. Si le résultat est encore `GENERAL_WARNING`, sa cause restera **non identifiée** à partir d'une catégorie anonymisée : il faudra alors envisager une inspection strictement locale et contrôlée du message du CLI, sans divulguer de texte sensible. Il ne faut ni supprimer l'avertissement, ni demander UAC, ni modifier la configuration globale ou changer de backend pour obtenir artificiellement un PASS.

## Cinquième essai H1.3a — erreur native du lanceur, sans canary (29 octobre 2026)

Sur main `db5829f4830109c30113e9c8b0e0bb1dc3fe51a5`, l'utilisateur obtient **11/11 tests de matrice** et **41/41 tests du lanceur** PASS, mais la commande réelle de compatibilité unique renvoie `COMPAT_STDERR_PRESENT:MXC_LAUNCHER_FAILURE:MARKER_ABSENT:EXIT_NONZERO`. **H1.3a réel reste BLOCKED**. Le script Python d'écriture n'a pas été exécuté, aucun résultat de confinement de fichiers ou de réseau n'existe. Les messages stderr n'ont pas été conservés ; `MXC_LAUNCHER_FAILURE` est une catégorie large, pas la preuve d'un échec précis d'API Win32.

L'inspection du code officiel figé [`mxc-sandbox/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/lib.rs) révèle que `MXC launcher:` est un préfixe **générique** autour de `windows::run()`. Son échec peut se produire à plusieurs étages : disponibilité PSEC native, environnement de lancement, décodage de la requête, volumes et dossiers système, traduction de politique ou processus MXC. Le code [`mxc-sandbox/src/native.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/native.rs) expose des erreurs supplémentaires, notamment la prise en charge native des chemins de refus.

### Contrôle supplémentaire strictement en lecture seule

Le script introduit `--check-mxc-host-environment`. Cette option **n'invoque ni Codex ni MXC**, ne crée aucun fichier ni processus. Elle teste seulement l'existence des variables **`SystemDrive`**, **`LOCALAPPDATA`** et **`SystemRoot`** dans l'environnement du processus Python ; aucune valeur personnelle n'est affichée. Le transport MXC épinglé [`mxc-sandbox/src/transport.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/transport.rs) exige notamment les deux premières variables d'hôte, et `SystemRoot` peut être nécessaire pour le comportement du profil enfant. `required_mxc_transport_host_env_present` couvre uniquement `SystemDrive` et `LOCALAPPDATA`. Si elles manquent, le lanceur existant en mode réel refuse désormais l'essai avec `MXC_HOST_ENV_REQUIRED_MISSING` avant d'invoquer Codex ; **il ne les invente pas et ne modifie pas l'environnement ni la configuration Windows**.

La classification `stderr` est complétée **sans jamais relâcher le STOP sur tout avertissement** : des messages correspondant exactement à des étapes officielles deviennent des codes fixes, par exemple `MXC_INVALID_LAUNCHER_REQUEST`, `MXC_ENV_UNICODE_INVALID`, `MXC_WINDOWS_VOLUME_ERROR`, `MXC_PLATFORM_DIRECTORY_ERROR`, `MXC_COM_INIT_ERROR`, `MXC_DENY_PATHS_UNAVAILABLE`, `MXC_CHILD_WAIT_ERROR` et `MXC_LAUNCHER_FAILURE` générique si rien de plus précis n'est connu. Aucun texte d'erreur brut, chemin, HRESULT, secret, ID ou argument ne doit être renvoyé.

**Décision :** la prochaine opération locale sera **exclusivement `--check-mxc-host-environment`**, après mise à jour et tests hors modèle. Un succès confirme des prérequis d'environnement, **pas la disponibilité de l'API MXC**. Si ces prérequis sont présents et que la catégorie générique persiste ultérieurement, envisager une lecture d'erreur locale limitée et contrôlée par l'opérateur, au lieu de répéter les essais ou de désactiver les protections. PR #14 ouverte, A/B non autorisés.

## Host prerequisites PASS, but `SystemDrive` dropped from isolated process (29 October 2026)

The operator's latest **read-only** host transport check on main `885f640385bdff490588aa4deb0c46eecf4ed13d` established **46/46** launcher synthetic tests PASS, and:
- `system_drive_present=true`, `local_app_data_present=true`, `system_root_present=true`;
- `required_mxc_transport_host_env_present=true`, `processes_launched=0`, `model_calls_made=0`;
- `mxc_native_capability_verified=false`, `standalone_mxc_runtime_verified=false`, `appserver_turn_mxc_verified=false`.

These booleans describe the **parent Python process environment**. They do **not** show what the **isolated child Codex CLI process** received. Reviewing the actual source identified a concrete missing transport prerequisite: `scripts/Probe-CodexAB-AppServerH1.py` `SAFE_ENV` intentionally permits `LOCALAPPDATA` and `SYSTEMROOT` but **omits `SYSTEMDRIVE`**; H1.3 previously used `h1.env_for_isolated_home(home)` directly in both the compatibility-only and filesystem-test paths. The pinned upstream [`codex-rs/mxc-sandbox/src/transport.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/transport.rs) explicitly requires a nonempty host `SystemDrive` at launcher transport construction, along with `LOCALAPPDATA`.

This is a **real defect in the local environment-building contract**, although it is **not proven** to be the root cause of the prior broad `COMPAT_STDERR_PRESENT:MXC_LAUNCHER_FAILURE`: that prefix comes from the helper after dispatch, and the unlogged underlying error is unknown.

### Narrow correction, H1.3 only

- Introduce `mxc_env_for_isolated_home(home, source)` **only in H1.3**, reusing the existing H1 safe filtered environment and injecting **exactly one** additional host variable, `SystemDrive`, after verifying it has the canonical drive-letter format `X:`. Do **not** modify `SAFE_ENV`, the H1/H1.2 probes, global Windows variables, real Codex profiles or token stores.
- Reject a missing or malformed `SystemDrive` before any Codex subprocess, and reject missing `LOCALAPPDATA` in the **isolated child**. Do not guess or substitute a system drive or add broad profile variables.
- Add `system_drive_format_valid` to the read-only host report; report only booleans, never variable values. `required_mxc_transport_host_env_present` retains its existing presence-only semantics.
- Use the same vetted H1.3-only isolated environment in both the **single-shot compatibility** and gated filesystem negative test modes, with no changes to their sandbox permissions or fail-closed stderr handling.
- Fake-only tests verify all new environment invariants, reject invalid values and ensure only one additional key is passed. **No native MXC execution occurs in CI.**

**Next evidence needed:** after full CI PASS, a **single explicit** local compatibility-only attempt can determine whether this omission affected startup. If another `MXC_LAUNCHER_FAILURE` occurs, STOP; do **not** make more speculative environment changes. Move instead to a privacy-controlled local examination of the original SDK error content, without copying sensitive output into GitHub or chat. H1.3 filesystem isolation, app-server parity, network and worker attestations remain not verified; the PR #14 stays open and A/B model calls are not authorized.

## Sixième H1.3a — compatibility echo succeeded but warning remains (29 October 2026)

The operator ran main `740d76356bb3d541353c882b3c935eb644f5fdef` after PR #83: **52/52** fake H1.3 launcher tests PASS, then the *single real compatibility command* produced:
`STOP: H13_STANDALONE_MXC_FAILED:COMPAT_STDERR_PRESENT:GENERAL_WARNING:MARKER_PRESENT:EXIT_ZERO`.

This is the **first observed success of the expected exact `MXC_OK` marker with process exit code 0**, after H1.3 restored the upstream-required `SystemDrive` to the disposable CLI environment. The prior error `MXC_LAUNCHER_FAILURE:MARKER_ABSENT:EXIT_NONZERO` did **not** recur. This temporal correlation suggests (but does not prove) that the missing variable caused some of the earlier launch failures. Crucially **stderr is still nonempty** and its exact content was never recorded; the existing strict probe correctly remains **STOP**. No filesystem negative test was run. **Do not mark OS MXC enforcement, network isolation, or app-server turn parity verified.**

### One-shot LOCAL screen-only inspection — separate opt-in script

The independent `scripts/Review-CodexAB-H13MXC-Warning.py` defaults to a no-process plan. Its separate explicit option `--execute-one-private-local-review` repeats **one** sandbox compatibility echo only, using all existing nonadmin/pinned-version/Windows-build checks, a new disposable `CODEX_HOME`, and the validated H1.3 `SystemDrive` child environment. No filesystem canary, model, turn, worker or A/B is involved.

- If stderr remains nonempty (bounded to 8192 bytes), the script shows **only on the local interactive Windows desktop**, in a modal `MessageBoxW`, the exact stderr for **the user's own private review**. The raw text is **not printed into PowerShell**, written to a file, committed, uploaded to Github, or sent to a server by the script. It may contain paths, usernames, secrets or device-specific configuration. **Do not screenshot or paste that window into the conversation.**
- After closing the local warning window, only a *fixed classification and status* appear in PowerShell, always with `LOCAL_WARNING_REVIEWED_STILL_STOP` and exit code **2** for nonempty stderr, **even if `MXC_OK` and exit code 0 were observed**. The user can describe the warning's general meaning without exposing raw values.
- If no stderr is produced, the unchanged strict exact `MXC_OK`/exit 0 gate may report `MXC_COMPAT_ECHO_PASS_NO_WARNING_NOT_ENFORCEMENT`. That is still not a filesystem sandbox proof.
- The message box is used instead of saving raw stderr to disk or risking accidental copy/paste of unfiltered console logs. There are no prompts for administrative rights, config changes, or permissions; closing the message box merely acknowledges local review.
- CI tests use only fake subprocess outputs and mocked dialogs, on Windows and Ubuntu; no real Codex or native sandbox is started in CI.

After this private review, identify the *source and severity* of the exact warning before considering a constrained allowlist. **Never globally ignore stderr, suppress warning generation, disable MXC or degrade the sandbox.** If warning content is sensitive, report only its generic category; in that case H1.3a may remain blocked pending a safely testable diagnostic.

## Source du warning MXC identifiée : garde de sécurité `arg0` (29 octobre 2026)

L'opérateur a lu l'avertissement sur son bureau Windows après l'essai réel `4b75cd6eca605606a9437d5c5a2a84dd9c80a50f`: **52/52** tests synthétiques PASS, `MXC_OK` présent, exit code **0**, mais `GENERAL_WARNING` sur stderr donc STOP strict. Le texte (reproduit ici **uniquement sous forme paraphrasée sans aucun chemin personnel**) dit que Codex poursuit sans pouvoir créer ses alias PATH : les exécutables auxiliaires sont volontairement interdits sous un dossier temporaire système.

La cause de **cet avertissement précis** est démontrée dans le code officiel épinglé [`openai/codex rust-v0.165.0 codex-rs/arg0/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/arg0/src/lib.rs) :
- `prepare_path_entry_for_codex_aliases` lit `find_codex_home()`, puis refuse de placer les binaires auxiliaires lorsque `codex_home.starts_with(std::env::temp_dir())`, avec un message `Refusing to create helper binaries under temporary dir`.
- Le gestionnaire d'erreur `prepare_path_env_var_with_aliases` émet `WARNING: proceeding, even though we could not create PATH aliases` et continue. Cet avertissement est donc **une protection voulue**, pas une raison de la supprimer.
- Les lanceurs H1.3a précédents créaient `CODEX_HOME` au moyen de `tempfile.TemporaryDirectory(...)` sans `dir`, ce qui plaçait le profil **sous le TEMP système**, satisfaisant exactement la condition de refus. C'est un défaut de choix de chemin propre à notre probe, désormais vérifié.
- La réussite du marqueur `MXC_OK` / exit 0 ne prouve **toujours pas** l'isolement des fichiers, du réseau, des workers ou d'un `turn/start`.

### Correctif structurel H1.3a : dossier jetable utilisateur HORS TEMP système

Le helper `validate_disposable_parent` / `disposable_probe_root` choisit maintenant le dossier de profil utilisateur **en dehors de l'arbre TEMP système résolu** et refuse les répertoires manquants, non-répertoires, parent symbolique ou imbriqué dans TEMP. Il crée un répertoire aléatoire **neuf** sous ce dossier, et y place `codex-home` et `workspace`. Le répertoire et tous ses fichiers sont ensuite nettoyés via `TemporaryDirectory`, sans jamais réutiliser le vrai dossier `~/.codex`, le contenu utilisateur existant ou un autre projet.

Le correctif s'applique de manière cohérente aux modes `--execute-local-mxc-compat-only`, `--execute-local-mxc-probe` et au diagnostic privé `Review-CodexAB-H13MXC-Warning.py`. Il **ne change pas** les politiques de permissions, le profil `:workspace`, `windows.sandbox=mxc`, les appels modèles, la garde `arg0`, les variables Windows globales ou les probes H1.1/H1.2.

Aucune exception générale de stderr ou d'avertissement n'a été ajoutée : toute erreur et tout warning restent **STOP**. Les nouveaux tests synthétiques garantissent la séparation des chemins temporaires, le nettoyage des nouveaux répertoires, l'absence de suppression de la garde et la portée strictement H1.3.

**Étape suivante** : après CI Windows/Ubuntu/PowerShell PASS, une nouvelle tentative unique **compatibilité-only**, non-admin, épinglée sur le commit fusionné, pourra établir si `MXC_OK` est désormais obtenu sans cet avertissement. Aucune exécution du canary d'écriture, aucune vérification réseau ou tour IA à cette étape. H1.3a effectivité du confinement encore NON QUALIFIÉE, PR #14 ouverte, A/B non autorisés.
