# P1.1 — Reprise du benchmark par le Codex interactif (TUI)

## Pourquoi cette voie

Deux essais précédents sur `codex exec --json --ephemeral` ont consommé des tokens et n'ont produit **aucune preuve de worker utile** : le premier n'a modifié aucun fichier ; le second a renvoyé `BLOCKED` et n'a pas lu le témoin. Le CLI lui-même et le modèle étaient accessibles, et les configurations / instructions ont été reconnues.

Une session interactive Codex avait, antérieurement, **réellement** lancé un worker qui a corrigé `total.py` dans le dépôt de smoke-test. L'objectif de ce canary est de comparer le **mode d'exécution**, avec une petite tâche équivalente, plutôt que de modifier les permissions ou de relancer `exec` sans hypothèse nouvelle.

**Ne pas interpréter une réussite du correctif comme une preuve suffisante de délégation** : le cycle de vie du worker doit aussi être observé dans le TUI. Le wrapper ne capture pas les messages, événements internes ou journaux du TUI.

## Sécurité et prérequis

- Lancer sur Windows depuis un **terminal interactif**, et seulement après `git pull --ff-only` et tests hors modèle.
- Utiliser le `baseline-home` isolé du pilote `C:\Dev\codex-ab-pr14-pilot-v3`. Il est déjà authentifié ; ne pas dupliquer `auth.json` ni le recopier.
- Répertoire de sortie **nouveau**, externe au dépôt du stack et au pilote `v3`. L'exemple : `C:\Dev\codex-ab-tui-baseline-v1`. Ne pas supprimer ou réutiliser une tentative existante.
- Le wrapper crée un dépôt de test jetable déterministe avec bug de calcul ; seule la modification de `total.py` est autorisée. Le mode est `workspace-write`, approbation `on-request`, sans `--yolo`, sans réseau ou dépendances supplémentaires demandées.
- Le **TUI peut enregistrer son historique de session** dans le `baseline-home` déjà isolé. Le wrapper n'y lit aucun historique et ne sauvegarde aucune conversation.
- Pas de candidate, pas de modification de `~/.codex`, pas de nouveau login, pas de changement de version du CLI ni du modèle dans ce test. Lancement réellement interactif : durée et nombre de tours contrôlés par la fin de session, non par un timeout automatisé. La consigne demande une seule tâche et l'arrêt après vérification.
- Cette session **consomme du quota Codex**, sans garantie de succès. C'est une seule voie alternative motivée par une preuve positive antérieure, pas la répétition du même `exec`.

## Procédure unique

~~~powershell
$ErrorActionPreference = 'Stop'
cd C:\Dev\codex-context-efficiency-stack

git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

python .\scripts\Test-Run-CodexAB-TUI-Canary.py
if ($LASTEXITCODE -ne 0) { throw 'Offline TUI canary tests failed' }

python .\scripts\Run-CodexAB-TUI-Canary.py run `
    --pilot C:\Dev\codex-ab-pr14-pilot-v3 `
    --output C:\Dev\codex-ab-tui-baseline-v1 `
    --execute

Write-Host "TUI canary exit code: $LASTEXITCODE"
~~~

Le wrapper ouvre directement Codex dans le TUI avec le prompt de travail de la baseline. Examiner dans cette interface si un worker **luna-medium** est effectivement lancé, ce qu'il fait, et s'il exécute les tests. **Après le résultat**, quitter le TUI avec `/exit` ; le script lance automatiquement les contrôles déterministes et imprime un JSON anonymisé.

Si la commande échoue ou si le rapport ne peut pas être interprété, le répertoire de test et les fichiers de départ restent présents. **Ne pas relancer** avec le même ou un nouveau dossier sans analyser les résultats.

## Variante expérimentale : approbations Codex désactivées (28 octobre 2026)

**À distinguer de la première exécution :** le TUI de référence a effectivement montré `Started /root/fix_total`, `Completed /root/fix_total` et les tests ont réussi. L'utilisateur a toutefois subi des confirmations répétées de commandes et des demandes de configuration sandbox/admin. Les enquêtes Windows ont identifié **0** événement UAC Operational ID 1 sur la plage inspectée et un `setup_marker.json` **introuvable** dans le profil baseline ; le profil usuel conservait des marqueurs anciens du 29 mars. La causalité des invites n'est pas démontrée.

Le code de ce script accepte désormais `--approval never` pour **une seule invocation interactive**, sans écrire `config.toml` et sans changer la sandbox :

1. Commencer par le préflight ci-dessous. Il vérifie la version Codex, les hashes d'AGENTS et du TOML baseline, puis affiche uniquement les valeurs déclarées des clés `approval_policy`, `sandbox_mode` et `windows.sandbox`. `not_declared` **ne signifie pas** que le moteur Windows n'applique aucune sandbox. Ce contrôle **ne prouve pas** la politique effective du tour TUI.
2. Ne déclencher l'exécution réelle que si le préflight réussit et que le chemin de sortie n'existe pas. Elle consommera du quota, sur un nouveau dépôt Git jetable **distinct** de la première réussite.
3. Le CLI recevra explicitement `--ask-for-approval never --sandbox workspace-write` et `model_reasoning_effort=medium`. Aucune autorisation administrative n'est fournie par le script ; pas de `--yolo`, de `danger-full-access`, de changement `[windows]` ou d'installation.
4. Si un prompt UAC, une demande admin ou une reconfiguration de sandbox apparaît, **refuser et interrompre** le test. Ne pas répéter plusieurs fois ni activer un autre mode de sécurité. Si un outil est bloqué, le worker doit s'arrêter avec `BLOCKED`, sans escalade.
5. À la fin normale du travail, quitter le TUI avec `/exit`, noter si le worker est effectivement apparu dans le panneau Agents, puis lire le rapport de tests. La sortie du script ne vérifie pas automatiquement l'identité du worker et ne prouve pas l'absence de demandes d'autorisation ; l'observation humaine est nécessaire.

### Préflight (zéro appel de modèle)

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

python .\scripts\Test-Run-CodexAB-TUI-Canary.py
if ($LASTEXITCODE -ne 0) { throw 'Offline test failure' }

python .\scripts\Run-CodexAB-TUI-Canary.py policy --pilot 'C:\Dev\codex-ab-pr14-pilot-v3'
if ($LASTEXITCODE -ne 0) { throw 'Policy preflight failure' }
~~~

### Si le préflight s'arrête avant d'ouvrir Codex

Le 28 octobre 2026, le premier `policy` (merge #43) a échoué deux fois avec un message générique. L'utilisateur a tenté `run --approval never` ensuite, mais le lanceur a renvoyé le **code 2** avant l'affichage `START` : aucune nouvelle exécution de modèle n'est observée. **Ne pas réessayer `run` tant que `policy` est bloqué.**

La commande suivante ne lance aucun agent, n'écrit aucun fichier et ne lit que les empreintes de la baseline, la version CLI et trois champs de configuration explicitement autorisés :

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py diagnose --pilot 'C:\Dev\codex-ab-pr14-pilot-v3'
~~~

Le rapport affiche des booléens `baseline_agents_match`, `candidate_agents_match`, `routing_config_match`, `cli_version_matches`, `toml_parseable` et `preflight_ready`. Il distingue maintenant aussi les cas suivants : `baseline_candidate_config_bytes_match`, `baseline_candidate_config_semantics_match` et `candidate_config_matches_record`. Les comparaisons ne révèlent aucun contenu ni empreinte. Il n'affiche **ni empreintes brutes, ni contenu de fichiers, ni logs/session/auth**. Le mode `policy` renvoie désormais un code d'échec prédéfini (`ISOLATED_CONFIG_HASH_MISMATCH`, `CODEX_VERSION_CHANGED`, etc.) au lieu d'une chaîne générique.

- `routing_config_match=false` indique que le TOML baseline n'est pas identique au snapshot de préparation ; ne pas contourner la protection ni écraser l'ancien profil, car cela casserait la reproductibilité.
- Si `candidate_config_matches_record=true` mais `baseline_candidate_config_bytes_match=false`, le changement touche seulement le profil baseline parmi ces deux profils ; ne pas le recopier ni le remettre à zéro avant d'en comprendre l'origine.
- Si les deux fichiers sont identiques mais `candidate_config_matches_record=false`, les deux ont dérivé depuis le snapshot enregistré. Les tests A/B devront repartir sur une **nouvelle paire isolée** avec une nouvelle empreinte immuable, jamais retoucher l'expérience historique.
- Si les fichiers diffèrent en octets mais sont sémantiquement identiques, des changements de formatage restent possibles, sans preuve qu'il s'agisse seulement de cela ; garder le contrôle d'intégrité bloquant.

- `cli_version_matches=false` indique une différence de version ou une vérification indisponible ; vérifier avant toute nouvelle session.
- `toml_parseable=false` signifie que notre nouveau parseur Python n'a pas validé la syntaxe du fichier ; il faut identifier le cas sans l'exposer ni le modifier à l'aveugle.

**N'exécuter la variante `never` qu'après diagnostic clair et nouveau feu vert.** Le test hors ligne ne prouve pas à lui seul que la machine réelle satisfait toutes les préconditions.

### Une unique exécution réelle, uniquement après un préflight réussi

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py run `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v3' `
    --output 'C:\Dev\codex-ab-tui-never-v1' `
    --approval never `
    --execute

Write-Host "Exit code: $LASTEXITCODE"
~~~

L'absence d'invites ne prouvera **pas à elle seule** une autonomie générale. Il faudra combiner : preuve de worker dans TUI, tests/diff, absence de sollicitations humaines et maintien de la sandbox. La vérification sera **une étude de compatibilité de politique**, pas une paire A/B valide pour la PR #14 : le premier TUI utilisait `on-request` et ne constitue donc pas un bras comparable.

**État :** cette section décrit une procédure disponible ; elle ne prétend pas que la variante `never` a déjà été exécutée ou validée.

## V4 — qualification de la sandbox MXC, après échec de `never` sans initialisation (28 octobre 2026)

Résultat observé, à ne pas extrapoler :

- `C:\Dev\codex-ab-pr14-pilot-v4` a été créé avec profils baseline/candidate et un `config.toml` identique ; les fingerprints du préflight `policy` sont conformes.
- La baseline V4 est authentifiée et le TUI `--approval never --sandbox workspace-write` a lancé `/root/total_fix`, mais le worker n'a pas pu lire `total.py`. Aucun fichier modifié ni test Python exécuté. Le menu Windows proposait alors une installation **administrateur**, une sandbox **non administrateur plus risquée** ou Quit.
- L'opérateur a vérifié MXC en **mode CLI sans modèle**, sur la baseline V4 : `codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK`. Résultat `MXC_OK`, code de sortie 0. **MXC est compatible pour cette commande**, sans preuve à ce stade de succès en TUI multi-agent.

La variante `run` accepte désormais l'option **strictement opt-in** `--windows-sandbox mxc`, valable uniquement sous Windows et **pour cette invocation**. Elle ajoute `-c windows.sandbox=mxc` à la commande Codex ; elle ne modifie pas les TOML, les droits Windows, les fichiers d'authentification ni les politiques habituelles. Les arguments restent `--sandbox workspace-write --ask-for-approval never`.

**Ne pas réutiliser** le dossier du TUI V4 précédent. Un nouvel essai est explicitement autorisé seulement après validation des tests hors modèle et avec une sortie neuve :

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

python .\scripts\Test-Run-CodexAB-TUI-Canary.py
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }

python .\scripts\Run-CodexAB-TUI-Canary.py run `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4' `
    --output 'C:\Dev\codex-ab-tui-mxc-v4-baseline-v1' `
    --approval never `
    --windows-sandbox mxc `
    --execute

Write-Host "Code de sortie : $LASTEXITCODE"
~~~

L'exécution TUI utilise du quota ; une seule invocation, sans reprise automatique. Si Codex ouvre encore un menu d'initialisation de sandbox ou une demande UAC/admin, **Quit/Refuser**, ne pas sélectionner le mode sans administrateur ni modifier les réglages. Si le worker échoue à lire le workspace avec MXC, conserver `BLOCKED` et les preuves au lieu de répéter. À l'issue normale, `/exit`, transmettre le rapport JSON et l'observation du cycle de vie du worker / nombre d'interventions.

**Ce test n'est pas un résultat A/B sur AGENTS :** comparer V4 `never` sans MXC à V4 `never` avec MXC contrôle un changement de sandbox. Pour la PR #14 il faudra ultérieurement deux bras avec **exactement le même mode MXC, la même politique d'approbation et la même surface TUI**. Ne pas fusionner #14 avant cela.

## V4 après exécution TUI — dérive du TOML détectée avant l'essai MXC

L'utilisateur a exécuté `git pull` (PR #46), puis **14/14 tests hors ligne réussis**. La commande TUI `--windows-sandbox mxc` s'est ensuite arrêtée **avant `START`**, avec `STOP: ISOLATED_CONFIG_HASH_MISMATCH` (code 2). **Aucune nouvelle tâche du modèle n'a été lancée lors de cet essai.**

Le moteur Codex a pu modifier le TOML lors de la précédente session TUI, mais nous n'avons pas encore confirmé quelles clés ont changé. Pour ne pas entrer dans une boucle de reconfiguration / recréation de profils, le script propose désormais une qualification **strictement bornée** :

- Le benchmark historique reste **immutable** : `benchmark-state.json` et les deux `config.toml` ne sont jamais réécrits. Les contrôles AGENTS et CLI restent obligatoires.
- `diagnose` affiche maintenant `mxc_sandbox_drift_eligible` : vrai uniquement si le TOML baseline diffère au plus par **la valeur `[windows].sandbox`** (ou par un simple formatage) de l'original conservé dans le TOML candidate. Le candidate doit avoir exactement l'empreinte historique.
- Les seules valeurs autorisées pour une différence de `[windows].sandbox` sont : absent, `mxc` et `elevated`. Le mode `unelevated` (repli plus faible) ou `disabled`, toute modification d'agent, de politique, de projet, de MCP, de permissions ou d'une autre clé provoque `STOP: ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED` (code 2) **sans invocation TUI**.
- Le contournement borné demande **à la fois** `--approval never --windows-sandbox mxc --accept-sandbox-key-drift --execute`. L'acceptation ne vaut que pour le **canary TUI baseline**, pas pour un véritable benchmark AGENTS A/B ; aucune reconstitution de l'ancienne configuration n'est prétendue.

Première vérification, sans quota, dans le dépôt du stack à jour :

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py diagnose `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
~~~

Si `mxc_sandbox_drift_eligible=false`, **ne pas lancer de nouveau modèle** : conserver les fichiers et investiguer les champs modifiés en lecture seule. Si `true`, après le contrôle des tests synthétiques, **une seule** nouvelle invocation dans un dossier encore inexistant :

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py run `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4' `
    --output 'C:\Dev\codex-ab-tui-mxc-v4-baseline-v2' `
    --approval never `
    --windows-sandbox mxc `
    --accept-sandbox-key-drift `
    --execute

Write-Host "Code de sortie: $LASTEXITCODE"
~~~

La sortie `baseline_config_snapshot_check=opt_in_sandbox_key_or_format_drift` identifie explicitement le cas accepté ; elle n'est ni une garantie d'accès effectif aux fichiers, ni une validation statistique A/B. Si une fenêtre UAC ou un choix de sandbox réapparaît, **Quit**, sans droits admin et sans mode non-admin à risque.

## V4 — la dérive n'est pas limitée à `windows.sandbox` (29 octobre 2026)

Nouvelle observation locale : `windows_sandbox=elevated`, `candidate_config_matches_record=true`, `mxc_sandbox_drift_eligible=false` et `preflight_ready=false`. Le script de protection a ensuite arrêté la commande `--accept-sandbox-key-drift` avec `STOP: ISOLATED_CONFIG_DRIFT_NOT_ALLOWLISTED`, code 2, **avant l'ouverture du TUI**. Les 18 tests hors ligne ont réussi et aucun nouveau modèle n'a été appelé. Ce résultat signifie qu'au moins une différence sémantique supplémentaire existe ; sa catégorie n'a pas encore été identifiée.

Il serait incorrect de supprimer ou d'assouplir la vérification d'empreinte avant de savoir de quel paramètre il s'agit. `diagnose` expose désormais le champ supplémentaire `redacted_config_drift_categories` : il indique **uniquement des catégories fixes**, par exemple `windows.sandbox`, `projects[*]`, `agents[*]`, `mcp_servers[*]`, `notice[*]`, `features[*]`, `other_config_key`. Les valeurs, chemins de projets, noms MCP, identifiants et clés TOML arbitraires ne sont jamais affichés. L'origine et la légitimité des différences restent à vérifier.

Commande de diagnostic **strictement en lecture seule, sans quota IA ni nouveau test TUI** :

~~~powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
python .\scripts\Run-CodexAB-TUI-Canary.py diagnose `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
~~~

Ne **pas** lancer `run` si `mxc_sandbox_drift_eligible=false`. Les champs supplémentaires servent seulement à choisir une résolution ciblée. Le fonctionnement MXC de `cmd.exe /d /c echo MXC_OK` reste acquis, mais l'autonomie TUI du worker sous MXC est non validée ; PR #14 reste ouverte.

## V4 — récupération auditée du TOML baseline au lieu de poursuivre les exceptions (29 octobre 2026)

Le dernier diagnostic V4 a établi : `candidate_config_matches_record=true` ; catégories modifiées `windows.sandbox`, `projects[*]` et `other_config_key`, `mxc_sandbox_drift_eligible=false`. Toute nouvelle tentative sous `--accept-sandbox-key-drift` reste donc **bloquée avant TUI** ; ne pas désactiver ce contrôle ni poursuivre des exceptions spéculatives.

Le code source officiel Codex inclut des mécanismes persistants de changement de modèle, de notifications et de confiance de projet dans `config.toml` : https://github.com/openai/codex/blob/main/codex-rs/core/src/config/edit.rs. Cela explique pourquoi les changements de configuration peuvent être normaux après une session ; cela ne prouve pas l'origine exacte des trois différences locales.

**Décision :** pour une nouvelle session de qualification, récupérer l'empreinte de configuration *initiale* en restaurant **seulement le TOML du profil baseline isolé V4**, sans créer de V5 ni copier les identifiants d'authentification. Un script dédié exige `--execute`, sauvegarde l'actuel `config.toml` localement dans un dossier d'audit **nouveau** à l'intérieur de V4, vérifie que `candidate-home/config.toml` correspond exactement au hash du snapshot original, contrôle les instructions AGENTS et la version du CLI, puis remplace atomiquement `baseline-home/config.toml` par la copie canonique. Aucune autre donnée n'est écrasée ; aucune donnée privée n'est publiée dans les sorties.

**Important :** fermer auparavant les sessions Codex qui utilisent `C:\Dev\codex-ab-pr14-pilot-v4\baseline-home`. La restauration est un changement **explicite** du profil baseline de test, non une réparation automatique silencieuse. Le contenu archivé peut inclure des chemins privés ou des réglages sensibles : **ne pas le télécharger sur GitHub ou le partager**. Les anciennes traces et rapports restent dans leur emplacement ; ne pas considérer les essais d'avant restauration comme comparables à ceux d'après. Ne pas employer cette procédure sur le `CODEX_HOME` habituel ni sur la candidate.

### Phase 1 — restauration sans modèle

~~~powershell
$ErrorActionPreference = 'Stop'
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }

python .\scripts\Test-Restore-CodexAB-IsolatedBaseline.py
if ($LASTEXITCODE -ne 0) { throw 'Restore synthetic tests failed' }

python .\scripts\Restore-CodexAB-IsolatedBaseline.py `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4' `
    --backup-label 'backup-20261029-before-mxc-v4' `
    --execute
if ($LASTEXITCODE -ne 0) { throw 'Restore refused or failed' }

python .\scripts\Run-CodexAB-TUI-Canary.py policy `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
if ($LASTEXITCODE -ne 0) { throw 'Restored policy preflight failed' }
~~~

### Phase 2 — une seule nouvelle exécution, après réussite de la phase 1

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py run `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4' `
    --output 'C:\Dev\codex-ab-tui-mxc-v4-baseline-after-restore-v1' `
    --approval never `
    --windows-sandbox mxc `
    --execute
~~~

**Éléments à conserver :** JSON final, statut/lifecycle du worker, apparition éventuelle d'une fenêtre UAC, nombre d'interventions. Si MXC échoue encore sur les lectures, arrêtez la qualification ; pas de fallback `unelevated`, pas de `danger-full-access` ni de nouveau rétablissement automatique. La PR #14 reste ouverte ; l'objectif ici est uniquement de tester la viabilité du worker dans MXC.

## 29 octobre 2026 — MXC fonctionnel, worker bloqué par la résolution de Python

Résultats de la dernière expérience baseline V4 restaurée, réalisée sous `--approval never --windows-sandbox mxc` :

- Cycle de vie du worker visible dans le TUI : `Started /root/total_fix` puis `Completed /root/total_fix` ; diff observé de `total.py` limité au calcul `prix * quantite`.
- Le worker a déclaré `BLOCKED` sur **sa propre** exécution de `python -m unittest discover -s tests -q` : `python.exe` résolu via WindowsApps n'a pas pu être lancé dans son contexte d'exécution.
- Le wrapper et son mode `inspect` ont indépendamment exécuté les tests avec `sys.executable` : deux tests réussis, `functional_and_scope_pass=true`, un seul fichier modifié, aucun non-suivi, diff Git valide, CLI code 0. L'utilisateur a également réussi un test **sans modèle** sous la commande `codex -c windows.sandbox=mxc sandbox ... -- $pythonExe -B -m unittest discover -s tests -q` (2 tests réussis, code 0). Donc **Python s'exécute dans MXC avec le chemin absolu**, mais le worker lui-même n'a pas encore vérifié sa correction.
- L'utilisateur pense avoir accepté la première option du menu de provisioning sandbox Windows à un moment donné. Le moment et la politique Windows effectivement appliquée dans le TUI ne sont pas attestés par le wrapper. Ne pas revendiquer d'absence de prompts administrateur ni d'autonomie sans intervention.

### Ajustement borné, sans relâcher la sécurité

Le lanceur accepte une option facultative **`--python-test-fallback-hint`**, seulement avec `--approval never --windows-sandbox mxc` sous Windows. Elle ne modifie ni `AGENTS.md`, ni le prompt baseline original enregistré, ni `config.toml`, ni le chemin d'interpréteur dans l'environnement, ni les ACL Windows.

Le lanceur vérifie que `sys.executable` est un fichier exécutable absolu `.exe` local et **fournit son chemin seulement dans le prompt privé du TUI** (donc susceptible de persister dans le profil isolé). Les sorties JSON et terminal ne publient pas ce chemin. L'instruction transmise au worker exige de :

1. Essayer d'abord `python -m unittest discover -s tests -q` tel que prévu ;
2. Si et **seulement si** cette commande **ne démarre pas**, à cause de la résolution de `python.exe` / WindowsApps, refaire au maximum **un essai** avec l'exécutable absolu communiqué et `-B -m unittest discover -s tests -q` ;
3. **Ne pas réessayer** si les tests échouent par assertion, si la sandbox oppose un refus de politique ou si une opération exigerait des droits supplémentaires. Dans ce cas `BLOCKED`, sans installation, réseau ni modification de permissions.

Cette règle est une **instruction au worker**, pas un mécanisme pouvant garantir ou observer de façon indépendante la fréquence de retries dans le TUI. Les vérifications déterministes du wrapper restent indispensables. Pour une comparaison A/B valide, l'option et le prompt complet doivent être strictement identiques dans les deux bras ; ne pas utiliser les tentatives historiques comme comparateurs.

Préflight hors modèle uniquement (préserver l'expérience en cas de nouvelle dérive) :

~~~powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
python .\scripts\Test-Run-CodexAB-TUI-Canary.py
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
python .\scripts\Run-CodexAB-TUI-Canary.py diagnose `
    --pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
~~~

Aucun nouveau test TUI n'est exécuté automatiquement : tout essai réel doit utiliser un **nouveau** dossier, demander une approbation explicite, et garder `--windows-sandbox mxc --approval never --python-test-fallback-hint`. Ne pas restaurer automatiquement la baseline si Codex la modifie encore ; utiliser seulement la procédure auditée existante, avec opt-in explicite.

## P1.1 — A/B TUI baseline / candidate et autocorrection Python (29 octobre 2026)

Le dernier canary baseline V4 a passé les deux tests et les contrôles Git **indépendants**. Le worker avait corrigé total.py mais n'a pas pu lancer lui-même Python depuis WindowsApps : le chemin absolu de l'interpréteur a ensuite réussi directement sous MXC. La délégation est observée dans le TUI ; la vérification *par le worker*, l'absence d'intervention et la sandbox effective ne sont pas encore démontrées.

Le lanceur accepte désormais `--arm baseline` (défaut) ou `--arm candidate`, avec un prompt, modèle, effort, fixture, politique et mode MXC identiques. L'arm candidate utilise son propre CODEX_HOME/authentification et son AGENTS.md expérimental. Il exige avant lancement que les **deux TOML correspondent strictement au snapshot** et que tous les fichiers de rôles `agents/*.toml` soient identiques entre les homes. Les fingerprints AGENTS/version CLI restent requis, et les overrides de drift sont refusés pour la candidate. Aucun dossier existant ne peut servir de nouveau résultat.

L'option `--python-test-fallback-hint`, strictement opt-in sous MXC + approval=never, ajoute au prompt une unique tentative de repli vers sys.executable quand le premier Python ne peut **pas démarrer**, mais jamais sur un refus sandbox, une erreur d'assertion ou une erreur applicative. Le wrapper ne peut pas attester le nombre de retries du worker ; l'observation du TUI reste nécessaire. Ne pas comparer les anciens runs avec les nouveaux : seules des paires lancées avec la même option sont comparables.

### Contrôles hors modèle à exécuter avant d'autoriser une nouvelle session

~~~powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
python .\scripts\Test-Run-CodexAB-TUI-Canary.py
if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed' }
python .\scripts\Run-CodexAB-TUI-Canary.py diagnose --pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
~~~

Si `preflight_ready=false`, **STOP** : ne pas lancer de worker. Il peut être nécessaire de restaurer **explicitement et avec sauvegarde** le seul TOML baseline selon la procédure auditée précédente, avec une étiquette de sauvegarde neuve. Ne jamais reprendre les mêmes sorties ni restaurer silencieusement. La candidate doit être authentifiée isolément, sans recopier auth.json.

Après un diagnostic valide et une autorisation d'exécution, confirmer séparément `policy --arm baseline` et `policy --arm candidate`, puis lancer **un canary baseline** sur un nouveau workspace avec `--approval never --windows-sandbox mxc --python-test-fallback-hint --execute`. Ne lancer le canary candidate avec les **mêmes flags** que si la baseline réussit et si `policy --arm candidate` passe encore après la session baseline. Chaque exécution consomme du quota. Ne pas faire les deux d'un coup à l'aveugle. Toute invite UAC/admin/sandbox doit être refusée.

Le comparatif nécessite la preuve du worker démarré/terminé, des tests effectués par le worker (et non seulement par le wrapper), zéro intervention manuelle, les vérifications Git/unittest indépendantes et les compteurs par bras. Une seule paire réussie ne valide pas un gain statistique de tokens ou de quota. La PR #14 reste ouverte.
## 29 octobre 2026 — PowerShell ne trouve plus Python dans une nouvelle session

Après mise à jour main vers PR #51, l'utilisateur a tenté d'exécuter le script de qualification dans une nouvelle session Windows PowerShell : chaque commande `python` a produit `Python was not found; run without arguments to install from the Microsoft Store...`, code **9009**. Les 24 tests, le diagnostic et le canary n'ont **pas** été lancés. L'ancien test MXC qui exécutait un chemin absolu vers Python avait réussi, mais cela ne prouve pas que cet interpréteur est encore disponible dans la nouvelle session. L'alias WindowsApps seul n'est pas un interpréteur.

Les commandes avaient été collées une par une dans PowerShell : un `throw` a arrêté uniquement la commande en cours, puis les lignes suivantes ont pu être exécutées manuellement. Un parcours de qualification ne doit donc pas dépendre de vérifications dispersées.

Le nouveau `scripts/Invoke-CodexABTuiQualified.ps1` est un **script unique fail-closed** :

- vérifie effectivement un Python >=3.11 avec `tomllib`, essaie le lanceur Windows `py -3.13`, `py -3`, les exécutions trouvées dans le PATH puis les emplacements d'installation Python classiques ; ne fait confiance ni au simple chemin ni au nom `python`, et refuse un alias Store qui quitte en 9009 ;
- ne fait aucune installation, modification d'alias, privilège UAC, copie d'authentification ni modification de configuration ; il affiche uniquement des statuts, pas les chemins potentiellement personnels de Python ;
- sans option d'exécution, effectue seulement les 24 tests Python, `diagnose` puis `policy` baseline et candidate ; une erreur **stoppe le script entier** avant le modèle ;
- option `-ProbeOnly` : vérifie uniquement Python, sans pilote ni appel Codex ;
- option `-RunBaseline` et `-Output` explicitement requises pour autoriser **une seule** nouvelle exécution TUI, toujours `workspace-write`, `approval=never`, `windows.sandbox=mxc`, repli Python borné. Aucun retry du TUI et aucune restauration de configuration automatique.

### Premier essai recommandé : uniquement préflight sans modèle

~~~powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
& .\scripts\Invoke-CodexABTuiQualified.ps1 -Pilot 'C:\Dev\codex-ab-pr14-pilot-v4'
~~~

Si le script répond `PYTHON_INTERPRETER_UNAVAILABLE_OR_ALIAS_ONLY`, ne pas relancer Codex. Faire un inventaire local de `py -0p`, `Get-Command py,python -All` et des emplacements d'installation ; ne pas lancer l'installeur Microsoft Store sans qualification. Si `V4_PROFILE_NOT_READY`, conserver les fichiers et réutiliser la restauration auditée seulement après analyse.

### Après succès du préflight et autorisation distincte

~~~powershell
& .\scripts\Invoke-CodexABTuiQualified.ps1 `
    -Pilot 'C:\Dev\codex-ab-pr14-pilot-v4' `
    -RunBaseline `
    -Output 'C:\Dev\codex-ab-tui-mxc-v4-selfcheck-baseline-v1'
~~~

Le test n'est déclenché qu'après préflight entièrement validé. Ne jamais réutiliser un dossier existant ; ne pas commencer candidate avant preuve de vérification *par le worker* et contrôles indépendants.
## 29 octobre 2026 — Premier A/B : candidate fonctionnelle mais contrôle Git en échec

La baseline v2 (TUI) passe les tests indépendants et le contrôle Git ; la candidate v1 a bien délégué au worker, effectué le repli Python et passé 2 tests, mais le rapport indépendant indique `git_diff_check_pass=false`. Seul `total.py` est suivi comme modifié et aucun fichier non suivi n'apparaît. **Le gate global reste FAIL** et les fichiers jetables de l'essai doivent être conservés sans correction avant extraction du diagnostic exact. La durée TUI `elapsed_s` inclut l'intervention humaine et ne mesure pas la seule exécution du worker.

La candidate rapporte 20 860 tokens totaux (20 005 entrée + 855 sortie, 56 576 cached en sus) contre 39 185 totaux pour la baseline (38 236 entrée + 949 sortie, 174 336 cached en sus). Ne pas conclure à un gain de quota avec une seule paire, dont une branche a échoué un gate qualité. Les totaux de tokens ne représentent pas le quota de l'abonnement.

Après l'essai, le diagnostic V4 avait une anomalie : `preflight_ready=true` alors que `candidate_config_matches_record=false`. Le préflight a été corrigé afin d'exiger les deux snapshots TOML originaux et l'égalité des configurations. Le lancement candidate avait déjà sa propre validation stricte ; ce correctif aligne le diagnostic hors modèle. Une nouvelle session ne doit jamais être lancée sans contrôles stricts.

**Diagnostic local du contrôle Git (sans appel au modèle, sans modification des fichiers)** :

~~~powershell
$work = 'C:\Dev\codex-ab-tui-mxc-v4-ab-candidate-v1\workspace'
& git -C $work diff --check
Write-Host ('GIT_DIFF_CHECK_EXIT=' + $LASTEXITCODE)
& git -C $work diff -- total.py
& git -C $work status --short
~~~

Ne pas supprimer de fichiers ni appliquer de `git apply --whitespace=fix` avant d'avoir archivé la preuve. Si `git diff --check` rapporte des espaces en fin de ligne, cela reste un vrai défaut du run et non une raison de changer rétroactivement `functional_and_scope_pass=false` en PASS. Le cas échéant, tester une prochaine version du protocole avec le même contrôle pour les deux bras.
## 29 octobre 2026 — Diagnostic exact du premier A/B et préparation d'un v2 équitable

Sur la candidate v1, la sortie locale `git diff --check` donne **`total.py:3: new blank line at EOF.`** (`exit=2`). Le patch de `total.py` corrige correctement l'arithmétique, mais ajoute une troisième ligne vide. Les deux tests Python étaient verts, mais l'acceptation globale du run reste **FAIL** comme enregistré, avec `git_diff_check_pass=false`. Ne modifier ni le dépôt jetable ni son rapport pour transformer rétrospectivement cet échec en succès.

Le diagnostic de drift corrigé par PR #53 signale à juste titre qu'après le run la candidate possède un `config.toml` différent du snapshot original. Pour préparer un éventuel nouveau benchmark, `Restore-CodexAB-IsolatedCandidate.py` fournit un rétablissement **explicitement demandé et archivé** du seul TOML candidate à partir du TOML baseline, sous réserve que ce dernier corresponde octet par octet au SHA d'origine enregistré. La sauvegarde du TOML candidate est écrite dans un nouveau sous-dossier `audit-backups/backup-...`; ni `AGENTS.md`, ni les tokens/authentifications, ni les profils globaux, ni les traces des runs ne sont modifiés. Ne lancer cette restauration qu'avec toutes les sessions V4 fermées, et après les tests hors modèle.

Le contrat du prompt du nouveau TUI est désormais `p1.1-git-diff-selfcheck-v2` **pour les deux bras**. Il demande au worker de lancer `git diff --check` avant de déclarer la tâche terminée, de vérifier que seul `total.py` est modifié et de corriger les lignes vides/espaces introduits, puis de revérifier. Le parent reste superviseur. Cette évolution change le prompt ; les résultats du premier A/B **v1** sont historiques et ne peuvent pas servir de baseline statistique pour un nouveau bras **v2**. Toute qualification v2 exige deux nouveaux runs disposant du même contrat et des mêmes flags, et une vérification indépendante.

### Restauration candidate, strictement hors modèle et seulement sur décision explicite

~~~powershell
$py = 'C:\Dev\Python31314\python.exe'
$pilot = 'C:\Dev\codex-ab-pr14-pilot-v4'
Set-Location 'C:\Dev\codex-context-efficiency-stack'
git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw 'Git pull failed' }
& $py .\scripts\Test-Restore-CodexAB-IsolatedCandidate.py
if ($LASTEXITCODE -ne 0) { throw 'Candidate restore tests failed' }
$label = 'backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss-ffff') + '-candidate-v2'
& $py .\scripts\Restore-CodexAB-IsolatedCandidate.py --pilot $pilot --backup-label $label --execute
if ($LASTEXITCODE -ne 0) { throw 'Candidate restore failed' }
& .\scripts\Invoke-CodexABTuiQualified.ps1 -Pilot $pilot
~~~

Cette procédure ne lance aucun modèle par défaut. Si le TOML baseline lui-même a dérivé, le restore candidate refuse de le prendre comme référence ; ne pas contourner le contrôle. Si les deux profils sont revenus à la référence mais que le workspace affiche une confirmation de confiance, celle-ci reste une **décision manuelle documentée**, non une élévation UAC. Il faudra maîtriser ce facteur dans la comparaison des durées.
## Interprétation des résultats

- `functional_and_scope_pass=true` et comportement worker vu dans TUI : **canary TUI fonctionnel, sous réserve de confirmer visuellement la délégation**. Cela ne valide pas encore l'A/B ni un nombre de runs statistiques.
- `functional_and_scope_pass=true` mais worker non observé : correction fonctionnelle, **contrat de délégation non démontré**.
- `functional_and_scope_pass=false` : échoué, ne pas lancer la candidate ; analyser le rapport et ce qui s'est passé dans le TUI.
- Le champ `worker_delegation_independently_verified` est volontairement `false` dans tous les cas : le wrapper est aveugle au cycle de vie du worker.
- `codex_cli_exit_code=0` n'est pas un succès métier. Les tests et le diff Git sont les critères fonctionnels.

Relire ultérieurement les preuves **sans appel Codex** :

~~~powershell
python .\scripts\Run-CodexAB-TUI-Canary.py inspect --output C:\Dev\codex-ab-tui-baseline-v1
~~~

Le benchmark `AGENTS.md` PR #14 nécessite ensuite des variantes **vraiment comparables**, l'observation de la délégation et plusieurs paires de résultats réussis, pas un unique canary positif. Ne pas fusionner PR #14 sur la base d'une simple correction de calcul.

Référence des flags interactifs : https://learn.chatgpt.com/docs/cli/reference
Incident : https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34
