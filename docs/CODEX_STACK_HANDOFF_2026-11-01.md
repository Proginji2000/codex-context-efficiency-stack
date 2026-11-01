# Passation opérationnelle — Codex Stack IA & Autonomie — 1 novembre 2026

**État fondé sur les sorties PowerShell communiquées par l'opérateur ; aucune connexion distante au PC.** Historique détaillé : [passation du 31 octobre](CODEX_STACK_HANDOFF_2026-10-31.md), [roadmap](QUALIFICATION_ROADMAP_2026.md), [broker V2](SUPERMEMORY_BROKER_MCP_V2_STAGE_20261031.md).

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
