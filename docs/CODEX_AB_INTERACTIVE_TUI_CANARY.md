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
