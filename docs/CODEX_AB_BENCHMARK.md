# Protocole A/B de la PR #14 : AGENTS.md sans modification globale

**Etat : outillage de comparaison prepare, aucun run Codex A/B realise.** La comparaison statistique ne vaut pas preuve d'economie de quota ChatGPT. Le script ne lance aucun modele, ne lit pas les historiques Codex et ne modifie ni la configuration, ni les depots.

## Objectif

Comparer l'ancien `AGENTS.md` (baseline actuellement validee) et la variante candidate de la [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14) sans confondre reduction de caracteres, tokens du CLI, cache et quota abonnement.

Pour une decision :
- utiliser **un depot jetable**, toujours au meme commit initial, avec la meme tache et les memes tests ;
- comparer deux environnements Codex isoles, avec authentification propre et configurations identiques **sauf le contenu d'AGENTS.md**. Ne jamais copier `auth.json`, des jetons ou des repertoires de session ;
- conserver la meme version CLI, le meme modele, effort, prompt, MCP, sandbox, et le meme nombre maximal de workers ;
- alterner l'ordre des executions : paire 1 baseline/candidate, paire 2 candidate/baseline, paire 3 baseline/candidate. Chaque execution part d'une copie propre du depot de test, sans reutiliser les changements precedents ;
- exiger une **delegation reelle** et la conservation du parent Luna en orchestrateur, les memes tests, la meme politique d'autorisations, et aucun contournement de sandbox ;
- noter les evenements `turn.completed` et les compteurs emis, en distinguant les `input_tokens` totaux, `cached_input_tokens` et `output_tokens` ;
- chronometrer la tache complete : `stream_processing_elapsed_s` du filtre n'est **pas** la latence totale ;
- ne jamais compenser un echec du modele candidate par un changement de tache ou un modele plus puissant sans en faire un essai distinct.

**Important :** une installation globale du candidat, une modification du fichier existant `~/.codex/AGENTS.md` ou la fusion de #14 sont exclus de ce protocole de preparation. Valider d'abord localement la possibilite d'isoler les instructions avec les mecanismes documentes du CLI installe. Eviter toute substitution implicite d'authentification ou de configuration. Les commandes d'invocation finales seront confirmees apres ce preflight.

## Collecte autorisee et minimisation des donnees

Pour chaque nouveau run explicitement lance sur une copie jetable, le filtre existant `scripts/Convert-CodexExecUsage.ps1` sait absorber la sortie `codex exec --json` et ne rend que des compteurs. Les evenements JSONL **bruts** (contenant instructions, commandes, traces ou identifiants de session) ne sont jamais archives dans ce protocole.

Les resultats de tests, le controle de delegation, les retries et la duree sont constates independamment de ces compteurs. Seuls les chiffres agreges et les booleens d'acceptation entrent dans le fichier local d'essais, jamais les prompts, sources, chemins sensibles ou sorties de commandes.

## Format du fichier local anonymise

Creer un JSON avec `schema_version: 1` et `runs`. Chaque run contient les champs ci-dessous ; remplacer les exemples par des observations reelles, sans inventer de compteurs. Les deux empreintes `agents_sha` correspondent aux contenus des deux variantes et doivent differer ; la meme empreinte est conservee pour tous les runs d'une variante.

```json
{
  "schema_version": 1,
  "runs": [
    {
      "pair": 1,
      "arm": "baseline",
      "case_id": "smoke-total-01",
      "controls": {
        "cli_version": "0.164.0",
        "model": "luna-medium",
        "reasoning_effort": "medium",
        "sandbox": "workspace-write",
        "repo_head": "50fa713ca6fa753a11eb435eb4b6f76cd447b57",
        "mcp_profile": "all",
        "prompt_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
      },
      "agents_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "success": true,
      "delegated": true,
      "parent_orchestrated": true,
      "safety_pass": true,
      "retries": 0,
      "elapsed_s": 10.0,
      "usage": {
        "complete_turns": 1,
        "turns_with_usage": 1,
        "failed_turns": 0,
        "input_tokens": 1000,
        "cached_input_tokens": 200,
        "output_tokens": 30
      }
    }
  ]
}
```

**Ceci est un exemple synthetique, et non un resultat de Codex.** Ajouter une execution `candidate` pour chaque paire et au moins trois paires (six executions) pour atteindre le minimum du comparateur. Les champs `controls` doivent etre strictement identiques, y compris `prompt_sha256` calcule sur le prompt identique. Le comparateur rejette les paires incompletes, les numeros discontinus, les champs inconnus, les donnees invalides et les contrôles differents. Ne copier que les six champs de `usage` visibles dans l'exemple a partir du rapport anonymise du filtre existant.

## Analyse hors-ligne et validation

Depuis PowerShell, a la racine du depot local a jour :

```powershell
python .\scripts\Test-Compare-CodexAB.py
python .\scripts\Compare-CodexAB.py --input C:\chemin\vers\essais-ab-anonymises.json
```

Le script renvoie des medianes par variante, variations relatives des tokens entrants **non caches** et du temps, et une qualification :
- `behavior_or_usage_regression` : echec, violation de la politique, delegation manquante ou usage incomplet ;
- `insufficient_repetitions` : moins de trois paires ;
- `metrics_inconclusive` : au moins une deterioration detectee (entree non cachee, duree au-dela du seuil heuristique +15 %, retries) ;
- `manual_review_candidate` : trois paires completes, aucune regression observee selon ces criteres. **Cela n'autorise ni une fusion ni le deploiement.**

Le script ne connait ni la facturation, ni les quotas de l'abonnement, ni la representativite de l'echantillon. Les variations en pourcentage ne sont que des observations sur cette tache. Plusieurs taches distinctes et un controle humain seront indispensables avant de conclure.

## Prochaines etapes apres cette PR

1. Qualifier un moyen de lancer les deux variantes dans deux environnements propres sans recopier des secrets ou changer l'environnement Codex global.
2. Faire valider le script localement et la CI synthetique; inventorier les outils effectivement exposes lors d'un run suivant le meme protocole.
3. Lancer trois paires sur la tache jetable avec un budget de quota explicite, puis comparer les preuves comportementales et le rapport.
4. Si l'optimisation n'apporte pas de gain robuste ou de precision equivalente, laisser la PR #14 ouverte et conserver la version en place.

Voir aussi [roadmap](QUALIFICATION_ROADMAP_2026.md), [filtre CLI](CODEX_EXEC_USAGE.md), [mesures](MEASUREMENT.md) et [profils MCP](CODEX_MCP_SCOPES.md).
