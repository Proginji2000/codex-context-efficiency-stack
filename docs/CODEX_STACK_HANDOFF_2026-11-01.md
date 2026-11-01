# Passation opérationnelle — Codex Stack IA & Autonomie — 1 novembre 2026

**État fondé sur les sorties PowerShell communiquées par l'opérateur ; aucune connexion distante au PC.** Historique détaillé : [passation du 31 octobre](CODEX_STACK_HANDOFF_2026-10-31.md), [roadmap](QUALIFICATION_ROADMAP_2026.md), [broker V2](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

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
