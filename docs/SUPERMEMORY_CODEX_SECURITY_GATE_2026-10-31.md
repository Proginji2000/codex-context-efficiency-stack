# Supermemory ↔ Codex — barrière de sécurité avant canary réel

**Date:** 31 octobre 2026. **Statut:** architecture et audit préparés, non déployés. Ce document complète [la passation du 31 octobre](CODEX_STACK_HANDOFF_2026-10-31.md) et la [roadmap](QUALIFICATION_ROADMAP_2026.md).

## Baseline acquise : ne pas rejouer

- Conteneur Supermemory Local v0.0.9 healthy, lié à 127.0.0.1:6767 ; volume de production et sauvegarde froide V5 restaurés et testés avec succès.
- Plan persistant `local / Xenova/bge-m3 / 1024` concordant entre snapshot et production (6/6).
- Ollama local `qwen3:8b` a généré 2 tokens via `/api/generate` (direct).
- Document fictif ingéré sur le namespace `codex_llm_canary_c58e251be7bf` : statut `done`, **3 souvenirs récupérés** via `list/memories` ; 3 POST de génération Ollama observés dans la même fenêtre, attribution du client et du modèle *non prouvée*.
- Adaptateur Python MCP stdio de la branche **uniquement locale** `codex/supermemory-local-adapter-20261030` au commit `e4fd34e` : `initialize`, `tools/list` exposant **`search` seulement**, et `tools/call search` vers Supermemory en lecture seule **PASS hors Codex** ; la branche n'est pas poussée. Réussites de tests Python 16/16 rapportées, hooks globaux inchangés.

## Pourquoi la simple suppression de « save » ne suffit pas

Le lanceur local `scripts/Invoke-CodexScopedMcp.ps1` requiert actuellement `SUPERMEMORY_API_KEY` dans l'environnement Windows qui lance Codex ; le processus Codex et ses descendants peuvent potentiellement hériter de cette clé. Le contrôle d'outil `search` / `save` et le contrôle de namespace sont **côté client**, et ne limitent pas les privilèges serveur de la clé complète. Dans le même contexte Windows, une identité qui peut utiliser `docker --context desktop-linux exec` sur le conteneur de production est susceptible de lire directement `/data/api-key` si l'OS/sandbox ne bloque pas cette opération ; un simple proxy sur le même compte n'établit pas une frontière de confiance.

**Ne jamais lancer de canary Codex avec la véritable clé de production tant que l'isolation ci-dessous n'est pas qualifiée.**

## Audit non destructif en premier (sans quota)

Artefact de conversation: `Test-CodexSupermemorySecurityBoundary-20261031.ps1`, SHA256 `C868D4968D6B473E3E3183B2D584D40EDE12CF5D403C8FDB82FBDA11AB2C23AC`. Script PowerShell 5.1 conçu pour :
1. Vérifier l'existence de la branche locale et du commit `e4fd34e`, l'existence du lanceur et de l'adaptateur, et le recours à la variable `SUPERMEMORY_API_KEY`. Aucun changement Git.
2. Lire seulement les statuts `healthy`, bind Docker `127.0.0.1:6767` et les **métadonnées** `stat` de `/data/api-key` ; aucun `cat` de la clé ou affichage de son contenu.
3. Exécuter **sans lancer de modèle** `codex sandbox windows -- powershell.exe -NoProfile -NonInteractive -EncodedCommand ...` avec une commande ne faisant qu'un `stat` sur ce fichier. Afficher `SANDBOX_DOCKER_EXEC_REACHABLE`, `SANDBOX_DOCKER_EXEC_NOT_OBSERVED` ou `SANDBOX_PROBE_INCONCLUSIVE_OR_UNSUPPORTED`. Le contrôle `codex sandbox windows` dépend de la version et de la configuration et ne prouve **pas** à lui seul la sécurité d'une future session, même en cas de refus.
4. Aucune modification aux fichiers, modèles, conteneurs, hooks, volumes ou à l'environnement du processus parent. Aucun appel modèle ni requête vers une API externe.

Ce script a été examiné statiquement mais **pas exécuté sur le PC Windows**. Ne pas revendiquer de résultat de sandbox avant la sortie opérateur.

## Audit exécuté — sortie opérateur du 31 octobre 2026

Script initial SHA256 conforme : `SECURITY_AUDIT_INTEGRITY_PASS`, puis `SECURITY_AUDIT_EXECUTION_COMPLETE`. Observations directes :

- `ADAPTER_LOCAL_HEAD_PASS` (branche locale `codex/supermemory-local-adapter-20261030`, HEAD `e4fd34e`).
- `ADAPTER_ENV_SECRET_INHERITANCE_RISK_CONFIRMED` : risque architectural de fuite de la clé API complète dans l'environnement de Codex.
- `PRODUCTION_HEALTH_PASS`, `HOST_LOOPBACK_ONLY_PASS` : production Supermemory healthy, publication Docker sur `127.0.0.1:6767` uniquement.
- `WINDOWS_OPERATOR_CAN_USE_DOCKER_EXEC_ON_SECRET_FILE` : **le compte Windows opérateur peut exécuter `docker exec stat` sur le fichier API-key** (métadonnées seulement). Cette capacité doit être retirée/isolée du contexte agent, indépendamment de la présence du secret dans ses variables d'environnement.
- `PARENT_PROCESS_HAS_SUPERMEMORY_KEY=False` : pas de variable de clé dans le processus PowerShell du test (n'invalide pas la possibilité de la lire via Docker).
- `SANDBOX_PROBE_INCONCLUSIVE_OR_UNSUPPORTED` : l'ancien script masque la sortie native et le code d'erreur détaillé ; **pas de preuve de blocage ou de réussite** dans la sandbox. `NO_CODEX_MODEL_CALLS`, `NO_SECRETS_PRINTED_OR_MUTATED`.

**Correctif de diagnostic V2 préparé mais non exécuté sur le PC** : artefact `Test-CodexMxcDockerBoundary-v2-20261031.ps1`, SHA256 `64C04CB0CBC960248CF462C88F2E42D19B1167666B65D1B9AB2948B0CD637999`. Le test lance explicitement, pour cette seule invocation, `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- powershell.exe ...`, d'abord `CODEX_MXC_ECHO_OK`, puis `docker exec stat` **sans lire la clé** seulement si le démarrage MXC réussit. Sorties d'erreur récapitulées en catégories, pas de logs bruts. **Ne modifie pas config.toml ni les hooks**. Compatible en principe avec la CLI ≥0.162 selon la documentation Windows actuelle, mais son comportement réel sous PowerShell 5.1 reste à confirmer.

Ce probe teste le **processus de commande sandboxé**, pas nécessairement le processus Codex lui-même ou un serveur MCP externe. Même un refus Docker dans ce probe ne suffit pas à autoriser l'envoi du secret à Codex. La décision du broker doit reposer sur une véritable frontière d'identité ou VM et sur la démonstration des refus d'accès directs.

## Audit MXC V2 exécuté — 31 octobre 2026

L'opérateur a validé SHA256 et exécuté `Test-CodexMxcDockerBoundary-v2-20261031.ps1`, sans modèle ni lecture de secrets :

- `MXC_PROBE_INTEGRITY_PASS`, `ADAPTER_LOCAL_HEAD_PASS`, `PARENT_SUPERMEMORY_API_KEY_ABSENT_PASS`, `CODEX_VERSION=codex-cli 0.164.0`.
- `MXC_ECHO_EXIT_CODE=0` et `MXC_ECHO_PASS` : démarrage de l'invocation `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- powershell.exe -EncodedCommand …` démontré.
- `MXC_DOCKER_EXIT_CODE=0` concerne **la commande PowerShell externe**, et non `docker exec` : inspection du script V2 montre qu'il émet `SANDBOX_DOCKER_EXEC_NOT_OBSERVED` après **un code de sortie non nul de `docker exec stat -c '%u' /data/api-key` dans MXC**. L'exécutable Docker était sur PATH (sinon le script aurait émis `SANDBOX_DOCKER_NOT_ON_PATH`). La cause exacte est non observée puisque le script cache toutes les erreurs Docker.
- `NO_MODEL_CALLS_NO_SECRET_READS`, `MXC_DIAGNOSTIC_COMPLETE`, `MXC_PROBE_EXECUTION_COMPLETE`.
- **Conclusions limitées :** l'appel Docker exec sur le fichier de clé a échoué depuis **ce sous-processus sandboxé**. Cela ne garantit ni l'isolement des processus Codex/MCP hors sandbox, ni la protection contre l'héritage de `SUPERMEMORY_API_KEY`, ni l'impossibilité pour le compte Windows opérateur d'utiliser Docker hors MXC. **Ne pas déclarer l'isolation globale PASS.**

**V3 diagnostique préparé, non exécuté sur Windows :** `Test-CodexMxcDockerBoundary-v3-diagnostic-20261031.ps1`, SHA256 `AFEB2060FFC63B352512AC0E900462F95A6BDB75A841DF148599D858F280275F` (artefact de chat hors dépôt GitHub). Une seule invocation MXC, dans laquelle les commandes **lecture seule** `docker version --format` et `docker exec stat` sont exécutées. Leurs codes de sortie sont affichés (pas leur contenu). L'erreur est classée comme accès refusé, daemon/pipe inaccessible, contexte Docker manquant, conteneur non visible ou autre. Aucune clé affichée ; pas de modèle, conteneur/volume modifié, config, hook ni changement Git. Si Docker est accessible par une autre voie, ne pas inférer la sécurité de tout le processus agent. Après ce seul diagnostic ciblé, privilégier une isolation par compte Windows indépendant ou VM avec Docker hôte inaccessible plutôt que des boucles de probes.

## MXC V3 exécutée — résultat définitif de la sonde sur l'identité sandboxée (31/10/2026)

Sortie fournie par l'opérateur, script V3 SHA256 conforme :
`MXC_V3_INTEGRITY_PASS`, `V3_PREFLIGHT_PASS`, `V3_MXC_EXIT=0`, `V3_DOCKER_BINARY=PRESENT`, `V3_DOCKER_DAEMON_EXIT=1`, `V3_DOCKER_DAEMON_UNAVAILABLE`, `V3_DOCKER_EXEC_EXIT=1`, `V3_DOCKER_SECRET_FILE_METADATA_UNREACHABLE`, `V3_DOCKER_FAILURE_CLASS=ACCESS_DENIED`, `V3_INNER_PROBE_COMPLETE`, `V3_SANDBOX_DOCKER_ACCESS_NOT_DEMONSTRATED`, `NO_MODEL_CALLS_NO_SECRET_CONTENT`, `V3_DIAGNOSTIC_COMPLETE`, `MXC_V3_EXECUTION_COMPLETE`.

**Lecture exacte :** la commande sandboxée MXC a trouvé l'exécutable Docker, mais ne pouvait pas atteindre le daemon dans cette invocation ; l'accès `docker exec stat` aux seules métadonnées du fichier `/data/api-key` a aussi échoué (sorties d'erreurs classées **ACCESS_DENIED**). Ceci valide le **refus observé depuis la commande enfant sandboxée**, et non la sécurité de tout le processus Codex, des agents ou des serveurs MCP. L'opérateur hors MXC possède toujours les droits Docker. Le test n'a ni lu la clé ni contacté un modèle. **Clôturer les probes Docker V1-V3 ; ne pas enchaîner d'autres sondes équivalentes.**

## Prototype de broker lecture seule — construit hors production, 31/10/2026

Un prototype Python standard-library-only (artefact de conversation `Supermemory_Readonly_Broker_Prototype_20261031.zip`) est préparé **sans clé réelle, non déployé** : endpoint local `POST /search` authentifié par **jeton distinct et limité**, namespace configuré et verrouillé côté serveur, cible amont fixe `127.0.0.1:6767`, refus des autres méthodes, chemins, champs JSON et redirections. Lecture clé API via fichier distinct côté broker ; aucun secret n'entre dans la ligne de commande, le code ou les journaux. **14 tests unitaires PASS** dans l'environnement de préparation, sur clés factices et amont simulé, aucun accès à Docker ni au vrai Supermemory.

Empreinte archive : SHA256 `C8F52A948C450945994198E427EF857442018AC448F6E38D251EBB2570637DA8`. Contenu : `supermemory_readonly_broker.py`, `tests/test_broker.py`, `README.md`. Ce prototype **ne crée pas** les comptes Windows, ACL, services, pare-feu, isolation réseau, rotation des jetons, rate-limits, audit d'identité ou la passerelle MCP ; **ne pas le déployer en l'état**. La frontière réelle requiert un processus Codex dans un compte/VM qui **ne peut pas accéder à Docker ou à la clé amont**, et un broker de confiance séparé ; le code ne suffit pas. L'adaptateur Python local `e4fd34e` reste intact.

**Prochaine tâche d'intégration (sans nouvelle sonde Docker) :** planifier/qualifier les comptes/ACL/réseau du broker et du runner Codex, compléter l'audit sécurité du proxy, puis la passerelle MCP n'ayant que le jeton limité. Un canary réel Codex↔Supermemory ne commence qu'après un test négatif d'accès à la clé depuis l'identité agent, puis un test positif de lecture et des tests négatifs d'écriture/namespace. Aucune nouvelle installation, migration ou connexion production n'a été réalisée.

## Architecture proposée : deux phases à ne pas confondre

**Phase A — canary purement technique sans secret réel :** après l'audit, tester l'exposition MCP dans Codex CLI depuis un dépôt jetable en `--sandbox read-only --ask-for-approval never`, sans autorisation supplémentaire et avec une clé factice incapable d'accéder aux données de production. Ce canary peut seulement démontrer l'initialisation de l'outil ou un refus d'authentification attendu ; **ce n'est pas une preuve de recherche réelle Codex→Supermemory**. Désactiver les MCP non nécessaires pour réduire le contexte et les accès, sous un profil d'invocation et sans mutation de `config.toml`.

**Phase B — accès réel sécurisé :** un service *broker* de confiance détient la vraie clé hors du processus et des descendants Codex ; le broker contraint côté serveur le namespace et l'unique opération `POST /ns/{namespace}/search` avec validation des paramètres, taille, redirections et gestion des erreurs. Le broker doit opérer **sous une identité/VM réellement séparée**, avec ACL et réseau qui empêchent l'agent Codex d'accéder au volume de production, au socket/daemon Docker, aux fichiers de clé et aux interfaces d'administration. Une simple séparation de processus ou de port `localhost` **ne suffit pas** si les deux processus appartiennent au même compte Windows avec accès Docker. Utiliser un compte/VM sans accès Docker hôte ou une architecture équivalente démontrée. L'hôte ne doit pas accepter de chemins arbitraires ni des méthodes d'écriture ; secrets non transmis en env, arguments, logs ou TOML au processus agent.

Contrôles d'acceptation négatifs obligatoires : recherche sur namespace autorisé OK ; namespace différent refusé ; `POST /document`, `DELETE`, changement de cible/port, redirections et endpoints arbitraires refusés ; vérification du refus d'accès à Docker/clé/partages depuis Codex ; aucun secret transmis aux logs ni à l'environnement agent ; preuve d'un appel MCP par un vrai worker Codex sous garde-fous ; rollback testé. Ne pas affirmer que la sandbox Codex est une frontière de sécurité pour les propres MCP pré-lancés sans le tester.

## Ordre de reprise

1. Collecter seulement les marqueurs du script d'audit ; si le sous-processus sandbox peut atteindre Docker, **ne pas** donner à Codex les secrets de production.
2. Choisir le lieu d'exécution du broker (VM confinée ou compte Windows avec restriction Docker prouvée) et un endpoint en lecture seule ; spécifier ACL et procédures de rollback.
3. Effectuer le canary sans autorisation réelle ou avec un service factice ; puis un canary réel limité, seulement après la qualification de l'isolation.
4. Instrumenter au besoin un test ciblé Supermemory→Ollama pour attribuer les requêtes au bon modèle et contrôler l'egress, sans répéter les tests déjà validés.
5. Synchroniser **sans écraser** la branche locale d'adaptateur (historique distinct du main GitHub), revue indépendante, puis PR du code ; reprendre P1.1, P1.2, P1.4 et P2 autonomie selon la roadmap.

**Interdictions:** aucun `docker compose down -v`, purge de volume, reset Git forcé, écriture de hooks globaux, extraction de clés dans le chat, activation `danger-full-access` sur le poste principal, ni installation supplémentaire avant nécessité validée.
