# Passation operationnelle — Codex Stack IA & Autonomie — 31 octobre 2026

**Etat rapporte et verifie par sorties de PowerShell fournies dans ChatGPT, non par acces distant au PC.** Ce document prolonge [la passation du 30 octobre](CODEX_STACK_HANDOFF_2026-10-30.md) et la [roadmap](QUALIFICATION_ROADMAP_2026.md), sans remplacer leurs historiques de qualification. Il sert a reprendre le projet apres saturation d'une conversation.

## Priorite

Finaliser l'integration **Supermemory Local 0.0.9 ↔ Codex CLI** en **opt-in, projet autorise, lecture seule en premier**, sans modifier les hooks globaux ni divulguer la cle API. Ne pas relancer installations, tests anciens ni benchmarks P1.1. Le pilote VM/full-access demeure ulterieur.

## Code Codex Supermemory — etat du 31 octobre

- Depot : `Proginji2000/codex-context-efficiency-stack`.
- **Branche uniquement locale sur le PC operateur**, non poussee sur GitHub : `codex/supermemory-local-adapter-20261030`, HEAD `e4fd34e` (`fix: harden scoped local Supermemory MCP adapter`). Le commit parent est `972d6dd` (fusion locale de `origin/main` a `fa51ccb8`), et l'adaptateur avait ete cree en `6765c68`. **Ne pas supposer que la branche/code de l'adaptateur est disponible sur GitHub.**
- Six fichiers codes/docs suivis ; securite corrigee (routes API, `query`, redaction de secrets JSON imbriques, opt-in lecture seule, endpoint 127.0.0.1:6767 fixe, revalidation namespace, erreurs MCP, validation longueurs).
- Tests rapportes : Python **16/16 PASS**, tests du lanceur PowerShell PASS, **23/23** scripts de syntaxe PASS, `git diff --check` PASS. Aucun test live Codex↔MCP jusqu'ici. `scripts/__pycache__/` reste non suivi : ne pas nettoyer automatiquement.
- `~/.codex/config.toml` et `~/.codex/hooks.json` SHA256 **UNCHANGED** par rapport aux valeurs historiques. Hooks `SessionStart` et `PostToolUse` a preserver.
- En attente de qualification : fuite possible de cle transmise en environnement aux descendants Codex ; aucune exposition a des donnees sensibles avant decision d'architecture de secrets. Ne pas activer l'ecriture automatique.

## Supermemory Docker — etat et preuves

- Image `docker.io/supermemory/supermemory:0.0.9`, conteneur `supermemory-supermemory-1`, `running/healthy` apres redemarrage.
- Volume production : `supermemory_supermemory-data` monte dans `/data`. API hote uniquement sur `127.0.0.1:6767`. NE JAMAIS supprimer ce volume, ni lancer `docker compose down -v`.
- Controle Compose vs runtime : **9/9 MATCH** : `OPENAI_BASE_URL=http://host.docker.internal:11434/v1`, modeles `OPENAI_MODEL`, `OPENAI_FAST_MODEL`, `OPENAI_TEXT_MODEL=qwen3:8b`; embeddings provider `local`, modele `Xenova/bge-m3`, dimensions `1024`; telemetry et update check demandes a `1`. Ces variables ne prouvent ni l'inference effective ni l'absence de trafic cloud.
- API authentifiee et recherche semantique synthetique avaient ete validees le 30/10. Aucune capture automatique des sessions Codex.
- **Sauvegarde a froid** le 31/10 : `C:\Users\Quentin\AppData\Local\SupermemoryBackups\snapshot-20261031-003115` : 60 fichiers, **935945989 octets**. Copie des fichiers `compose.yaml`, `compose.override.yaml`, `.env` dans `config` ; cle et identite sous `data`. Ce repertoire **contient des secrets ; ne jamais l'envoyer dans le chat ou sur GitHub**.
- `SUPERMEMORY_COLD_BACKUP_PASS` ; service `healthy` apres restart. Restauration du contenu dans volume distinct, comparaison `diff -qr`, suppression du volume test : `SUPERMEMORY_RESTORE_CONTENT_PASS`.
- **Restauration applicative PAS ENCORE validee.** Essai V1 : defaut de quoting Go templates Docker dans le cleanup ; V2 : application restauree `unhealthy`/quitte ; V3 : `RESTORED_EXIT_CODE=1`, `RESTORED_OOM_KILLED=False`, `RESTORED_HEALTH=unhealthy`. Categorie de logs potentiels : modele/cache et stockage/permissions **non conclusives**. Instance restauree sans reseau, ni port publie.
- Cleanup de l'essai V1 : `RESTORE_ORPHAN_CLEANUP_PASS`. Inventaire final : **0** conteneurs test / **0** volumes test selon filtre `label=openai.supermemory.isolated-restore-check`.
- Production `docker exec id` : `uid=10001(supermemory)`, `gid=10001(supermemory)` ; `/data` **10001:10001 mode 700** et `/data/api-key` **10001:10001 mode 600**. Le clone V1-V3 a ete reconstruit par un conteneur utilitaire execute en root depuis un repertoire hote NTFS. **Hypothese forte non encore prouvee : proprietaires des fichiers restaures devenus root:root, rendant /data inaccessible au serveur non-root.** Ne pas conclure que les donnees sont corrompues ou que le LLM est responsable.
- Emplacements testes `/data/.cache`, `/data/cache`, `/root/.cache`, `/home/node/.cache` : NOT_VISIBLE_OR_ABSENT. Ne pas en conclure que tous les caches de modeles sont absents.

## Nouvelle tentative V4 et correctif V5 (31/10, apres la presente passation)

- **V4 NON VALIDEE**. La commande de l'operateur a rencontre un dossier d'extraction deja existant (garde initiale declenchant `STOP`), puis a continue ligne par ligne malgre les erreurs. Le ZIP d'origine et le script local ont toutefois passe leur verification SHA256 ; il ne faut pas traiter le `Write-Host SUPERMEMORY_V4_PASS` manuel comme preuve de succes.
- V4 a cree un volume temporaire et lance la copie ; `docker /bin/sh -c` a echoue avec `syntax error: unexpected end of file (expecting \")\")`. Cause de script : expression shell `\"$(stat ...)\"` dans un programme multiligne transmis par l'interface native de **Windows PowerShell 5.1**, dont le passage de guillemets ne preservait pas le code. Aucun `RESTORED_TEMP_OWNERSHIP_PASS` n'a ete obtenu ; l'hypothese ownership reste **ouverte**, pas prouvee.
- Le script V4 a affiche `ISOLATED_CONTAINER_CLEANUP_PASS` et `ISOLATED_VOLUME_CLEANUP_PASS` apres l'echec, mais un nouvel inventaire externe des orphelins n'a pas encore ete realise a cette date.
- **V5 preparee, pas encore executee sur Windows**. Fichier `Test-SupermemoryIsolatedAppRestore-v5-ownerfix.ps1` (artefact de conversation), SHA256 `712B7A2DAFA208CCC7B0E78B7F69A62FFE283FCE01E089EBA445F05DAEBDCC86`. ZIP `Supermemory_Restore_V5_20261031.zip`, SHA256 `8D8B27F6E32FEB7A767D0C00FDF5A70C5C8D7621372B95C057DFC5D39B5B57EB`. Les scripts POSIX extraits ont passe `sh -n`, plus controle statique des chemins de montage ; **aucun PASS Docker/PowerShell effectif revendique**.
- V5 monte des petits fichiers shell LF/UTF-8 via bind Docker, executes avec `/bin/sh /tmp/restore.sh` et `/bin/sh /tmp/read.sh`, plutot que de transmettre le programme multiligne via `-c`. V5 doit restaurer et comparer le volume clone, corriger **uniquement sur clone** vers UID/GID 10001:10001 et les modes 700/600, tester health/API sous isolation, puis nettoyer les ressources temporaires.
- Prochain retour demande : **sortie V5 et son marqueur interne `ISOLATED_APP_RESTORE_FULL_PASS` seulement si reellement emis par le script**. Si health echoue apres permissions corrigees, la prochaine analyse ciblera les erreurs au demarrage, sans exposer les logs bruts ni assouplir sans motif l'isolation reseau.

## Prochain gate : tester les droits uniquement sur volume temporaire (V5)

1. Garder la production en marche ; verifier `healthy`, image, montage, et integrite des fichiers de sauvegarde sans lire les secrets.
2. Creer un nouveau volume temporaire nomme/labelise avec nonce. Copier le snapshot, comparer les fichiers **avant correction des metadonnees**.
3. Dans le **volume temporaire uniquement**, `chown -R 10001:10001 /dest`, `chmod 700 /dest` et `chmod 600 /dest/api-key` ; verifier uid/gid/modes. Ne pas modifier source Windows ni volume production.
4. Demarrer le conteneur Supermemory restore isolé (pas de port publie, `--network none`). Son absence d'acces a Ollama peut bloquer l'initialisation : si l'application echoue encore, diagnostiquer sans afficher de logs bruts et **sans assouplir le reseau par defaut**.
5. Si healthy, faire une lecture API authentifiee depuis sidecar `--network container:<test>`, puis nettoyer conteneur et volume temporaires, verifier l'absence d'orphelins. Eviter les faux PASS : un `Write-Host` lance apres erreur ne constitue pas une preuve.
6. Ensuite seulement, verifier effectivite BGE-M3 verrouille, routage reel Qwen3/Ollama, et absence de trafic exfiltrant ; puis canary Codex MCP scope/code en lecture seule ; decision sur secrets et PR du code.

Les scripts diagnostiques V1-V3 sont des artefacts de la conversation, **pas** des fichiers suivis dans le depot GitHub. Ne pas reexecuter sans raison les sauvegardes et canaries deja acquis.

## Autres priorites et limites

- Serena 2.1.0 (LSP et memoire intersessions) et shadcn MCP conditionnel etaient deja valides, PR #91/#92 fusionnees.
- `P1.1` reste EN QUALIFICATION ; PR #14 toujours ouverte. V3 4/4 canaries fonctionnelles mais economie de quota non demontree. Ne pas fusionner #14 sans preuve complementaire.
- P1.2 exposition effective MCP, P1.4 autocorrection, P2 multi-writers/worktrees, P3 VM confinee et P4 full access restent ouverts selon la roadmap ; priorite actuelle = Supermemory et securite.

## Si le chat s'interrompt

Reprendre a partir de ce document, de `docs/QUALIFICATION_ROADMAP_2026.md`, du code **local** au commit `e4fd34e` et des dernieres sorties PowerShell. Demander uniquement la sortie non sensible du test **V4 droits de la restauration isolee**, pas les secrets, dumps de conteneur ou env files. Ne jamais supprimer des caches ou dossiers non suivis par automatisme.
