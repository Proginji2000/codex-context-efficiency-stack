# P1.1 — H1.3c Windows Job Object : descendants contrôlés et nettoyage du harnais

**État : lanceur expérimental opt-in, tests CI synthétiques uniquement. Aucune exécution native Windows de ce nouveau contrôle n'a encore eu lieu.**

## Dépendances déjà attestées

H1.2 réel : `thread/start` app-server conforme pour **permissions déclarées uniquement**. H1.3a : sous Windows non-admin, CLI Codex **0.165.0**, test autonome `codex sandbox` MXC `:workspace` **PASS** pour comportement d'écriture : contrôle hôte externe accessible, écriture dans le workspace, tentative de création extérieure refusée, parent confirme sentinelle inchangée. Résultat `STANDALONE_MXC_FILESYSTEM_NEGATIVE_PASS_NOT_APPSERVER` sur main `e21f22abd0fffa20be63e98abb9b006f306583f4`. Aucune preuve d'isolation réseau, de parité app-server, de terminaison exhaustive des descendants ou de workers. [#61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61), [#34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34).

## Problème à résoudre

Le fait que `subprocess.Popen().wait()` ou le processus CLI principal termine ne prouve pas que ses descendants ont tous disparu. Une preuve exige une **observation OS indépendante**, différente des affirmations du modèle, du CLI ou d'une suppression de fichiers temporaires.

Le code épinglé [`rust-v0.165.0 codex-rs/cli/src/debug_sandbox.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/cli/src/debug_sandbox.rs) attend effectivement son enfant `child.wait().await`, tandis que [`mxc-sandbox/src/native.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/native.rs) attend le processus MXC natif. Ceci **ne suffit pas** à attester le cycle de vie de tous les processus descendants.

## Nouveau protocole H1.3c — sans modèle

Lanceur `scripts/Probe-CodexAB-H13CJobTree.py` :

1. **Par défaut `PLAN_ONLY_NO_PROCESS`**. Le test réel exige `--execute-local-job-tree-probe`, uniquement sous Windows non-admin et avec la version figée du CLI ; aucun `turn/start`, auth, session, worker IA ni benchmark.
2. Utilise `core.disposable_probe_root` de H1.3a : nouveau dossier temporaire **sous le profil utilisateur mais hors TEMP système**, nouveau `CODEX_HOME`, workspace et trois scripts Python factices. N'accède à aucun projet tiers et ne modifie aucun profil Codex global.
3. Test de compatibilité MXC préalable `MXC_OK`, stdout exact, sortie 0 et **stderr vide**. Toute anomalie STOP sans lancer le test descendants.
4. Crée un Windows Job Object **privé** avec `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. Lance son propre processus racine Python avec `CreateProcessW(CREATE_SUSPENDED)`, l'assigne au Job **avant** `ResumeThread` pour éviter la fenêtre de création d'un descendant hors Job. Tout échec d'affectation => STOP, sans réclamer UAC ni ajouter `CREATE_BREAKAWAY_FROM_JOB`.
5. La racine lance **une seule** commande CLI `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- ...`. Dans MXC, un enfant Python original crée **un seul** petit-fils dormant et annonce ses deux PID via une petite réponse JSON dans le workspace jetable ; aucun réseau ni accès aux données personnelles.
6. Le parent lit les PID **uniquement en mémoire**, interroge `QueryInformationJobObject(JobObjectBasicProcessIdList)`, vérifie que **racine, enfant et petit-fils** sont simultanément présents dans le Job et vivants via `OpenProcess`/handles Win32. Le programme ne divulgue aucun PID, nom de compte, chemin ou sortie brute.
7. **Le harnais lui-même** appelle `TerminateJobObject`. Il attend que les handles des trois processus observés soient signalés et que la liste des PID actifs du Job soit vide. Toute observation manquante, race, timeout, impossibilité d'ouvrir un handle ou descendant persistant => STOP. Cette terminaison forcée **ne prouve pas** que Codex nettoie spontanément tous ses enfants.
8. En `finally`, fermeture ciblée des handles et du Job, nettoyage des dossiers jetables. Les règles `KILL_ON_JOB_CLOSE` demeurent actives même si le harnais rencontre une erreur pendant le contrôle. Aucun contournement des Job Objects imbriqués, aucune élévation et aucune modification de configuration Windows n'est autorisé.

**Résultat admissible si tout passe :** `H13C_CONTROLLED_JOB_DESCENDANTS_TERMINATED_BY_HARNESS_PASS`. Il signifie uniquement que les descendants **contrôlés** ont été observés dans **notre** Job Object et terminés par **notre** harnais. Le programme doit continuer à publier `codex_automatic_descendant_cleanup_verified=false`, `unknown_descendant_escapes_independently_excluded=false`, `complete_child_tree_cleanup_independently_attested=false`, `worker_provenance_verified=false` et `appserver_turn_mxc_verified=false`.

**Risque de plateforme :** MXC peut imposer des règles de création de processus ou de Job Objects imbriqués incompatibles avec ce test. En cas de `ROOT_JOB_ASSIGN_FAILED`, `READY_TIMEOUT_OR_INVALID` ou `PROCESS_HANDLE_QUERY_FAILED`, **STOP**. Ne pas désactiver les protections, ne pas modifier les Jobs hérités et ne pas demander les droits administrateur. Un échec signale un contrôle non qualifié, pas nécessairement une vulnérabilité.

## CI et autorisation

`scripts/Test-Probe-CodexAB-H13CJobTree.py` teste la classification des sorties **fabriquées** : preuves manquantes/dupliquées/mal typées, liste de processus incohérente, descendant absent, handles non signalés, Job non vide après terminaison, confidentialité, option par défaut inerte et construction des commandes épinglées. La CI Python 3.13 Windows + Ubuntu **n'invoque jamais le vrai Job Object ou Codex**. Cette PR n'exécute aucune opération sur le PC de l'opérateur.

**Étape suivante :** seulement après CI PASS, fournir une commande PowerShell locale avec branche et SHA épinglés, contrôle d'arbre Git propre, tests synthétiques, puis **une seule** invocation `--execute-local-job-tree-probe`. Revenir avec le code de résultat, sans relancer automatiquement. Ne pas fusionner [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14) ni lancer les 12 essais A/B.
