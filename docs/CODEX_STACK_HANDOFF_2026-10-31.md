# Passation operationnelle — Codex Stack IA & Autonomie — 31 octobre 2026

**Etat rapporte et verifie par sorties de PowerShell fournies dans ChatGPT, non par acces distant au PC.** Ce document prolonge [la passation du 30 octobre](CODEX_STACK_HANDOFF_2026-10-30.md) et la [roadmap](QUALIFICATION_ROADMAP_2026.md), sans remplacer leurs historiques de qualification. Il sert a reprendre le projet apres saturation d'une conversation.

## 1 novembre 2026 — codex-runner : test du jeton effectif et accès Docker négatif observé

L'opérateur a lancé une **nouvelle session PowerShell sous `codex-runner`** via `runas`. Résultats directement fournis : `RUNNER_IDENTITY_PASS`, `RUNNER_NO_ACTIVE_ADMIN_PASS`, `RUNNER_NO_DOCKER_GROUP_PASS`, `RUNNER_NO_INHERITED_API_KEY_PASS`, `DOCKER_PIPE_1_RESULT=1`, `DOCKER_PIPE_2_RESULT=1`, `RUNNER_DOCKER_ACCESS_NOT_OBSERVED`, `NO_MODEL_CALLS`, `NO_SECRET_CONTENT_READ`, `RUNNER_SECURITY_GATE_COMPLETE`.

**Interprétation précise :** le jeton du runner n'est pas élevé et ne porte pas `docker-users`, la clé Supermemory n'est pas héritée, et les deux requêtes `docker version` via les pipes `docker_engine` et `dockerDesktopLinuxEngine` ont échoué. Un code de sortie 1 n'identifie pas à lui seul la cause (ACL vs daemon indisponible/contexte), donc `RUNNER_DOCKER_ACCESS_NOT_OBSERVED` **n'équivaut pas** à un refus ACL prouvé ni à une isolation de sécurité globale. Aucune recherche réelle Codex→broker→Supermemory réalisée, pas de clé transmise à Codex. Les sondes MXC et le banc offline 24/24 sont déjà terminés : **ne pas les relancer**.

**Nouvelle étape de livraison (préparée, pas exécutée sur Windows) :** script conversation `Stage-SupermemoryBrokerV2-Offline.ps1`, SHA256 `BFF08C4CECCFE38566F3BA0B4F7C7EB6F31F7BBC35A64EE9A3C82B22A7E86938`. Stage code uniquement dans `%ProgramData%\\CodexMemoryBrokerStage-V2`, avec ACL non héritées pour opérateur/SYSTEM/Administrateurs, dossier `secrets-empty` vide, SHA256 de l'archive V2 vérifié, aucun service, clé ou réseau. Nécessite élévation et refuse d'écraser un stage existant ; rollback limité au dossier créé. **Statique seulement, test PowerShell Windows pas encore fourni ; ne pas déployer le broker V2 en production** (threading et identité de service non durcis). Après stage, vérifier sous `codex-runner` que le répertoire protégé est inaccessible, puis définir une identité séparée pour le service broker et les secrets avant le canary live.

## 1 novembre 2026 — compte codex-runner cree, verification de privileges requise

L'operateur a execute explicitement le provisionnement Windows du compte local dedie `codex-runner` depuis PowerShell avec privileges administrateur et confirmation `CREER CODEX-RUNNER`. Sorties : `RUNNER_PREFLIGHT_PASS`, `RUNNER_CREATED_PASS`, `RUNNER_USERS_GROUP_PASS`, `RUNNER_NO_ADMIN_DIRECT_PASS`, `RUNNER_NO_DOCKER_DIRECT_PASS`, `RUNNER_PROVISIONING_COMPLETE`. **Le compte existe**, est membre direct du groupe local Users et n'appartient directement ni a Administrateurs ni a docker-users d'apres les controles. Les anciens comptes locaux candidats n'ont pas ete modifies par ce script. Pas de modification Supermemory/Docker ni de lancement Codex.

**Point a retenir :** la condition de longueur du mot de passe a ete modifiee par l'operateur de 16 a 10 caracteres (`if ($password.Length -lt 10)`). Le script ne fournit **aucune preuve de longueur effective** du mot de passe ni de qualite. Si longueur <16, rotation conseillee avec saisie securisee, sans afficher ni transmettre le mot de passe.

**PROCHAIN GATE IMMEDIAT :** `runas /user:<machine>\\codex-runner powershell.exe -NoProfile -NoExit` depuis une console normale, saisie du mot de passe sans le publier, puis tests read-only **sous l'identite reelle** pour confirmer token non admin, absence groupe docker-users, absence variable de cle, et refus/unavailability de Docker daemon. Ne pas confondre impossibilite de trouver `docker.exe` ou absence du contexte `desktop-linux` avec une preuve d'ACL refusee. Refus Docker depuis MXC n'etablit pas l'isolation du parent Codex/MCP. Aucun secret, profil Codex existant, compte cloud, SSH ou fichier personnel ne doit etre copie dans le runner. Puis seulement concevoir le compte broker de confiance, ACL/service et le canary synthetique.

## Vérification d'usage des deux comptes locaux — 31/10/2026 (dernier état)

Sortie PowerShell opérateur : `ACCOUNT_1_SERVICE_REFERENCES=0`, `ACCOUNT_1_TASK_REFERENCES=0`, `ACCOUNT_2_SERVICE_REFERENCES=0`, `ACCOUNT_2_TASK_REFERENCES=0`, `VISIBLE_SERVICE_TASK_AUDIT_PASS`, `NO_ACCOUNT_NAMES_OR_SIDS_PRINTED`, `NO_SYSTEM_CHANGES`, `ACCOUNT_USAGE_AUDIT_COMPLETE`. Dans le périmètre visible et avec les alias recherchés, aucune référence dans les services Windows ni les tâches planifiées. **Cela ne prouve pas que les comptes sont inutilisés ou sécurisés :** profils et applications, droits hérités, comptes utilisés autrement et accès Docker ne sont pas couverts.

**Décision recommandée :** ne pas réaffecter automatiquement ces comptes ; privilégier un futur **compte Windows local standard dédié `codex-runner`**, sauf si l'opérateur confirme l'usage exclusif d'un compte préexistant. Le compte Codex doit être isolé de Docker et de la clé Supermemory ; broker doté d'une identité distincte. **Ne rien créer sans étape de provisionnement explicitement autorisée**, test négatif des droits effectifs et procédure de rollback. Le broker V2 est encore prototype hors ligne, 24/24 PASS Windows ; aucune intégration live Codex ni service Windows déployé. Plus d'inventaires d'identités répétitifs ; passer à la préparation du provisioning. Détails : [SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

## Classification comptes Windows — résultat plus récent (31/10/2026)

`ACCOUNT_CLASSIFICATION_PASS` : `INITIAL_CANDIDATES=2`, `CURRENT_USER_OVERLAPS=0`, `BUILTIN_RID_ACCOUNTS=0`, `OTHER_LOCAL_ACCOUNTS=2`, `OTHER_PASSWORD_REQUIRED=2`, `INDIRECT_PERMISSIONS_NOT_VERIFIED`. Les deux comptes locaux activés ne sont ni l'opérateur ni des identités Windows intégrées RID <1000, et ne sont pas listés directement dans Admin/docker-users. **Aucun compte n'est encore autorisé pour Codex :** vérifier l'usage par services/tâches, puis les droits effectifs avec son identité et l'isolation des secrets. Aucun utilisateur, permission, secret ou service n'a été modifié. Spécification de la suite : [SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

## Inventaire Windows broker : lecture seule PASS (plus récent, 31/10/2026)

Sortie PowerShell de l'opérateur : `CURRENT_TOKEN_ADMIN=False`, `PARENT_SUPERMEMORY_KEY_PRESENT=False`, `DOCKER_USERS_GROUP_PRESENT=True`, `STANDARD_ACCOUNT_CANDIDATES=2`, `ACCOUNT_INVENTORY_COMPLETE`, `BROKER_PORT_6811=NO_LISTENER`, `NO_ACCOUNTS_CREATED`, `NO_PERMISSIONS_CHANGED`, `NO_SECRETS_READ`, `WINDOWS_IDENTITY_PREFLIGHT_COMPLETE`.

**Ne pas interpréter 2 comme deux identités de runner utilisables :** le filtre n'éliminait pas le compte courant ayant accès Docker hors sandbox, ni les comptes intégrés/système, ni les appartenances indirectes. `CURRENT_TOKEN_ADMIN=False` indique l'absence de privilège Administrateur actif dans ce jeton, pas l'absence de toute appartenance admin. Le port 6811 est actuellement sans écouteur, pas réservé. **Pas d'isolation d'identités démontrée ; aucun compte créé ou modifié.**

**Prochain gate :** classement local en lecture seule, sans imprimer de noms ni de SID, des deux candidats. Exclure compte courant, RID intégrés et comptes de service; ne pas réutiliser de compte système. Ensuite, si aucun compte adapté, spécifier la création d'un compte local standard exclusivement pour Codex et un compte broker distinct, avec ACL et tests de refus effectifs avant le premier canary live. Détails : [SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

## Broker + MCP V2 : 24/24 PASS sous Windows (dernier résultat du 31/10/2026)

Sortie PowerShell 5.1 de l'opérateur, archive ZIP SHA256 vérifiée : `BROKER_MCP_V2_INTEGRITY_PASS`, `Ran 24 tests in 6.751s`, `OK`, `BROKER_MCP_OFFLINE_TESTS_PASS`, `NO_SECRETS_NO_PRODUCTION_CHANGES`, `BROKER_MCP_V2_WINDOWS_PASS`. Les 24 tests utilisent des jetons factices et une API simulée, sans exécuter Codex, Docker, Ollama ou Supermemory en production. Extraction du ZIP en dossier temporaire unique puis cleanup par le wrapper PowerShell. **Jalon Windows hors ligne validé ; aucune qualification d'isolation d'identité, de service broker ni de recherche live Codex n'est encore réalisée.** Ne pas rejouer les tests hors ligne à code identique.

**Prochaine priorité :** inventaire non destructif Windows (compte opérateur, groupes Docker/Admin, existence éventuelle d'un compte local standard distinct, disponibilité du port broker 6811, absence de secret dans l'environnement) pour fixer les identités de confiance et d'agent. Ne pas créer de compte, changer les ACL, exposer la clé réelle ou lancer Codex avec cette clé sans décision de déploiement et tests négatifs. Détails : [SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

## Nouveau livrable : broker + MCP V2 offline (31/10/2026)

Une V2 indépendante du prototype initial est construite : broker Python `POST /search` namespace fixe + pont MCP JSON-RPC stdio `search` uniquement avec jeton de lecture limité, **sans `SUPERMEMORY_API_KEY` dans la passerelle**. 24 tests offline PASS dans l'environnement de préparation, dont exécution de la passerelle comme sous-processus. Aucun test Windows/opérateur ni déploiement n'a été effectué. ZIP de conversation `Supermemory_Readonly_Broker_MCP_Offline_V2_20261031.zip`, SHA256 `A0A40F07D0C4272647D54E3839A5163067BE48ACF5F9D509C07B8165FDD811B5`. Spécification et instructions : [SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md). L'archive n'est pas hébergée par GitHub ; elle est attachée dans la conversation.

**Prochain gate :** Windows offline 24/24, puis séparation Windows/VM réelle des identités et permissions avant tests avec la clé de production. Ne pas répéter sondes MXC/Docker, réinitialiser Supermemory ni écraser la branche adaptateur locale `e4fd34e`.

## MXC V3 terminé et broker read-only prototypé — 31/10/2026 (dernier état)

L'opérateur a exécuté la sonde MXC V3 avec checksum vérifié. **`V3_DOCKER_DAEMON_EXIT=1`, `V3_DOCKER_EXEC_EXIT=1`, `V3_DOCKER_FAILURE_CLASS=ACCESS_DENIED`, `V3_SANDBOX_DOCKER_ACCESS_NOT_DEMONSTRATED`**, sur un processus enfant sandboxé (MXC 0.164.0). L'exécutable Docker était présent mais le daemon inaccessible. **Ce résultat ne prouve pas la protection de l'environnement du parent Codex ou des serveurs MCP** ; le compte Windows hors MXC possède toujours Docker. `NO_MODEL_CALLS_NO_SECRET_CONTENT`. **Probes Docker V1-V3 closes.** Aucun autre test Docker similaire n'est demandé.

**Livrable préparatoire hors production :** `Supermemory_Readonly_Broker_Prototype_20261031.zip`, SHA256 `C8F52A948C450945994198E427EF857442018AC448F6E38D251EBB2570637DA8` (3 fichiers Python / tests / README, disponible comme artefact du chat, pas dans le repo). **14 tests unitaires PASS sur clés factices**, endpoint `/search` seul, namespace fixé et jeton broker distinct, aucune redirection ou route d'écriture. **Non déployé, pas encore une frontière de sécurité**. Prochaine étape : identité Windows/VM séparée pour Codex sans accès Docker/clé amont, broker de confiance, ACL/permissions et passerelle MCP avec seulement un jeton de lecture. L'adaptateur local `e4fd34e` et Supermemory prod intacts. Spécification : [SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md](SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md).

## MXC V2 — résultat réel du 31 octobre 2026 (le plus récent)

La sonde V2 lancée par l'opérateur a **démarré MXC sans modèle** (`MXC_ECHO_PASS`, `MXC_ECHO_EXIT_CODE=0`) sous Codex CLI `0.164.0`, avec clé API Supermemory absente de l'environnement parent. Le test Docker depuis MXC a affiché `SANDBOX_DOCKER_EXEC_NOT_OBSERVED` et `MXC_DOCKER_EXIT_CODE=0`. **Attention :** le code de sortie 0 correspond au PowerShell de la sonde ; le code Docker interne était **non nul**, sinon le marqueur aurait été `SANDBOX_DOCKER_EXEC_REACHABLE`. Le diagnostic de cette erreur Docker reste masqué (permissions, pipe ou contexte indéterminés). Aucun secret lu ; pas de modèle ni modification globale.

**Prochain contrôle unique :** `Test-CodexMxcDockerBoundary-v3-diagnostic-20261031.ps1` SHA256 `AFEB2060FFC63B352512AC0E900462F95A6BDB75A841DF148599D858F280275F` (script du chat, pas de commit dans le dépôt). Permet de distinguer accès daemon Docker vs échec de `docker exec stat`, et catégorise le refus, sans afficher de log brut. Même un refus démontré ne suffira pas à garantir qu'une clé entière héritée serait protégée par Codex ou les serveurs MCP. La production Supermemory, les hooks, le code local e4fd34e restent inchangés ; choisir une vraie séparation de secrets (compte/VM) après cette sonde et arrêter les tests répétitifs.

## Résultat le plus récent — audit de la frontière Codex/Supermemory

**`SECURITY_AUDIT_EXECUTION_COMPLETE`, mais `SANDBOX_PROBE_INCONCLUSIVE_OR_UNSUPPORTED` : aucun feu vert pour brancher la clé réelle dans Codex.** L'opérateur a confirmé `ADAPTER_LOCAL_HEAD_PASS`, `ADAPTER_ENV_SECRET_INHERITANCE_RISK_CONFIRMED`, `PRODUCTION_HEALTH_PASS`, `HOST_LOOPBACK_ONLY_PASS`, `WINDOWS_OPERATOR_CAN_USE_DOCKER_EXEC_ON_SECRET_FILE`, `PARENT_PROCESS_HAS_SUPERMEMORY_KEY=False`, `NO_CODEX_MODEL_CALLS`, `NO_SECRETS_PRINTED_OR_MUTATED`. Le compte Windows hôte peut accéder via Docker aux métadonnées du fichier clé ; la preuve de la restriction sandbox manque. **Un `inconclusive` n'est ni un blocage Docker prouvé ni une exposition prouvée depuis le processus sandboxé.**

**Prochaine étape immédiate :** sonde sans modèle `Test-CodexMxcDockerBoundary-v2-20261031.ps1` SHA256 `64C04CB0CBC960248CF462C88F2E42D19B1167666B65D1B9AB2948B0CD637999` (artefact du chat, non poussé sur GitHub). Elle force MXC uniquement pour l'invocation, vérifie un echo inoffensif puis `docker exec stat` sans lire la clé ; distingue échec de démarrage vs accès Docker. La sortie de cette V2 reste à obtenir. Spécifications détaillées : [SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md](SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md).

**Ne pas remettre la clé réelle dans l'environnement Codex**, activer des hooks ou installer des outils. Les validations V5, plan BGE, Ollama direct, 3 mémoires synthétiques et MCP Python hors Codex restent acquises.

## Nouveau chantier actif : frontière de secrets Codex / Supermemory

Plan et audit non destructif : [SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md](SUPERMEMORY_CODEX_SECURITY_GATE_2026-10-31.md). **Aucun canary Codex avec la clé API réelle tant que l'identité Codex pourrait accéder à Docker ou hériter des secrets.** Prochaine preuve attendue : sortie de l'audit Windows sans appel modèle. Le plan BGE-M3, la restauration V5, l'inférence Ollama directe, les 3 mémoires extraites et le smoke-test MCP Python restent valides et ne doivent pas être relancés. Ce document d'architecture ne constitue pas une nouvelle preuve d'isolement ou d'accès effectif Codex.

## Qualification de l'extraction du canary — 31 octobre 2026 (dernier résultat)

**`EXTRACTED_MEMORIES_PRESENT_PASS`** : sortie Windows PowerShell communiquée par l'opérateur. Un **unique contrôle en lecture seule**, `POST http://127.0.0.1:6767/ns/codex_llm_canary_c58e251be7bf/list/memories?limit=10`, JSON `{}`, a renvoyé :

- `MEMORIES_RETURNED=3`, `MEMORIES_TOTAL=3` ; `MEMORY_LIST_READ_PASS`, `EXTRACTED_MEMORIES_PRESENT_PASS`, `EXISTING_CANARY_MEMORY_CHECK_COMPLETE`.
- Le document unique du namespace était déjà `system.status=done`. On a donc une preuve de **trois mémoires réellement disponibles via l'API de lecture** pour le document synthétique, même si `system.dreamingStatus` et `system.memoryCount` n'étaient pas présents dans les réponses de métadonnées antérieures.
- Aucune nouvelle ingestion ni altération de production n'a eu lieu lors de ce contrôle. Ne pas refaire les tests document/status/mémoire, ni le backup/restore, ni le plan d'embeddings ou l'inférence Ollama directe.
- Les **3 requêtes de génération Ollama** observées durant l'ingestion restent des **indices corrélatifs**, pas une preuve d'attribution à ce processus ou à `qwen3:8b`, ni une preuve d'absence de fallback cloud.

**Prochain bloc prioritaire :** instrumenter l'attribution locale Supermemory→Ollama / l'absence d'egress inapproprié, puis préparer un **canary Codex MCP lecture seule** avec cloisonnement de la clé complète Supermemory. Le test Python direct MCP est déjà PASS ; **ne pas transmettre `SUPERMEMORY_API_KEY` dans l'environnement de Codex ou de ses descendants** sans solution de moindre privilège. L'adaptateur est encore uniquement local sur `codex/supermemory-local-adapter-20261030` au commit `e4fd34e`, et n'est pas dans le dépôt GitHub. Définir un mécanisme broker/proxy filtrant ou autre gestion de crédentiel indépendante avant tout usage avec données sensibles. Ne pas écraser la branche locale en synchronisant main.

## Contrôle documentaire du canary existant — 31/10/2026 (plus récent)

**`EXISTING_CANARY_METADATA_CHECK_COMPLETE` ; `DOCUMENT_INDEXED_PASS`**, d'après sortie opérateur Windows PowerShell : `POST /ns/codex_llm_canary_c58e251be7bf/list/documents?limit=10` avec corps `{}` en lecture seule, clé API masquée, a renvoyé `DOCUMENTS_FOUND=1`, `DOCUMENT_STATUS=done`, `DREAMING_STATUS=ABSENT`, `MEMORY_COUNT=ABSENT`, `DREAMING_STATUS_UNCONFIRMED`.

**Conclusion exacte :** le document synthétique est bien indexé, mais ces deux métadonnées n'ont pas été incluses dans cette réponse, pas plus que `dreamingStatus` lors du `GET /document/{id}` antérieur. **Ne pas traiter ABSENT comme erreur d'extraction ni comme extraction achevée.** Aucun nouveau document créé ; pas de test de restauration ou d'inférence Ollama directe nécessaire.

**Prochain geste minimal :** `POST /ns/codex_llm_canary_c58e251be7bf/list/memories?limit=10`, corps `{}`, consulter uniquement le décompte sans afficher les textes/ID secrets. Un résultat >0 prouve l'existence de souvenirs extraits ; 0 ne prouve pas l'échec (le texte synthétique peut ne générer aucun souvenir). Après cette lecture, ne pas continuer une série de tests de métadonnées absentes : qualifier l'origine des 3 requêtes Ollama avec observation fiable ou passer à une stratégie de canary Codex↔MCP contrôlant la clé API, uniquement après validation des limites de sécurité.

La branche adaptateur `codex/supermemory-local-adapter-20261030` est toujours locale à `e4fd34e`, non poussée ; ne pas écraser au moyen d'un `git pull` ou de nettoyage forcé. Ce document de passation est suivi sur GitHub `main` ; les scripts et clés restent sur le PC.

## Corrélation Supermemory → Ollama — essai synthétique du 31/10/2026 (résultat le plus récent)

**`SUPERMEMORY_OLLAMA_CORRELATION_INCONCLUSIVE`**, et non PASS. L'opérateur a exécuté un unique test synthétique depuis PowerShell 5.1, avec lecture des nouveaux octets du journal Ollama `%LOCALAPPDATA%\Ollama\server.log` après création du document.

- Production `supermemory-supermemory-1` **healthy** ; `SUPERMEMORY_OLLAMA_PREFLIGHT_PASS`.
- Un document non personnel a été accepté dans le namespace dédié **`codex_llm_canary_c58e251be7bf`** (`SYNTHETIC_DOCUMENT_ACCEPTED_PASS`).
- La lecture `GET /ns/{namespace}/document/{id}` renvoie **`system.status=done`** : traitement/indexation du document achevé. **`system.dreamingStatus` renvoie vide/absent** ; ne pas interpréter comme `done`, `failed` ou `dreaming`. La variable `$id` était locale au scriptblock PowerShell et sa valeur n'a pas été imprimée ; éviter de demander un nouvel ingest simplement pour l'obtenir.
- **3 requêtes POST de génération** ont été détectées dans le segment du log Ollama suivant le début du test (`OLLAMA_NEW_GENERATION_REQUESTS=3`, `OLLAMA_GENERATION_TRAFFIC_OBSERVED`). Le motif couvre `/v1/chat/completions`, `/v1/completions`, `/v1/responses`, `/api/chat`, `/api/generate` ; **aucune attribution formelle au seul conteneur Supermemory ou au modèle `qwen3:8b`**, car d'autres clients peuvent solliciter Ollama.
- Condition d'origine `status=done AND dreamingStatus=done AND requests>0` non satisfaite à cause du champ `dreamingStatus` non renseigné. **Ne pas ajouter de PASS de corrélation** à ce stade.
- Les docs publiques v5 `apps/docs/ingestion/document-operations.mdx` indiquent que `POST /ns/{namespace}/list/documents?limit=10` (corps `{}`) renvoie la liste des documents `system.status`, `system.dreamingStatus`, `system.memoryCount` sans inclure le contenu par défaut. Les docs indiquent que `status=done` ne garantit pas que l'extraction des mémoires est achevée ; `dreamingStatus` peut ne pas être exposé dans certaines réponses. **Prochain contrôle recommandé : lister uniquement les métadonnées du namespace existant, sans nouvelle écriture ni logs bruts**. Si l'état dreaming reste absent, résultat « inconnu », pas « failed ».
- Après cela, pour prouver le routage précis Supermemory→Ollama, prévoir une attribution instrumentée par origine/modèle ou isolation contrôlée du trafic et vérifier l'absence de fallback externe ; ne pas prétendre démontrer le « zéro egress » avec un compteur de POST.
- La sauvegarde et restauration V5 PASS, le plan BGE-M3 6/6 PASS, Ollama Qwen3 direct PASS, l'adaptateur MCP read-only hors Codex PASS restent acquis : **ne pas les rejouer**. Premier canary Codex↔MCP toujours en attente, avec risque d'héritage de cle complète de l'API dans l'environnement descendant.

## MCP Supermemory live smoke — 31/10/2026 (dernier resultat, hors Codex)

**`SUPERMEMORY_MCP_READONLY_SMOKE_PASS`**, sortie PowerShell 5.1 rapportee par l'operateur, sans lancer Codex :

- `MCP_PREFLIGHT_PASS` : branche de travail locale `codex/supermemory-local-adapter-20261030`, HEAD `e4fd34e`, conteneur `supermemory-supermemory-1` healthy.
- Lancement `py -3 -B .\scripts\supermemory_mcp.py` en stdio JSON-RPC sous `C:\Dev\codex-context-efficiency-stack`. Cle Supermemory lue directement du conteneur sans etre affichee ; variables de processus restaurees par `finally`. Namespace du depot et `SUPERMEMORY_ALLOW_SAVE=0` (lecture seule).
- Requetes `initialize`, `notifications/initialized`, `tools/list`, `tools/call` avec `name=search` sur une requete synthetique. Retours `MCP_INITIALIZE_PASS`, `MCP_READONLY_TOOLS_PASS` (un seul outil `search`), `MCP_LIVE_SEARCH_PASS` (pas d'erreur JSON-RPC/MCP et contenu renvoye).
- **Alimentation du namespace non exigee :** un resultat de recherche vide reste acceptable. Ce test valide la couche MCP jusqu'a l'API Supermemory, **pas** la pertinence des souvenirs ni l'inference LLM.
- **Limite securite** : une cle API Supermemory complete presente dans l'environnement d'un processus Python est accessible a ses descendants eventuels. Ne pas l'exposer a Codex ni a des donnees sensibles sans decision explicite d'isolation/secret.

**Gate acquis :** adaptateur Python ↔ Supermemory Local, en lecture seule, hors Codex. **Gates ouverts :** (1) verifier via preuve instrumentee Supermemory → Ollama `qwen3:8b` sur une seule entree synthetique ; (2) controle d'egress et de fallback cloud ; (3) premier canary Codex ↔ MCP lecture seule avec controle de l'heritage de la cle ; (4) synchroniser sans ecraser la branche adaptateur toujours exclusivement locale, puis PR code et autres priorites P1/P2. Les backup/restore, plan d'embeddings, et Ollama /api/generate direct sont deja PASS, ne pas les rejouer.

## Verification Ollama Qwen3 — 31/10/2026 (dernier resultat)

**`OLLAMA_QWEN3_INFERENCE_PASS`** rapporte par la sortie Windows PowerShell operateur : `GET http://127.0.0.1:11434/api/tags` annonce `qwen3:8b` et `POST /api/generate` (prompt synthetique "OK", `stream=false`, `think=false`, `num_predict=32`) renvoie `model=qwen3:8b`, `done=true`, `eval_count=2`. Marqueurs `OLLAMA_MODEL_AVAILABLE_PASS`, `OLLAMA_QWEN3_INFERENCE_PASS`.

**Ce qui est acquis :** Ollama Windows sait generer effectivement et localement avec qwen3:8b, independamment de Codex. Controle sans ecriture dans les memoires Supermemory.

**Ce qui reste distinct :** ce test **ne prouve pas** qu'un traitement Supermemory a appele Ollama, ni l'absence d'autres sorties/fallback reseau cloud. Prochaine qualification : appel synthetique Supermemory sur namespace dedie avec preuves observees du parcours Supermemory → Ollama, isolation des donnees de test et aucun secret affiche ; puis canary Codex ↔ MCP en lecture seule. Ne pas refaire inference Ollama directe, backup V5, ou plan d'embeddings 6/6.

## Validation embeddings — 31/10/2026 (dernier gate valide)

**`EMBEDDING_PLAN_SNAPSHOT_RUNTIME_PASS` : 6/6 comparaisons conformes**, d'apres la sortie PowerShell de l'operateur. Le fichier persistant `embedding-plan.json` existe dans le snapshot froid `snapshot-20261031-003115/data` et dans le conteneur de production `supermemory-supermemory-1`. Schema observe : `provider`, `modelId`, `dimensions` (**`modelId`, pas `model`**).

| Champ du plan | Snapshot | Runtime |
| --- | --- | --- |
| `provider` | `local` — MATCH | `local` — MATCH |
| `modelId` | `Xenova/bge-m3` — MATCH | `Xenova/bge-m3` — MATCH |
| `dimensions` | `1024` — MATCH | `1024` — MATCH |

Le serveur de production est `healthy` pendant cette lecture. **Plan persistant et configuration embeddings conformes ; ne pas reinitialiser la base, changer de modele, refaire le backup/restore, ni relancer V1-V5.** Cela ne constitue pas une preuve d'inference effective du modele sur toute requete ni de zero trafic sortant.

**Prochain gate actif :** qualifier l'inference reelle `qwen3:8b` via Ollama (et l'absence de fallback cloud) avec observation locale securisee ; ensuite canary Codex ↔ MCP en lecture seule et controle du secret d'API. La branche adaptateur `codex/supermemory-local-adapter-20261030` au commit local `e4fd34e` est non poussee et a ete creee avant les dernieres mises a jour de docs sur main. Ne pas perdre ni ecraser les commits locaux en synchronisant plus tard. PR #14 P1.1 toujours ouverte, benchmarks distincts.

## Validation V5 effective — 31/10/2026 (nouvel etat canonique)

**Restauration applicative Supermemory Local 0.0.9 : PASS, phase close.** Sortie Windows PowerShell fournie par l'operateur :

- `V5_INTEGRITY_PASS` (SHA256 du script attendu verifie avant lancement).
- `OFFLINE_HELPERS_PASS` ; `CLONED_CONTENT_MATCH_PASS` ; `RESTORED_TEMP_OWNERSHIP_PASS` (UID/GID 10001:10001, /data 700, api-key 600 **sur copie temporaire seulement**).
- `ISOLATION_NO_NETWORK_NO_PORTS_PASS` ; `RESTORED_APP_HEALTH_PASS` ; `RESTORED_AUTHENTICATED_READ_PASS` (GET /v3/projects a l'interieur de la namespace reseau du clone).
- `ISOLATED_CONTAINER_CLEANUP_PASS` ; `ISOLATED_VOLUME_CLEANUP_PASS` ; `LOCAL_SCRIPT_CLEANUP_PASS` ; `ISOLATED_APP_RESTORE_FULL_PASS` ; `SUPERMEMORY_V5_PASS`.

**Interpretation :** le passage de la copie par NTFS necessite la restauration explicite des proprietaires et permissions Linux sur le volume cible. La procedure V5 le fait sur un volume ephemere ; les donnees sont restituables et l'application demarre avec lecture API authentifiee. Le succes ne demontre pas isoleement que l'ownership etait l'unique cause des echec V2/V3 (V5 a egalement repare le quoting des scripts shell). La production n'a pas ete modifiee ; pas de nouveau backup necessaire pour ce jalon. V1-V4 restent des historiques d'echecs, pas des tests a refaire.

**Prochain gate actif :** verifier l'effectivite du plan d'embeddings verrouille `local / Xenova/bge-m3 / 1024`, puis le chemin d'inference `qwen3:8b` via Ollama, en distinguant configuration declaree, mesures observables et preuve d'absence de trafic vers des fournisseurs externes. Lancer ensuite un canary Codex ↔ MCP en **lecture seule** et resoudre la diffusion de la cle d'API vers les processus descendants avant donnees sensibles. **Brancher la branche de travail locale `e4fd34e` seulement apres ces gates ; le code de l'adaptateur n'est toujours pas sur main.** Ne pas redeployer, relancer les tests de sauvegarde, activer des hooks globaux ou ingerer des donnees reelles sans controles.

Les sections V1-V4 et l'ancien « prochain gate V5 » ci-dessous sont conservees comme historique et sont **supplantees** par ce resultat.

## Priorite

Finaliser l'integration **Supermemory Local 0.0.9 ↔ Codex CLI** en **opt-in, projet autorise, lecture seule en premier**, sans modifier les hooks globaux ni divulguer la cle API. Ne pas relancer installations, tests anciens ni benchmarks P1.1. Le pilote VM/full-access demeure ulterieur.

## Code Codex Supermemory — etat du 31 octobre

- Depot : `Proginji2000/codex-context-efficiency-stack`.
- **Branche uniquement locale sur le PC operateur**, non poussee sur GitHub : `codex/supermemory-local-adapter-20261030`, HEAD `e4fd34e` (`fix: harden scoped local Supermemory MCP adapter`). Le commit parent est `972d6dd` (fusion locale de `origin/main` a `fa51ccb8`), et l'adaptateur avait ete cree en `6765c68`. **Ne pas supposer que la branche/code de l'adaptateur est disponible sur GitHub.**
- Six fichiers codes/docs suivis ; securite corrigee (routes API, `query`, redaction de secrets JSON imbriques, opt-in lecture seule, endpoint 127.0.0.1:6767 fixe, revalidation namespace, erreurs MCP, validation longueurs).
- Tests rapportes : Python **16/16 PASS**, tests du lanceur PowerShell PASS, **23/23** scripts de syntaxe PASS, `git diff --check` PASS. Aucun test live Codex↔MCP jusqu'ici. `scripts/__pycache__/` reste non suivi : ne pas nettoyer automatiquement.
- `~/.codex/config.toml` et `~/.codex/hooks.json` SHA256 **UNCHANGED** par rapport aux valeurs historiques. Hooks `SessionStart` et `PostToolUse` a preserver.
- En attente de qualification : fuite possible de cle transmise en environnement aux descendants Codex ; aucune exposition a des donnees sensibles avant decision d'architecture de secrets. Ne pas activer l'ecriture automatique.

## Supermemory Docker — etat et preuves

- Image `docker.io/supermemory/supermemory:0.0.9`, conteneur `supermemory-supermemory-1`, `running/healthy` apres redemarrage.
- Volume production : `supermemory_supermemory-data` monte dans `/data`. API hote uniquement sur `127.0.0.1:6767`. NE JAMAIS supprimer ce volume, ni lancer `docker compose down -v`.
- Controle Compose vs runtime : **9/9 MATCH** : `OPENAI_BASE_URL=http://host.docker.internal:11434/v1`, modeles `OPENAI_MODEL`, `OPENAI_FAST_MODEL`, `OPENAI_TEXT_MODEL=qwen3:8b`; embeddings provider `local`, modele `Xenova/bge-m3`, dimensions `1024`; telemetry et update check demandes a `1`. Ces variables ne prouvent ni l'inference effective ni l'absence de trafic cloud.
- API authentifiee et recherche semantique synthetique avaient ete validees le 30/10. Aucune capture automatique des sessions Codex.
- **Sauvegarde a froid** le 31/10 : `C:\Users\Quentin\AppData\Local\SupermemoryBackups\snapshot-20261031-003115` : 60 fichiers, **935945989 octets**. Copie des fichiers `compose.yaml`, `compose.override.yaml`, `.env` dans `config` ; cle et identite sous `data`. Ce repertoire **contient des secrets ; ne jamais l'envoyer dans le chat ou sur GitHub**.
- `SUPERMEMORY_COLD_BACKUP_PASS` ; service `healthy` apres restart. Restauration du contenu dans volume distinct, comparaison `diff -qr`, suppression du volume test : `SUPERMEMORY_RESTORE_CONTENT_PASS`.
- **Restauration applicative PAS ENCORE validee.** Essai V1 : defaut de quoting Go templates Docker dans le cleanup ; V2 : application restauree `unhealthy`/quitte ; V3 : `RESTORED_EXIT_CODE=1`, `RESTORED_OOM_KILLED=False`, `RESTORED_HEALTH=unhealthy`. Categorie de logs potentiels : modele/cache et stockage/permissions **non conclusives**. Instance restauree sans reseau, ni port publie.
- Cleanup de l'essai V1 : `RESTORE_ORPHAN_CLEANUP_PASS`. Inventaire final : **0** conteneurs test / **0** volumes test selon filtre `label=openai.supermemory.isolated-restore-check`.
- Production `docker exec id` : `uid=10001(supermemory)`, `gid=10001(supermemory)` ; `/data` **10001:10001 mode 700** et `/data/api-key` **10001:10001 mode 600**. Le clone V1-V3 a ete reconstruit par un conteneur utilitaire execute en root depuis un repertoire hote NTFS. **Hypothese forte non encore prouvee : proprietaires des fichiers restaures devenus root:root, rendant /data inaccessible au serveur non-root.** Ne pas conclure que les donnees sont corrompues ou que le LLM est responsable.
- Emplacements testes `/data/.cache`, `/data/cache`, `/root/.cache`, `/home/node/.cache` : NOT_VISIBLE_OR_ABSENT. Ne pas en conclure que tous les caches de modeles sont absents.

## Nouvelle tentative V4 et correctif V5 (31/10, apres la presente passation)

- **V4 NON VALIDEE**. La commande de l'operateur a rencontre un dossier d'extraction deja existant (garde initiale declenchant `STOP`), puis a continue ligne par ligne malgre les erreurs. Le ZIP d'origine et le script local ont toutefois passe leur verification SHA256 ; il ne faut pas traiter le `Write-Host SUPERMEMORY_V4_PASS` manuel comme preuve de succes.
- V4 a cree un volume temporaire et lance la copie ; `docker /bin/sh -c` a echoue avec `syntax error: unexpected end of file (expecting \")\")`. Cause de script : expression shell `\"$(stat ...)\"` dans un programme multiligne transmis par l'interface native de **Windows PowerShell 5.1**, dont le passage de guillemets ne preservait pas le code. Aucun `RESTORED_TEMP_OWNERSHIP_PASS` n'a ete obtenu ; l'hypothese ownership reste **ouverte**, pas prouvee.
- Le script V4 a affiche `ISOLATED_CONTAINER_CLEANUP_PASS` et `ISOLATED_VOLUME_CLEANUP_PASS` apres l'echec, mais un nouvel inventaire externe des orphelins n'a pas encore ete realise a cette date.
- **V5 preparee, pas encore executee sur Windows**. Fichier `Test-SupermemoryIsolatedAppRestore-v5-ownerfix.ps1` (artefact de conversation), SHA256 `712B7A2DAFA208CCC7B0E78B7F69A62FFE283FCE01E089EBA445F05DAEBDCC86`. ZIP `Supermemory_Restore_V5_20261031.zip`, SHA256 `8D8B27F6E32FEB7A767D0C00FDF5A70C5C8D7621372B95C057DFC5D39B5B57EB`. Les scripts POSIX extraits ont passe `sh -n`, plus controle statique des chemins de montage ; **aucun PASS Docker/PowerShell effectif revendique**.
- V5 monte des petits fichiers shell LF/UTF-8 via bind Docker, executes avec `/bin/sh /tmp/restore.sh` et `/bin/sh /tmp/read.sh`, plutot que de transmettre le programme multiligne via `-c`. V5 doit restaurer et comparer le volume clone, corriger **uniquement sur clone** vers UID/GID 10001:10001 et les modes 700/600, tester health/API sous isolation, puis nettoyer les ressources temporaires.
- Prochain retour demande : **sortie V5 et son marqueur interne `ISOLATED_APP_RESTORE_FULL_PASS` seulement si reellement emis par le script**. Si health echoue apres permissions corrigees, la prochaine analyse ciblera les erreurs au demarrage, sans exposer les logs bruts ni assouplir sans motif l'isolation reseau.

## Prochain gate : tester les droits uniquement sur volume temporaire (V5)

1. Garder la production en marche ; verifier `healthy`, image, montage, et integrite des fichiers de sauvegarde sans lire les secrets.
2. Creer un nouveau volume temporaire nomme/labelise avec nonce. Copier le snapshot, comparer les fichiers **avant correction des metadonnees**.
3. Dans le **volume temporaire uniquement**, `chown -R 10001:10001 /dest`, `chmod 700 /dest` et `chmod 600 /dest/api-key` ; verifier uid/gid/modes. Ne pas modifier source Windows ni volume production.
4. Demarrer le conteneur Supermemory restore isolé (pas de port publie, `--network none`). Son absence d'acces a Ollama peut bloquer l'initialisation : si l'application echoue encore, diagnostiquer sans afficher de logs bruts et **sans assouplir le reseau par defaut**.
5. Si healthy, faire une lecture API authentifiee depuis sidecar `--network container:<test>`, puis nettoyer conteneur et volume temporaires, verifier l'absence d'orphelins. Eviter les faux PASS : un `Write-Host` lance apres erreur ne constitue pas une preuve.
6. Ensuite seulement, verifier effectivite BGE-M3 verrouille, routage reel Qwen3/Ollama, et absence de trafic exfiltrant ; puis canary Codex MCP scope/code en lecture seule ; decision sur secrets et PR du code.

Les scripts diagnostiques V1-V3 sont des artefacts de la conversation, **pas** des fichiers suivis dans le depot GitHub. Ne pas reexecuter sans raison les sauvegardes et canaries deja acquis.

## Autres priorites et limites

- Serena 2.1.0 (LSP et memoire intersessions) et shadcn MCP conditionnel etaient deja valides, PR #91/#92 fusionnees.
- `P1.1` reste EN QUALIFICATION ; PR #14 toujours ouverte. V3 4/4 canaries fonctionnelles mais economie de quota non demontree. Ne pas fusionner #14 sans preuve complementaire.
- P1.2 exposition effective MCP, P1.4 autocorrection, P2 multi-writers/worktrees, P3 VM confinee et P4 full access restent ouverts selon la roadmap ; priorite actuelle = Supermemory et securite.

## Si le chat s'interrompt

Reprendre a partir de ce document, de `docs/QUALIFICATION_ROADMAP_2026.md`, du code **local** au commit `e4fd34e` et des dernieres sorties PowerShell. Demander uniquement la sortie non sensible du test **V4 droits de la restauration isolee**, pas les secrets, dumps de conteneur ou env files. Ne jamais supprimer des caches ou dossiers non suivis par automatisme.
