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
