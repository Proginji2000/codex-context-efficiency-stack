# Passation opérationnelle — Codex Stack IA & Autonomie — 1 novembre 2026

**État fondé sur les sorties PowerShell communiquées par l'opérateur ; aucune connexion distante au PC.** Historique détaillé : [passation du 31 octobre](CODEX_STACK_HANDOFF_2026-10-31.md), [roadmap](QUALIFICATION_ROADMAP_2026.md), [broker V2](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

## 1 novembre 2026 — device auth ChatGPT Codex réussi sous codex-runner (dernier résultat)

L'opérateur a sélectionné explicitement `CODEX_HOME` dans `%LOCALAPPDATA%\CodexSM-Synthetic-0165` depuis la session `codex-runner` puis exécuté `C:\ProgramData\CodexRunnerCLI-0165\bin\codex.exe login --device-auth`. Le terminal affiche `Successfully logged in` et `codex login status` confirme `Logged in using ChatGPT`. L'option de connexion par code d'appareil a dû être activée préalablement dans les paramètres ChatGPT. **Aucun code temporaire, adresse e-mail ni jeton n'est conservé dans cette passation.**

**Jalon :** authentification ChatGPT indépendante établie dans le profil Codex du runner. Pas d'appel modèle ni d'appel MCP depuis Codex dans le transcript de connexion. Le terminal peut ouvrir une requête modèle dès le prochain `codex exec`; cela utilisera le quota du compte. Ne pas recopier le fichier `auth.json` ni le transmettre. Aucun droit de lire les fichiers broker ou clé production n'a été octroyé au runner.

**Prochain et unique canary autorisé :** redémarrer sous `codex-broker` le service HTTP synthétique `C:\ProgramData\CodexMemoryBrokerStage-V2\app\BrokerSyntheticServer.ps1` (faux jeton, faux upstream, `127.0.0.1:6811`, auto-stop 600s), puis lancer depuis `codex-runner` **un seul** `codex exec` avec `CODEX_HOME` isolé, sandbox `read-only`, approbations `never`, espace de travail jetable dédié, `--json`, et une instruction explicite `sm_synthetic.search(query="synthetic probe")` sans shell ni autre outil. La réussite nécessite **un événement JSON `item.completed` avec `item.type=mcp_tool_call`, `server=sm_synthetic`, `tool=search`, `status=completed` et résultat `mcp-cross-account-synthetic`** ; ne pas qualifier sur la seule affirmation du modèle. Si le serveur manque ou outil annulé, STOP et consigner BLOCKED. Aucun Supermemory réel, Docker, profil opérateur ou accès production.

## 1 novembre 2026 — profil Codex CLI isolé + MCP synthétique enregistré : PASS (dernier résultat)

L'opérateur a exécuté le script PowerShell **V2** sous l'identité réelle `codex-runner`. Le premier essai s'était arrêté AVANT création de profil à cause de l'emploi de la variable PowerShell protégée `$home` (alias insensible à la casse de `$HOME`), corrigé en `$isolatedCodexHome` sans changer le comportement de sécurité.

Dernière sortie effective : `RUNNER_CODEX_AND_BRIDGE_INTEGRITY_PASS`, `ISOLATED_CODEX_HOME_CREATED_PASS`, `ISOLATED_MCP_REGISTERED_PASS`, `ISOLATED_MCP_CONFIG_VERIFIED_PASS`, `CODEX_RUNNER_SYNTHETIC_MCP_CONFIG_PASS`, `NO_AUTH_OR_MODEL_CALLS`, `NO_PRODUCTION_KEYS_USED`.

**Acquis :** profil séparé `%LOCALAPPDATA%\\CodexSM-Synthetic-0165` sous le **compte runner**, activé par `$env:CODEX_HOME` dans la session ; entrée MCP stdio `sm_synthetic` enregistrée via `codex mcp add`, correspondant au Python embarqué `C:\ProgramData\CodexMemoryPython314\python.exe` et au pont `C:\ProgramData\CodexMemoryMcpStage-V2\mcp_readonly_bridge.py` dont l'empreinte SHA256 a été vérifiée. `codex mcp get ... --json` et `mcp list --json` ont réussi. Le jeton sous `synthetic-token.txt` est **fictif et prédéterminé**, jamais utilisable en production. Pas de copie du `.codex` ni d'authentification du compte principal, pas d'appel de modèle.

**Limite :** validation de **configuration déclarative uniquement** ; pas encore de démarrage MCP par `codex exec`, ni d'appel effectif à `search` par un agent. Le test synthétique intercomptes direct (hors Codex) reste PASS. Le profil `CODEX_HOME` doit être sélectionné explicitement dans toute nouvelle session PowerShell sous runner, par exemple `$env:CODEX_HOME = Join-Path $env:LOCALAPPDATA 'CodexSM-Synthetic-0165'` ; ne pas lancer Codex depuis le profil principal.

**Prochain gate :** contrôler localement `codex login status` avec le `CODEX_HOME` isolé, puis si absent procéder à une authentification volontaire **indépendante** via `codex login --device-auth`, sans copier de tokens. N'effectuer un premier vrai `codex exec` que sur le serveur HTTP **synthétique** `codex-broker`, avec sandbox read-only, approbations désactivées, workspace vierge, appel explicite `sm_synthetic.search(query='synthetic probe')` et aucune écriture, Docker ou clé Supermemory. Le démarrage d'un modèle Codex consommera éventuellement du quota ; ne pas le confondre avec le canary live Supermemory (non autorisé/qualifié).

## 1 novembre 2026 — Codex CLI 0.165.0 sous codex-runner : PASS (dernier résultat)

L'opérateur a exécuté `Install-CodexRunnerCLI-0165-20261101.ps1`, SHA256 `D31F77A5901B932735A1718387695D0DB03AC9BF28CA43A48053CC784AB59026`, et a confirmé `INSTALLER CODEX RUNNER`. Les marqueurs sont : `CODEX_RUNNER_INSTALL_SCRIPT_INTEGRITY_PASS`, `CODEX_RUNNER_CLI_PREFLIGHT_PASS`, `CODEX_RELEASE_SHA256_PASS`, `CODEX_RUNNER_CLI_PROTECTED_STAGE_PASS`, `CODEX_RUNNER_CLI_VERSION_0165_PASS`, `NO_AUTH_OR_MCP_CONFIG_CHANGED`, `CODEX_RUNNER_CLI_STAGE_COMPLETE`, `CODEX_RUNNER_INSTALL_SCRIPT_EXECUTION_COMPLETE`. Vérification distincte de l'exécutable via PowerShell : `& 'C:\ProgramData\CodexRunnerCLI-0165\bin\codex.exe' --version` → `codex-cli 0.165.0`.

**Acquis :** executable officiel versionné dans staging ProgramData protégé, permissions de lecture/exécution pour `codex-runner`, CLI fonctionnel sans changement de PATH, login, config MCP, Docker, service ou environnement principal. Ce test ne prouve pas que Codex est connecté à ChatGPT, qu'un modèle peut s'exécuter, ou qu'une requête MCP a été émise *depuis Codex CLI*. Le préflight précédent `RUNNER_CODEX_CLI_NOT_FOUND` est clos. Le broker + MCP intercomptes en dehors du CLI restent synthétiquement PASS.

**Prochain gate sans appel de modèle :** créer depuis le vrai `codex-runner` un répertoire `CODEX_HOME` propre et nouveau dans son `LocalAppData` ; enregistrer uniquement le serveur stdio `sm_synthetic` avec `codex mcp add sm_synthetic --env BROKER_CLIENT_TOKEN_FILE=<chemin du jeton **fictif**> -- C:\ProgramData\CodexMemoryPython314\python.exe -I -B C:\ProgramData\CodexMemoryMcpStage-V2\mcp_readonly_bridge.py`. Fichier jeton fictif stocké seulement sous ce profil. Confirmer `codex mcp get sm_synthetic --json` et `codex mcp list --json`; aucun `codex exec`, modèle, `login`, secret Supermemory réel ou copie de `.codex` de l'opérateur. La réussite est une **configuration déclarative**, non une connexion réelle Codex/MCP. Le serveur synthétique existant peut rester arrêté.

## 1 novembre 2026 — Codex CLI absent du compte restreint (dernier contrôle)

Après reconfirmation `MCP_BROKER_CROSS_IDENTITY_SYNTHETIC_PASS`, l'opérateur a exécuté sous la véritable identité `codex-runner` un préflight `Get-Command codex -All` / `--version` sans appel de modèle. Sortie : `RUNNER_IDENTITY_PASS`, `RUNNER_CODEX_CLI_NOT_FOUND`, `NO_CONFIG_CHANGED`, `NO_MODEL_CALLS`, `RUNNER_CODEX_PREFLIGHT_COMPLETE`.

**Interprétation :** Codex CLI n'est pas trouvable comme application/script par la recherche de commande dans cet environnement Windows. Ne pas le confondre avec un échec MCP ou ACL et ne pas réutiliser implicitement le CLI, le profil `.codex`, la connexion ChatGPT, les secrets ou les dépendances installés sous le compte opérateur.

**Prochain livrable préparé, NON exécuté sous Windows :** fichier local de conversation `Install-CodexRunnerCLI-0165-20261101.ps1` SHA256 `D31F77A5901B932735A1718387695D0DB03AC9BF28CA43A48053CC784AB59026`. Télécharge depuis la release GitHub **officielle OpenAI** `rust-v0.165.0` le paquet x64 Windows `codex-package-x86_64-pc-windows-msvc.tar.gz`, avec hash officiel déjà épinglé par Scoop `2A64BEB5856C3170738793E0AA65B44AA3F2D7B8F53221A3F72BDAFE6485D119` ; vérifie avant décompression. Demande confirmation opérateur `INSTALLER CODEX RUNNER`. Stage uniquement un nouveau `C:\ProgramData\CodexRunnerCLI-0165` sous ACL non héritées SYSTEM/Administrateurs FullControl et `codex-runner` ReadAndExecute ; aucun autre compte ni PATH ni profil Codex modifié. Vérifie `bin\codex.exe --version` 0.165.0, nettoie le téléchargement et supprime le seul stage nouveau en cas d'échec. Pas de configuration MCP/auth et aucun appel modèle ; **le PowerShell de stage n'a pas été exécuté sur le poste**.

**Après stage :** depuis `codex-runner`, exécuter uniquement `C:\ProgramData\CodexRunnerCLI-0165\bin\codex.exe --version` et rapporter `RUNNER_CODEX_VERSION_0165_PASS`. Ne pas encore faire de login, accepter une approbation réseau, activer des hooks globaux, ni copier auth.json/config.toml du compte opérateur. Ensuite travailler la connexion MCP dans un profil indépendant sous `codex-runner`, avec serveur broker encore synthétique ; secrets réels uniquement après durcissement du broker.

## 1 novembre 2026 — chaîne MCP intercomptes synthétique PASS (dernier résultat)

Sortie fournie par l'opérateur depuis **PowerShell `codex-runner`** après préparation du kit intercomptes et lancement du broker synthétique `codex-broker` :

```text
MCP_RUNNER_IDENTITY_PASS
MCP_BRIDGE_SOURCE_INTEGRITY_PASS
MCP_INITIALIZE_PASS
MCP_READONLY_TOOLS_PASS
MCP_SEARCH_THROUGH_BROKER_PASS
MCP_WRITE_TOOL_DENIED_PASS
MCP_BROKER_CROSS_IDENTITY_SYNTHETIC_PASS
NO_PRODUCTION_KEYS_OR_SUPERMEMORY_CALLS
RUNNER_MCP_SYNTHETIC_TEST_COMPLETE
```

**Conclusion :** la chaîne **pont MCP stdio sous codex-runner → broker HTTP localhost sous codex-broker → upstream fictif** a fonctionné, avec rejet d'outil d'écriture, sans clé Supermemory ou appel de production. Le pont V2 n'offre que `search(query)`; aucune connexion **Codex CLI** au pont, aucun vrai moteur Supermemory et aucun service broker durable n'ont été qualifiés. La sortie du lancement du serveur synthétique et du staging administratif n'est pas dans ce dernier message, mais le succès du test MCP atteste qu'un serveur compatible était accessible.

**Jalon clos :** tests ACL des deux comptes, broker HTTP synthétique Windows et MCP intercomptes synthétique. **Ne plus rejouer ces validations sur code inchangé.**

**Suite de qualification :** durcir le serveur V2 avant tout secret réel (concurrence de requêtes/connexions limitée, timeout client, arrêt supervisé, journalisation sans secrets), isoler le stockage des clés Supermemory **uniquement côté broker** (runner n'aura qu'un jeton local limité), puis vérifier cette séparation avec jetons factices et tests d'accès négatifs. Ensuite, premier canary réel sur **namespace synthétique dédié** (aucune donnée privée) `codex_llm_canary_c58e251be7bf`, suivi de l'intégration au Codex CLI sous `codex-runner` ; ne jamais donner la clé API production à Codex. Le broker actuel reste un prototype et n'a pas été démarré avec le secret réel.

## 1 novembre 2026 — broker HTTP synthétique Windows PASS (dernier résultat)

L'opérateur a démarré le **véritable** `C:\ProgramData\CodexMemoryBrokerStage-V2\app\broker.py` avec l'interpréteur CPython embedded `C:\ProgramData\CodexMemoryPython314\python.exe` sous l'identité `codex-broker`. Empreinte source préalablement vérifiée (`BROKER_CODE_INTEGRITY_PASS`). Serveur lié à `127.0.0.1` sur un port éphémère et upstream simulé en mémoire : `BROKER_SYNTHETIC_AUTHORIZED_SEARCH_PASS` (200), `BROKER_SYNTHETIC_INVALID_TOKEN_PASS` (401), `BROKER_SYNTHETIC_METHOD_DENY_PASS` (405), `BROKER_SYNTHETIC_NAMESPACE_OVERRIDE_DENY_PASS` (400), `BROKER_SYNTHETIC_HTTP_PASS`, `NO_PRODUCTION_KEYS_OR_API_CALLS`, `BROKER_SYNTHETIC_TEST_COMPLETE`.

**Décision :** blocage Python Store résolu par interpréteur autonome, et **qualification du broker HTTP synthétique sous l'identité Windows dédiée terminée**. Pas de clé API Supermemory de production, aucune recherche vraie, aucun service permanent, ni Codex CLI pendant ce test. Les validations ACL de `codex-broker` et `codex-runner` restent acquises (cf. section précédente). Le prototype HTTP V2 reste à durcir avant emploi d'un secret réel (concurrence non bornée, timeouts, service lifecycle et token custody).

**Prochain jalon — vraie chaîne cross-account MCP, toujours synthétique :** artefact de conversation `Codex_Supermemory_MCP_CrossAccount_Synthetic_20261101.zip`, SHA256 `7A33D857EFFF7F294EE8F8D491C7ECBDF0C3FBBF5BC1A07EFB55C81EADE00E30`. Inclut un script de stage privilégié à confirmation `PREPARER MCP SYNTHETIQUE`, le `mcp_readonly_bridge.py` **identique au ZIP V2** (SHA256 `69D7A984EE48F39C57819CCC6E98D27CB60A1FF2E582099B94A9898191329A79`), et deux lanceurs de test à exécuter séparément par `codex-broker` (serveur localhost:6811 upstream fictif, auto-stop 10 min) et `codex-runner` (MCP stdio subprocess, fichier jeton fictif temporaire). Le script admin ne modifie que l'ACE RX du runner sur le Python embedded, crée `%ProgramData%\CodexMemoryMcpStage-V2` protégé avec code MCP RX pour runner, et place un lanceur factice à côté de broker.py. **N'exécute aucune clé, service, Docker ni Codex.** Vérifié : parsing Python et intégration MCP→broker simulée **PASS dans le conteneur d'essai** ; kit staging PowerShell **non encore exécuté ou certifié sur Windows**. À exécuter uniquement avec consentement administrateur et rollback documenté.

Ne pas répéter les tests précédents. Après `MCP_BROKER_CROSS_IDENTITY_SYNTHETIC_PASS` sous Windows seulement, passer au durcissement du broker et à l'architecture des deux jetons pour la première requête réelle Codex→Supermemory.

## 1 novembre 2026 — les DEUX identités ACL PASS, test broker HTTP Windows BLOCKED par Python Store

L'opérateur a exécuté le contrôle de non-régression sous `codex-runner` : `ROOT_LIST=DENIED_PASS`, `CODE_READ=DENIED_PASS`, `CODE_WRITE=DENIED_PASS`, `SECRETS_LIST=DENIED_PASS`, `RUNNER_ACL_REGRESSION_PASS`, `NO_FILES_MODIFIED`.

Le contrôle effectif `codex-broker` est à nouveau confirmé : `ROOT_LIST=ALLOWED_PASS`, `CODE_READ=ALLOWED_PASS`, `CODE_WRITE_HANDLE=DENIED_PASS`, `SECRETS_LIST=DENIED_PASS`, `BROKER_EFFECTIVE_ACL_PASS`, `NO_FILES_MODIFIED`, `NO_SECRET_CONTENT_READ`.

**Jalon ACL deux comptes clos. Ne pas répéter ces tests sans changement d'ACL.**

Tentative suivante : test serveur HTTP synthétique du vrai `broker.py` sous `codex-broker`, avec `py.exe -3 -B -`. **BLOCKED avant exécution Python :** `Unable to create process using ... C:\Program Files\WindowsApps\PythonSoftwareFoundation.Python.3.13_...\python3.13.exe -B - : Accès refusé`. `BROKER_SYNTHETIC_HTTP_FAILED`. Aucun `BROKER_SYNTHETIC_HTTP_PASS` Windows, aucun serveur HTTP démarré, aucun secret réel ou accès à Supermemory. Cause observée : lanceur Python Microsoft Store résout vers un exécutable WindowsApps non exécutable par le compte distinct `codex-broker`; **ne pas desserrer les ACL WindowsApps ni copier le profil Python de l'opérateur.** Le même scénario de test, exécuté séparément dans le conteneur de l'assistant contre le véritable `broker.py` du ZIP V2, confirme les statuts HTTP `200,401,405` et une unique recherche simulée ; cela ne remplace pas le test Windows.

**Correctif d'environnement proposé, pas encore exécuté :** un Python CPython **3.14.10** 64-bit *embeddable* officiel python.org déployé dans `%ProgramData%\\CodexMemoryPython314`, répertoire isolé à ACL protégées avec compte opérateur/SYSTEM/Administrateurs FullControl et `codex-broker` ReadAndExecute, sans droits runner, sans changement PATH, registre, service, Python Store ni configuration Codex. ZIP fournisseur vérifié SHA256 `90905E64A840557D8C1BC4F5B74DB3D7EE85E3FFB217611CAC1C7813ACEA4159` d'après https://www.python.org/downloads/release/python-31410/ (publication du 25 octobre 2026). Script local de la conversation `Install-CodexBrokerPortablePython-20261101.ps1`, SHA256 `21A343C7E44215E9B357BA436276C9BF870626D373A3441AC792F94DF1316736`, **préparé statiquement et non encore exécuté/qualifié sous Windows**. Action volontaire : confirme `DEPLOYER PYTHON BROKER`, télécharge uniquement depuis python.org, vérifie le hash avant extraction, crée le nouveau dossier sous ACL contrôlées, vérifie les imports stdlib, rollback du nouveau dossier sur échec. Exécution du script avec élévation explicite opérateur. Pas de clé production ni de réseau Supermemory.

**Prochain gate :** `BROKER_PYTHON_EMBED_RUNTIME_READY` depuis compte opérateur, puis test de lancement réel `%ProgramData%\\CodexMemoryPython314\\python.exe` sous `codex-broker` et reprise du canary HTTP synthétique avec cet exécutable explicite. Pas de boucle de préflight / tests ACL. Le Python embarqué restant sans pip, il sert uniquement au broker stdlib; les questions de service, secrets et durcissement restent ouvertes.

## 1 novembre 2026 — ACL lecture seule codex-broker appliquée au staging (dernier résultat)

L'opérateur a exécuté en PowerShell élevé `Grant-CodexBrokerStageReadOnly-20261101.ps1` après vérification SHA256 `64A5D4C31C1D7B9E5B7A143CFB2612D1B3D48A1E2B3AC31E47C3B1048D7324EB` et confirmation explicite `AUTORISER LECTURE BROKER`. Sorties : `BROKER_ACL_SCRIPT_INTEGRITY_PASS`, `BROKER_STAGE_ACL_PREFLIGHT_PASS`, `BROKER_STAGE_ROOT_READONLY_ACE_PASS`, `BROKER_STAGE_APP_READONLY_ACE_PASS`, `BROKER_STAGE_SECRETS_UNCHANGED_PASS`, `NO_CODE_OR_SECRET_CONTENT_MODIFIED`, `NO_SERVICE_OR_PRODUCTION_API_CHANGED`, `BROKER_STAGE_BROKER_ACL_APPLIED`.

**Portée :** la racine `C:\ProgramData\CodexMemoryBrokerStage-V2` et `app` portent désormais les ACE de lecture/exécution attendues pour `codex-broker` ; l'ACL de `secrets-empty` n'a pas été changée. Aucun secret, service Windows, code, configuration MCP ou API de production modifié. **Cela prouve l'application des ACE, pas encore les droits effectifs sous le jeton `codex-broker` ; ne pas supposer l'accès à `secrets-empty` définitivement refusé sans test sous cette identité.**

**Prochain gate unique :** ouvrir un PowerShell sous `codex-broker` avec `runas`, puis vérifier un `File.Open` en lecture (attendu accordé), en écriture sans mutation (attendu refusé) sur `app\broker.py`, ainsi que l'énumération de `secrets-empty` (attendu refusée). Après changement d'ACL, vérifier également que `codex-runner` reste sans lecture du code. Aucun jeton, clé réelle, service ou agent Codex n'est nécessaire. Suivant ces tests, concevoir des secrets séparés et une exploitation de service durcie : le broker V2 reste un prototype hors ligne.

## 1 novembre 2026 — codex-broker créé, provisionnement V2 PASS (dernier résultat)

L'opérateur a lancé `Provision-CodexBrokerIdentity-V2-20261101.ps1` après vérification SHA256 `6E8EFDC03D39D6F5C8C2FC4DF72930C1AF0CC76170EB1EEEC77B9365E4345991`, a confirmé `CREER CODEX-BROKER` et saisi localement un mot de passe SecureString (minimum **16** caractères contrôlé par le script). Marqueurs : `BROKER_IDENTITY_V2_INTEGRITY_PASS`, `BROKER_IDENTITY_PREFLIGHT_PASS`, `BROKER_IDENTITY_CREATED_PASS`, `BROKER_IDENTITY_USERS_ONLY_DIRECT_PASS`, `BROKER_IDENTITY_NO_ADMIN_DIRECT_PASS`, `BROKER_IDENTITY_NO_DOCKER_DIRECT_PASS`, `NO_SERVICE_OR_SECRET_CONFIGURED`, `BROKER_IDENTITY_PROVISIONING_COMPLETE`, `BROKER_IDENTITY_V2_EXECUTION_COMPLETE`.

**Résultat :** compte local standard dédié `codex-broker` créé et distinct de `codex-runner`. Appartenance directe Users vérifiée ; pas d'appartenance directe Administrators/docker-users. **Pas encore de session `runas` sous ce compte, pas de preuve de jeton effectif ni d'autorisation ACL, pas de clé ou service.** L'échec antérieur V1 dû à la description de 61 caractères est clos. Les validations `BROKER_STAGE_RUNNER_ACL_DENIAL_PASS` et 24/24 tests Windows offline restent acquises et ne doivent pas être relancées sans changement d'ACL/code.

**Préparation de la prochaine étape (pas encore exécutée sous Windows) :** artefact local de cette conversation `Grant-CodexBrokerStageReadOnly-20261101.ps1`, SHA256 `64A5D4C31C1D7B9E5B7A143CFB2612D1B3D48A1E2B3AC31E47C3B1048D7324EB`. Script PowerShell 5.1 à exécuter sous compte opérateur élevé avec confirmation `AUTORISER LECTURE BROKER`. Vérifie identité/groupes/staging vide de secrets, puis accorde à `codex-broker` ReadAndExecute **sans héritage sur la racine**, ReadAndExecute **héritable uniquement sous `app`**, et aucun accès au répertoire `secrets-empty`. Les deux ACL initiales sont mémorisées en mémoire pour rollback en cas d'échec. Aucun fichier code, clé, secret, service ou configuration MCP modifié. **Contrôle statique uniquement dans la session assistant ; ne pas prétendre un PASS Windows avant la sortie opérateur.**

**Après application :** vérifier effectivement depuis une session `codex-broker` l'accès en lecture au code et le refus d'accès au dossier de secrets ainsi que le refus d'écriture ; confirmer que `codex-runner` reste sans accès aux fichiers de staging. Ensuite seulement : emplacement permanent dédié de clé et jeton client sous ACL spécifiques, durcissement du service broker et tests sur données synthétiques. Le prototype HTTP V2 (threading illimité) n'est pas prêt pour production.

## Incident création codex-broker — 1 novembre 2026, 14:50 (dernier état)

L'opérateur a exécuté le script initial `Provision-CodexBrokerIdentity-20261101.ps1`, SHA256 vérifiée `AD9F75661A70C13965D093AFC8260F97557C2A38D647E29BBF49C4F4208AEB4B`. `BROKER_IDENTITY_PREFLIGHT_PASS` puis confirmation `CREER CODEX-BROKER` et saisie SecureString. **Échec lors du binding des paramètres de `New-LocalUser`** : la description `Restricted Supermemory broker identity - no service installed` comporte **61 caractères**, et l'implémentation Windows accepte **48 maximum**. Aucun `BROKER_IDENTITY_CREATED_PASS` ni `BROKER_IDENTITY_PROVISIONING_COMPLETE` n'a été émis. Préflight initial avait constaté l'absence de compte ; le binding d'arguments a échoué avant la création ; **vérifier à nouveau l'absence du compte avant retry**. Pas de modification volontaire des ACL, services ou secrets.

**Correctif minimal V2 préparé et non encore exécuté sur Windows :** `Provision-CodexBrokerIdentity-V2-20261101.ps1`, SHA256 `6E8EFDC03D39D6F5C8C2FC4DF72930C1AF0CC76170EB1EEEC77B9365E4345991`. Différence unique vérifiée statiquement : description abrégée `Supermemory broker - no service installed` (**41 caractères**). Le mot de passe SecureString, la confirmation interactive, les conditions Admin/Users/docker-users et le rollback restent identiques. La V2 n'est pas un nouveau succès de provisionnement avant la preuve Windows ; l'utilisateur doit exécuter la nouvelle archive uniquement après vérification du SHA256. Le mot de passe de la première tentative ne peut pas être réutilisé automatiquement.

**Prochain jalon :** `BROKER_IDENTITY_PROVISIONING_COMPLETE` avec compte local standard et groupes directs vérifiés. Aucun service, API réelle, clé, MCP ou modification de production ne doivent être entrepris avant la qualification séparée du compte et des ACL.

## Validations acquises — ne pas rejouer sans modification de code

- Supermemory Local Docker v0.0.9 healthy, sauvegarde/restauration V5 PASS ; BGE-M3 provider local/Xenova/bge-m3/1024 confirmé ; inférence directe Ollama qwen3:8b PASS.
- Document de canary synthétique dans `codex_llm_canary_c58e251be7bf` indexé, **3 mémoires extraites** et disponibles ; les trois POST Ollama observés n'attestent pas encore leur modèle/attribution exacte ni l'absence de fallback cloud.
- Adaptateur MCP Python direct, lecture seule `search`, PASS hors Codex ; branche locale non poussée `codex/supermemory-local-adapter-20261030` HEAD `e4fd34e`. Ne pas l'écraser par synchronisation forcée.
- Broker HTTP de lecture seule + pont MCP V2 : **24 tests unitaires PASS sous Windows PowerShell 5.1**, archive `Supermemory_Readonly_Broker_MCP_Offline_V2_20261031.zip`, SHA256 `A0A40F07D0C4272647D54E3839A5163067BE48ACF5F9D509C07B8165FDD811B5`. Aucun secret réel ni serveur de production durant ces tests.
- Compte local `codex-runner` créé à la demande expresse de l'opérateur. Jeton réel via runas : pas admin actif, pas membre de docker-users, pas de `SUPERMEMORY_API_KEY` héritée. Deux pipes Docker version ont renvoyé code 1 : **accès non observé**, mais refus ACL Docker non attribué avec certitude.
- Répertoire de staging **code uniquement** `C:\ProgramData\CodexMemoryBrokerStage-V2`, ACL non héritées, dossier `secrets-empty` sans contenu, aucun service ou secret installé. Script `Stage-SupermemoryBrokerV2-Offline.ps1` SHA256 `BFF08C4CECCFE38566F3BA0B4F7C7EB6F31F7BBC35A64EE9A3C82B22A7E86938` a PASS sous Windows.

## Dernier résultat — refus ACL effectif dans codex-runner (1 novembre 2026)

L'opérateur a répété le test de jeton puis exécuté la sonde de répertoire sous une **vraie session Windows codex-runner**. Marqueurs :

```text
RUNNER_IDENTITY_PASS
STAGE_DIRECTORY_LIST=ACCESS_DENIED_PASS
STAGE_BROKER_READ=ACCESS_DENIED_PASS
STAGE_BROKER_WRITE_HANDLE=ACCESS_DENIED_PASS
BROKER_STAGE_RUNNER_ACL_DENIAL_PASS
NO_FILES_MODIFIED
NO_SECRETS_READ
BROKER_STAGE_ACL_TEST_COMPLETE
```

**Décision :** protection effective du **répertoire de staging** contre le runner validée par trois opérations .NET (énumération, ouverture lecture, ouverture écriture sans écrire). Ne pas confondre ceci avec l'isolation de toutes les données du poste ou la sécurité globale du serveur broker. Ne pas répéter les sondes ACL/Docker sans modification. La clé API Supermemory n'a pas été lue par le runner et le broker n'est **pas démarré**.

## Prochaine action proposée : identité de confiance distincte, sans déploiement

Artefact de conversation **préparé, non exécuté sous Windows** : `Provision-CodexBrokerIdentity-20261101.ps1`, SHA256 `AD9F75661A70C13965D093AFC8260F97557C2A38D647E29BBF49C4F4208AEB4B`.

- Nécessite un PowerShell élevé sous l'opérateur et la confirmation exacte `CREER CODEX-BROKER`.
- Crée uniquement un **nouveau compte Windows local standard `codex-broker`**, avec mot de passe unique saisi par SecureString (au moins 16 caractères), membre direct du groupe Users mais non Administrators/docker-users. Vérifie qu'il n'existait pas, puis rollback du compte créé si une étape échoue.
- **Ne change pas** les ACL du staging, les groupes du runner, les services, le réseau, le pare-feu, Docker, les hooks, Codex, l'API ou les secrets Supermemory.
- Compte seul non suffisant : qualification ultérieure de son jeton, ACL attribuées à ce service uniquement, secret dans un emplacement réservé au broker, jeton client limité accessible au pont MCP, tests négatifs depuis l'identité agent, rollback et durcissement HTTP (concurrence/timeout, démarrage service). Le prototype V2 ne doit pas être lancé avec la clé réelle avant ces contrôles.

## Roadmap non close

P1.1 comparaison A/B de AGENTS.md PR #14 toujours ouverte ; P1.2 exposition MCP/quota, P1.4 autocorrection et P2 vrais writers parallèles toujours à qualifier. P3 VM fortement isolée puis P4 accès étendu dans la VM restent futurs. Ne pas confondre prototype Supermemory hors ligne et recherche MCP live par Codex. Aucun autre accès `danger-full-access` au poste Windows n'est autorisé.

## Reprise courte

**Dernier PASS : `BROKER_STAGE_RUNNER_ACL_DENIAL_PASS`.** Prochain jalon **si confirmé/autorisé par l'opérateur** : provisionner la nouvelle identité `codex-broker` sans aucun secret ; ensuite qualifier les ACL et un broker factice avant toute connexion à Supermemory. Ne pas refaire tests V5, embeddings, Qwen3 direct, 24 tests offline, inventaires de comptes ou sondes Docker.
