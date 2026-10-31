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
