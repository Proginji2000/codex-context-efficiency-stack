# Broker Supermemory ↔ Codex V3 — prototype borné, qualification hors ligne

**2 novembre 2026.** Livrable de conversation : `Supermemory_Readonly_Broker_MCP_Offline_V3_20261102.zip`, **SHA256 `5CC82DAA00272963F1BA57E2B9BEDA28E1BBD02599DFA53FEE23357E178832A6`**. Le ZIP est un artefact ChatGPT, **pas** un fichier du dépôt GitHub. Son code n'est pas encore installé sous Windows et **aucune connexion réelle Supermemory** n'a été tentée avec ce livrable. Archive dérivée de V2, sans écrasement du stage protégé V2.

## Objectif et limites

Le canary V3 Codex 0.165.0 → MCP Python → broker HTTP **synthétique** a été effectivement qualifié le 02/11 dans la [passation](CODEX_STACK_HANDOFF_2026-11-01.md). Avant toute clé ou API locale réelle, durcir le broker V2 contre les connexions non bornées, les clients lents et les fuites de détails.

Code V3 dans l'archive :
- `broker.py` : `BoundedThreadingHTTPServer`, capacité de **4 handlers simultanés** par défaut (option `--max-connections` 1–16), backlog 8 ; surcharge → HTTP 503.
- Socket timeout inactif 3 s ; durée absolue par connexion 16 s (fermeture du socket par minuteur) ; délai upstream 8 s. Attention : le minuteur ne peut pas tuer un callback Python bloqué arbitrairement, d'où la nécessité ultérieure d'un superviseur Windows/service et de politiques de ressources OS.
- Corps HTTP 4096 octets maximum ; réponse du broker 65536 octets ; query 1000 caractères ; en-têtes ≤32 et somme des champs ≤8192 octets **après** parsing standard de Python.
- Bind exclusivement `127.0.0.1` ; `POST /search` authentifié par jeton client limité ; namespace serveur fixe, API upstream fixe `127.0.0.1:6767/ns/<namespace>/search`, pas de redirection ni write route. `GET /health` non authentifié ; les autres actions sont rejetées.
- `mcp_readonly_bridge.py` : une seule méthode `search(query)`, annotations MCP `readOnlyHint=true`, `destructiveHint=false`, `idempotentHint=true` (**indices descriptifs, pas un mécanisme de permission**). Ne jamais fournir la clé Supermemory dans le bridge/runner.
- `Invoke-BrokerV3OfflineQualification.ps1`, `README.md`, 2 fichiers de tests. Pas de nouvelle dépendance Python tierce.

## Preuve de préparation dans l'environnement assistant

```text
python -I -B -m unittest discover -s tests -q
Ran 36 tests in 12.554s
OK
```

Les 24 tests V2 existants sont conservés, complétés par 12 tests : surcharge (503, puis récupération), contrôle du namespace, limite d'en-têtes, routes d'écriture 405, jeton erroné, limite de débit, masquage d'erreur, réponse upstream excessive, annotations MCP, caractères interdits dans les tokens, expiration d'une connexion lente, limites invalides des workers. Test de déconnexion compatible avec fermeture EOF (Linux) ou reset (Windows). Serveurs de test exclusivement sur ports **aléatoires de 127.0.0.1**, émetteurs simulés. **Aucun Codex, Docker, Ollama, Supermemory réel, accès externe ou secret de production** lors de ces tests.

## Étape suivante : qualification Windows opérateur (pas encore PASS)

- Télécharger le ZIP de la conversation, comparer le SHA256 exact et extraire dans un **nouveau** répertoire de tests de `Downloads`. Refuser toute archive modifiée ou destination déjà existante. Ne pas utiliser `C:\ProgramData\CodexMemoryBrokerStage-V2`.
- Dans un PowerShell ordinaire de l'opérateur, lancer `Invoke-BrokerV3OfflineQualification.ps1` avec son Python 3.13. Le wrapper utilise `-I -B`, neutralise temporairement les variables environnementales `SUPERMEMORY_API_KEY`, `BROKER_CLIENT_TOKEN_FILE` et `OPENAI_API_KEY` pour le sous-processus de tests, puis restaure les valeurs de la session.
- Attendre `BROKER_V3_OFFLINE_36_TESTS_PASS`, consigner la sortie et **STOP**. Ne rien déployer, ne pas redémarrer Docker, ne pas copier les clés ou pousser de branche locale.
- En cas d'échec, collecter les marqueurs et les échecs **sans secrets**, ne pas masquer les tests rouges ni relancer tout le banc historique.

## Gates ultérieurs avant requête réelle

1. Revue des ACL effectives : seul `codex-broker` peut ouvrir la clé Supermemory et le fichier jeton serveur. `codex-runner` n'a que son **jeton client limité**, son bridge et le profil Codex indépendant.
2. Préparation des fichiers de secrets sans exposition à GitHub, logs, commandes, env des agents ni conversation ; rotation, rollback et procédure d'arrêt.
3. Mise en place du service protégé sous `codex-broker` ; health, fail-closed, refus des actions d'écriture / namespace override / mauvais jeton, redaction et sauvegarde des preuves.
4. Seulement après succès : une requête réelle **en lecture seule sur le namespace déjà synthétique** ; aucune donnée personnelle/privée ingérée ou exposée. Aucun test automatique sur namespace production.
5. Gérer superviseur, firewall, règles egress et watchdog. Loopback ne protège pas contre les autres utilisateurs locaux ; annotation MCP ne remplace pas les ACL/autorisation.

**Décision :** V3 **PREPARED_OFFLINE_36_PASS** dans l'environnement de préparation, **WINDOWS_NOT_YET_QUALIFIED**, **PRODUCTION_NOT_AUTHORIZED**. Les tests V1–V3 de l'ancien canary synthétique sont clos et ne doivent pas être rejoués sans changement justifié.
