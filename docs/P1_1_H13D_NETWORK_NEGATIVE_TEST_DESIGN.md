# P1.1 — H1.3d : conception de qualification réseau MXC (aucune connexion réelle)

**État au 29 octobre 2026 : PLAN_ONLY_NO_NETWORK_OR_PROCESS.** H1.3c contrôlé a obtenu un PASS Windows réel. Ce document prépare la **qualification distincte du réseau** mais ne l'atteste pas. Aucune machine ou service personnel n'est contacté par les scripts de cette PR.

## Références épinglées

- [Codex `rust-v0.165.0` — `codex-rs/mxc-sandbox/src/policy.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/policy.rs) : `network_enabled = permissions.network_sandbox_policy().is_enabled()`, `proxied = command.managed_network.is_some()`. Par défaut, le policy compiler envoie `NetworkAction::Deny` pour l'egress si le réseau n'est pas activé ou si un réseau géré est présent. Lorsqu'il y a un proxy géré, des exceptions **loopback** `127.0.0.0/8` et `::1/128` peuvent être créées.
- [Schéma officiel `rust-v0.165.0` `codex-rs/core/config.schema.json`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/core/config.schema.json) : `allow_local_binding` vaut **true par défaut sous MXC**, car MXC ne peut pas imposer `false` dans ce paramètre. Ainsi, un contrôle unique de loopback ne permet pas d'inférer l'interdiction d'accès Internet.
- H1.2 : l'écho réel `network_access=false` décrit la politique **déclarée**, sans preuve d'application au système d'exploitation. H1.3a : comportement de confinement des écritures CLI autonome PASS. H1.3c : trois descendants contrôlés ont été observés et terminés par le **harnais** dans un Job Windows ; Codex auto-cleanup non attesté.

## Hypothèses et risques

Un échec réseau peut provenir de la sandbox, mais aussi d'une panne DNS, d'un routage absent, d'un pare-feu du serveur, d'un timeout, d'un endpoint hors ligne, d'un proxy ou d'un refus applicatif. Aucun de ces échecs ne prouve à lui seul qu'une politique de sécurité s'est appliquée. De même, une connexion vers `localhost` peut être autorisée par la conception MXC.

Une affirmation d'isolation sans vérifier l'activation du réseau géré, le choix du backend, l'accès positif du parent vers **exactement la même cible**, l'émission effective de la tentative par l'enfant, et le refus attribuable à une règle OS/proxy serait trompeuse.

## Matrice d'acceptation H1.3d

Le fichier `scripts/Plan-CodexAB-H13DNetwork.py` n'a **aucun mode réel de connexion** ; le seul mode supplémentaire `--simulate` confirme qu'un rapport fabriqué est rejeté. `scripts/Test-Plan-CodexAB-H13DNetwork.py` utilise uniquement des valeurs fictives.

Le futur contrôleur devra, **avant toute exécution réelle** :

1. Déterminer si le test doit démontrer l'interdiction de l'**egress direct** ou la médiation par **proxy géré**, avec preuve de `network_access=false` et de la configuration effectivement appliquée. Ces deux régimes ne doivent pas être confondus.
2. Choisir **un endpoint numérique non-loopback explicitement contrôlé par l'opérateur**, temporaire, sans secrets ni dépendance à un service externe non maîtrisé. L'endroit où le construire (hôte local non-loopback, homelab isolé ou autre machine contrôlée) est à qualifier séparément : pare-feu, NAT et exceptions de réseau privé peuvent invalider le test. **Aucun endpoint n'est encore sélectionné ni autorisé.**
3. Établir un contrôle positif du **parent non sandboxé** qui peut joindre la même IP, le même port et le même service **pendant le même créneau**.
4. Prouver indépendamment la tentative effective du processus sandboxé et l'absence d'un autre chemin de contournement (proxy non autorisé, DNS, fallback, tunnel).
5. Obtenir un refus **explicitement attribuable à la politique OS ou au proxy configuré**, idéalement avec une preuve indépendante de l'agent de contrôle. Le simple retour `timeout`, `connection_refused`, `dns_failure`, `unreachable` ou `proxy_error` ne compte jamais comme preuve de refus.
6. Contrôler indépendamment qu'aucune connexion sortante du canary n'a atteint la cible témoin, tout en tenant compte de la fiabilité de l'observateur. Si elle a été atteinte, STOP — ne jamais attribuer un PASS à ce cas.
7. N'autoriser **qu'une** séquence bornée, non administrateur, dans les mêmes dossiers temporaires jetables que H1.3a, avec un CLI épinglé et sans modèle ou `turn/start`. Lancer un test de réseau réel **uniquement après une nouvelle validation explicite de la cible et des conditions**.
8. Ne pas afficher de données réseau privées (IP, ports personnels, identifiants, journaux ou tokens) ni modifier les paramètres réseau globaux. Si la preuve manque, statut **INCONCLUSIVE/STOP**, pas PASS.

La matrice est **plus stricte que l'observation d'un simple appel `connect()` refusé** : même un échec explicitement reporté doit être corroboré par le contrôle de politique indépendant. L'outil de plan ne peut pas transformer son propre succès de tests en preuve réseau réelle : ses sorties gardent `real_network_egress_verified=false`.

## Décision et interdictions

**H1.3d : non démarré en réel / non qualifié.** Le prochain jalon autorisé est la validation CI offline de la matrice et de ses critères d'échec. Ne lancer ni service socket, ni connexion externe, ni modèle, ni benchmark A/B à l'occasion de cette PR.

Les jalons H1.3b (parité app-server `turn/start`), provenance des workers, nettoyage automatique Codex, containment réseau et PR #14 restent bloqués ou séparés. Issues de suivi : [#61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61), [#34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34).
