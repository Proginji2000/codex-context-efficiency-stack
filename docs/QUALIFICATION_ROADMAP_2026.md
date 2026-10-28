# Feuille de route de qualification Codex, dashboards et VM isolee

**Reference : 28 octobre 2026.** Projet : `codex-context-efficiency-stack`. Ce document est un backlog vivant : ajouter de nouveaux P1/P2/P3 apres les resultats sans retrograder des blocages connus. Priorite = importance et dependances, pas pourcentage d'avancement ni date de livraison.

## Objectif et principes non negociables

Maximiser le **travail de developpement reussi et verifie par unite de quota et de temps**, en conservant un orchestrateur Luna qui delegue les taches de fond a des workers specialises et des controles deterministes (build, tests, lint, diff).

- Ne pas considerer la taille d'un fichier AGENTS, un nombre d'outils MCP ou un compteur `input_tokens` comme une preuve de consommation de quota Plus.
- Ne pas modifier les instructions globales, la configuration des serveurs MCP, les projets sensibles, les permissions Codex, ni installer de skill/MCP sans essai en scope isole et retour arriere.
- Preferer le controle par etapes : observations -> benchmark comparable -> decision -> deploiement graduel.
- Git et les tests sont plus fiables que des rapports de workers ou les fichiers `STATE.md` non mis a jour.
- Parent Luna = orchestrateur, non executeur. Un writer par perimetre. Conserver branches, fichiers locaux, worktrees, secrets et preuves.
- `danger-full-access` n'est **pas** un objectif immediat ni un droit sur l'hyperviseur ou le reseau local : uniquement une option de fonctionnement ulterieure **dans une VM fortement isolee**.

## Baseline observee (en dehors des tests synthetiques)

- Codex CLI `0.164.0`, authentifie par ChatGPT sur Windows; une mise a jour `0.165.0` etait proposee, mais non installee pour ces tests.
- Sur le depot isole `codex-autonomie-smoke-20261028`, une session Luna a effectivement lance `/root/fix_total` et un worker a corrige `total.py`. Verification independente : 2 tests `unittest` OK, `git diff --check` OK, seul `total.py` est modifie parmi les fichiers suivis.
- Un autre worker a effectue des **appels MCP** : CRG `list_repos_tool` OK (le depot de test n'etait pas indexe), Context7 consultation publique OK, Node REPL `2+3=5` OK, Playwright navigation `about:blank` et `browser_snapshot` OK apres installation de Chromium et correction locale sauvegardee de la configuration.
- Un worker de reprise read-only a retrouve HEAD `50fa713ca6fa753a11eb435eb4b6f76cd447b57`, la modification locale, le `STATE.md` obsolete, et 2 tests reussis sans re-ecrire le code. Fichiers non suivis `__pycache__`, `tests/__pycache__`, `.playwright-mcp/` observes, non supprimes.
- Worktree `audit-1` cree puis retire **reellement** par l'utilisateur, la branche `codex/audit-1` restant conservee. La vague de deux worktrees distincts a ete verifiee uniquement sur un depot de test synthetique : l'execution simultanee de deux vrais writers Codex n'est pas encore prouvee.
- Quatre serveurs locaux declares dans `config.toml` : `code-review-graph`, `context7`, `node_repl`, `playwright`. Dans l'interface runtime `/mcp` : ces quatre connectes avec respectivement 30, 2, 4 et 25 outils. Autres observations : `codex_apps` connecte (258 outils), `codex_tui` (12), `cua_repl` (3), `codex_app` desactive (0), `oracle_reflex` en echec (0). Le total de schemas effectifs charges par tour et leur cout en tokens **restent inconnus**.
- Les PR #20 (profils MCP par invocation), #21 (gestion sure des worktrees), #22 (planificateur de deux writers) sont fusionnees; PR #14 (AGENTS reduit) est ouverte, **non deployee**. Taille candidate : 19 846 -> 12 977 caracteres (-34,6% du texte, **pas des tokens**).
- Premiere capture CLI connue : 108 273 `input_tokens` incluant 80 384 caches, 259 `output_tokens`. **Pas** d'attribution a une couche ni de mesure de quota abonnement.

## P0 — Stabilite, securite et reference de mesure (avant toute nouvelle optimisation globale)

| ID | Tache | Acceptation / preuve |
|---|---|---|
| P0.1 | Figer un rapport de qualification V1 et le perimetre reellement teste | Resultats directs et limites ci-dessus; aucune revendication de multi-writer ou d'autocorrection apres permission refusee |
| P0.2 | Etablir le benchmark de reference sur un depot jetable : CLI, config scopee, agent/role, MCP runtime, tests, latence, retries, compteurs de tokens disponibles | Resultats de taches **reussies**, meme commit et prompt; distinguer cache et quota; pas d'historique prive ingere |
| P0.3 | Definir la politique d'autorisations Windows actuelle et le retour arriere | `workspace-write` + `on-request` par defaut pour projets courants; aucune elevation globale non validee; revue des chemins sensibles |
| P0.4 | Examiner le depot de smoke-test avant nettoyage | Examiner `.playwright-mcp/` et caches non suivis; ne rien supprimer sans avoir determine leur utilite |

**Gate P0** : baseline fiable et commande de restauration documentee. P0 n'impose pas l'arret du Codex deja utilisable.

## P1 — Optimisations et fonctionnalites a impact eleve

| ID | Tache | Critere d'acceptation |
|---|---|---|
| P1.1 | **PR #14** : comparer ancien/nouveau `AGENTS.md` dans deux sessions propres, parametres constants et vraie delegation | Comportement equivalent, tests OK, pas de regression du contrat orchestrateur; rapport de compteurs + cache + duree; fusion seulement apres preuve et accord |
| P1.2 | Expliquer les **258 outils `codex_apps`**, plus `codex_tui`/`cua_repl` et doublons MCP, sans desactiver aveuglement les outils utilisateur | Inventaire par famille, provenance, outils effectivement exposes aux tours; configuration scopee ou profil code-only uniquement si A/B justifie |
| P1.3 | Benchmark reel des profils `git/code/docs/ui` de la PR #20 | Memes taches reussies avec et sans restrictions, sans MCP necessaire manquant; aucun gain quota invente |
| P1.4 | Qualifier l'autocorrection et les permissions | Test volontaire de fail local recouvrable, diagnostic autonome, correction, tests relances, zero escalade inutile; blocage securite non contourne |
| P1.5 | **Dashboard skill pilote** : reutiliser `ui-implementer` + `frontend-design`, comparer un skill specialise shadcn/ui **au seul skill existant**, sur un projet React jetable | Vrai dashboard avec KPIs, filtres, etats vide/erreur, graphes, ergonomie mobile, a11y; build, tests et captures Playwright; aucune nouvelle dependance globale par defaut |
| P1.6 | Metriques de qualite et quota par tache (CSV/report existant, enrichissement si verifie) | Temps reel, 1er essai, retries, escalades, erreurs de permissions, outils appeles et usage expose; pas de scraping de sessions privees |

**Gate P1** : reduction de contexte sans degradation, outil dashboard valide, premiers gains prouves au lieu de supposes.

## P2 — Autonomie durable et fiabilite de l'ecosysteme

| ID | Tache | Critere d'acceptation |
|---|---|---|
| P2.1 | Deux workers **Codex reels** dans deux worktrees propres sur depot jetable; integrations et cleanup controle | Trace de deux sous-agents, perimetres exclusifs, tests, controle des changements, integration verifiee; branche conservee; pas de suppression forcee |
| P2.2 | Boucle multi-essais bornee, reprise d'echec, gestion des threads satures | Diagnostic une fois, retry borne, reutilisation des workers ou stop propre, pas de parent takeover |
| P2.3 | Diagnostiquer `oracle_reflex` (server `failed`) | Cause locale redigee sans secrets; retour a un `connected` et appel non destructif **uniquement dans un environnement autorise**, ou desactivation scopee apres decision |
| P2.4 | Qualification du worker UI et de Playwright sur un dashboard complet | Traces d'utilisation reelle de `ui-implementer`, skill charge si installe, screenshots et interaction, acces clavier, responsive, composants testes |
| P2.5 | Capacites de graphiques selon le type de dashboard | React produit : shadcn/ui Charts (Recharts); grandes series/temps reel : ECharts sous benchmark; metriques d'infrastructure : Grafana. Ne pas installer les trois sur tous les projets |
| P2.6 | Assurance GitHub et securite avant PR, tests isolés, Gitleaks si disponible | Gate de revue independante, statuts CI, fichiers secrets rediges, aucune modification de projets proteges sans delegation explicite |
| P2.7 | Reprise et handoffs longs / interruptions / etats obsoletes | Worker retrouve Git/STATE/PR/test, detecte contradictions, aucune perte de travail ou recomputation systematique |
| P2.8 | Verification des mises a jour de Codex CLI et des plugins sans migration precipitée | Journal versions, compatibilite role/MCP/sandbox, test canary, retour arriere |

**Gate P2** : stack utilisable sur de vrais developpements avec incidents recuperables, tests et preuves reproductibles.

## P3 — Candidature VM Codex isolee (planification seulement tant que P0-P2 non acceptes)

Le futur objectif utilisateur est un environnement **Codex avec acces etendu a l'interieur d'une VM**, pour limiter les restrictions inutiles sur des developpements autorises. Ce n'est **pas** l'octroi de droits sur l'hyperviseur Proxmox, le PC Windows principal, les shares multimedia ou le LAN.

| ID | Tache | Critere d'acceptation |
|---|---|---|
| P3.1 | Cadrage des besoins VM : Linux/Windows, CLI/Desktop, acces navigateur, outils CI, CPU/RAM/disque disponibles, charge Proxmox actuelle | Fiche de choix et dependances; pas de VM provisionnee sans decision |
| P3.2 | Isolation : VM non privilegiee sur hyperviseur, VLAN/bridge dedie, firewall deny-by-default inbound, acces sortant limite, aucun routage vers LAN de confiance | Tests reseau negatif/positif, aucun partage host, pas d'acces API Proxmox ni Docker socket du host |
| P3.3 | Identites et secrets : compte non root, token GitHub a permissions minimales, gestionnaire de secrets hors repo, acces temporaires et rotation | Aucun secret du PC hote, pas de cle SSH large, journaux sans secret, possibilite de revocation |
| P3.4 | Reversibilite : template propre, snapshot apres provisioning, sauvegarde config et depots, reinitialisation/reinstallation repetable | Retour a un etat sain verifie et documente |
| P3.5 | Installation **en mode restreint** du stack dans la VM | Tests baseline, quatre MCP utiles et Playwright selon besoin, parity de build/reprise, rapport de differences Windows/Linux |

**Gate P3** : VM confinee et recuperable, pas seulement une VM qui demarre.

## P4 — Pilote `full access` confine, puis exploitation

| ID | Tache | Critere d'acceptation |
|---|---|---|
| P4.1 | Examiner options `workspace-write`/approbation auto vs `danger-full-access`; justifier l'exception | Historique de blocages reelement dus au sandbox, plutot qu'un choix de confort |
| P4.2 | Sur **clone jetable de VM seulement**, ouvrir un profil full-access **limite a cette VM** | Ecriture, install/test et outillage autorises; impossibilite de toucher host, LAN, depots critiques, secrets non montes |
| P4.3 | Verifier menaces agentiques et flux reseau | Test d'exfiltration simule avec donnees factices, rules egress, acces aux depots, prompt injection, rollback |
| P4.4 | Operer avec des permissions et points d'arret adaptes aux actions irreversibles | Merge/production/secrets/mutation hors depot toujours sujets a des gates explicites |
| P4.5 | Migration graduee de projets pilotes et documentation finale | Un projet non sensible accepte; mesures de rendement; plan de repli vers PC actuel |

**Gate P4** : acces etendu contenu dans le guest, corrigeable et auditable. Ne jamais assimiler `--yolo` a un mode securise.

## P5 — Extensions si les mesures les justifient

- Spec Kit pour grands projets a exigences ambiguës : installation par projet, jamais pour micro-corrections.
- Skill dashboard avance / registry privee, eventuel MCP shadcn **scope au projet** (apres le test du skill et mesure du contexte); ne pas ajouter un MCP global par defaut.
- Visualisation temps reel des marches et des points de trade, exploitation et KPI WMS/WSR, dashboard Proxmox/Grafana : cas d'usage de validation distincts, sans connecter de donnees sensibles a des services non approuves.
- Comparaisons de routeurs ou petits modeles decisionnels, plus grand context window, compression/context proxy : seulement avec donnees A/B positives.
- Alignement eventuel Claude Code et documentation multi-plateformes apres stabilisation.
- Journal d'evaluation des nouveaux chantiers P2/P3 decouverts en cours de tests : leur classification peut evoluer selon la gravite.

## Proposition initiale de stack dashboard

**Choix recommande** :
1. Pour un dashboard d'application React : conserver `ui-implementer` + `frontend-design` (skill existant), evaluer d'abord le **skill officiel shadcn/ui**, composant Charts/Recharts et Playwright; scope par projet.
2. En cas de besoin de gros flux de donnees et graphiques interactifs haute frequence, evaluer **Apache ECharts** par benchmark sur le vrai volume; ce n'est pas automatiquement un MCP.
3. Pour supervision Proxmox, services et runners : **Grafana** avec tableaux versionnes, sans en faire un framework UI d'app.
4. Le **MCP shadcn/ui** officiel sait chercher et installer des composants de registres, mais reste **facultatif** : d'abord prouver l'insuffisance du skill, puis mesurer le schema/tool overhead avant toute connexion. Ne pas dupliquer CRG/Context7 inutilement.

Sources officielles (revues le 28 octobre 2026) :
- https://ui.shadcn.com/docs/skills
- https://ui.shadcn.com/docs/mcp
- https://ui.shadcn.com/docs/components/base/chart
- https://echarts.apache.org/handbook/en/get-started/
- https://grafana.com/docs/grafana/latest/administration/provisioning/
- https://learn.chatgpt.com/docs/agent-approvals-security
- https://developers.openai.com/api/docs/guides/agents-api/environments/security

## Prochaine action technique

Commencer par P0.2/P1.1 **sans installer d'outil supplementaire** : definir un protocole A/B reproductible de la PR #14 a partir des traces deja disponibles, puis choisir une tache courte et non sensible sous quota consenti. En parallele (sans appel de modele), inventorier les familles `codex_apps` observables et etablir le pilote dashboard sur projet neuf; ne rien desactiver tant que l'impact n'est pas mesure.

**Definition de done globale** : Codex reussit des taches reelles, delegue aux bons workers, corrige les erreurs ordinaires, preserve les permissions/secrets et les projets, mesure les effets sur quota/temps et reste recuperable apres crash ou interruption. Un pilote VM full-access n'est admissible qu'apres toutes les gates precedentes.
