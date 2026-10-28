# P1.5 — Pilote dashboard : qualification des workers et skills

**Statut : protocole + données fictives.** La construction React et les essais réels Codex ne sont **pas encore exécutés**. Référence : [issue #38](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/38). L'accès effectif aux outils des sous-agents reste bloqué en `codex exec` : [issue #34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34).

## Objectif

Comparer, à environnement constant, **deux variantes du même workflow dashboard** :

- **A (référence)** : `ui-implementer` + skill existant `frontend-design` si réellement installé.
- **B (candidate)** : exactement la même configuration, plus **le skill shadcn/ui officiel**, installé uniquement dans le projet jetable et confirmé par les traces de l'agent.

Le critère est **la qualité de l'interface fonctionnelle par unité de quota et de temps**, pas la réduction brute de caractères. Si le skill B n'apporte pas d'amélioration démontrée, ne pas en faire une dépendance globale.

## Produit à réaliser

Un **tableau de bord de préparation logistique entièrement fictif**, sans connexion aux systèmes réels.

- En-tête : nom de l'application, état des données fictives, période, dernier filtre appliqué.
- Filtres : date de début/fin (dans la plage du jeu), zone A/B/C ou toutes.
- KPI : commandes préparées, objectif, taux de réalisation, commandes en retard, anomalies et backlog de fin de période.
- Courbe ou barres des volumes préparés et objectifs par jour ; axe, unité, légende et infobulles.
- Tableau d'anomalies agrégées par zone et jour, tri, état vide et accès clavier.
- États : chargement simulé, erreur contrôlée, jeu vide après filtre.
- Affichage mobile 375×812 et bureau 1440×900, sans défilement horizontal involontaire.
- Police, contrastes, focus visible et labels explicites ; accessible sans souris.
- Aucun appel externe en exécution ; données locales figées, aucune télémétrie utilisateur.

## Données et calculs de référence

Fichier unique : `examples/dashboard-pilot/fixtures/synthetic-warehouse-kpis.json`. Il contient **42 lignes fictives** (14 jours × 3 zones), marquées `synthetic_only_no_production_data`. Aucune date ou métrique n'est une valeur réelle d'entreprise.

Définitions obligatoires :

- `prepared` = somme de `orders_prepared` des lignes filtrées.
- `target` = somme de `orders_target` des lignes filtrées.
- `achievement_pct` = `100 × prepared / target` si `target > 0`, sinon non disponible (**ne jamais diviser par zéro**).
- `late_orders` et `anomalies` = sommes des champs correspondants.
- `backlog_end` = somme des `backlog_end` **à la dernière date retenue par zone**, jamais la somme des backlog quotidiens.
- Si aucune ligne ne satisfait le filtre : totaux = 0, pourcentage non disponible, message d'état vide.
- Dates triées, bornes inclusives ; ne pas inventer de valeurs manquantes.

Les calculs doivent être des fonctions pures testables indépendamment de React, avec au moins un cas zéro, un cas zone A et un cas dates multi-zones. Les tests du résultat doivent comparer les valeurs aux agrégations déterministes, pas uniquement vérifier que des éléments HTML existent.

## Stack et contrôle des dépendances

- React + TypeScript en projet jetable ; dépendances installées uniquement après approbation de l'environnement et verrouillées dans un lockfile.
- shadcn/ui Charts utilise **Recharts v3**. Composer avec `ChartContainer`, `ChartTooltip` et composants Recharts ; vérifier la hauteur minimale responsive, les libellés accessibles, le zoom et les axes. <https://ui.shadcn.com/docs/components/base/chart>
- Skill officiel shadcn : <https://ui.shadcn.com/docs/skills>. Inspecter la version / provenance, ajouter dans la copie **B uniquement**, jamais dans le dossier de skills utilisateur.
- Les captures Playwright ne doivent pas être comparées sur des OS/browser non alignés : <https://playwright.dev/docs/test-snapshots>.
- On ne connecte pas CRG, Context7, Playwright ou aucun outil supplémentaire au modèle pour l'A/B tant que leur contribution et leur nécessité ne sont pas explicitement cadrées. Ne pas changer globalement les MCP.

## Acceptation fonctionnelle et qualité

1. `npm ci` sur installation propre, `npm run build`, tests unitaires et contrôles TypeScript/lint définis par le projet : tous verts.
2. Playwright (même OS/navigateur) : plage de dates, choix de zone, KPI recalculés, détails et tri du tableau, retour de l'état vide.
3. Accessibilité : labels de filtres, ordre de tabulation, focus visible, titres hiérarchiques, `aria-live` pour erreur/chargement, contraste acceptable ; ne pas prétendre à un audit WCAG exhaustif avec une capture.
4. Vérification visuelle bureau + mobile, captures datées et hashées après installation approuvée de Chromium ; une capture seule n'est pas une preuve d'interactivité.
5. Aucun secret, identifiant WMS, API privée, connexion réseau ou mutation de projet existant.
6. Une seule branche writer par variante, même fixture et conditions de base, chemins de sortie distincts, préflight vérifiant les versions et les modifications.
7. Trace d'un **worker réellement démarré**, de ses tests et du chargement du skill. Ne pas prendre un compteur `spawn_agent` absent en JSONL V2 comme preuve négative ; croiser avec une interface de suivi fiable. Le parent doit rester orchestrateur.
8. Mesurer succès au premier essai, corrections, temps, tokens rapportés (cache séparé), latence et qualité ; ces compteurs ne sont pas automatiquement des unités de quota Plus.

## Séquence d'exécution

**Étape 0 — acquise avec ce protocole :** fixture fictive + validation pure Python + documentation CI. Aucun modèle ou worker lancé.

**Étape 1 — à qualifier séparément :** mécanisme de délégation fiable (TUI/app-server ou correctif explicite de [#34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34)), preuve de chargement du skill frontend-design, versions/dépendances autorisées. Ne pas refaire le pilote A/B échoué.

**Étape 2 — seulement une fois l'étape 1 passée :** réaliser la variante A dans un dépôt jetable et accepter le résultat ; ensuite réaliser B avec seul changement `shadcn` et répéter l'acceptation. Sans résultat A validé, ne pas dépenser le quota sur B.

**Étape 3 — décision :** conserver la solution minimale qui satisfait tous les critères, enregistrer les preuves dans l'issue #38 et clore P1.5 uniquement après essai runtime.

## Garde-fous

Pas d'installation mondiale, pas de navigateur authentifié, pas d'accès production, pas de déploiement public, pas de nouveau service payant, pas de full access sur hôte Windows. Ne pas fusionner la PR #14 pour ce pilote. Garder P1.1 et P1.2 runtime comme blocages séparés.
