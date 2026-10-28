# P1.5 — Outillage facultatif pour développer des dashboards

**Objectif validé par l'utilisateur (28 octobre 2026) :** enrichir le **stack d'agents de développement Codex**, afin que les workers disposent des bons outils lorsque le développement d'une interface, d'un tableau de bord ou de graphiques est demandé dans un **projet réel**.

**Hors périmètre :** produire un dashboard autonome, lancer un projet React fictif, fabriquer des KPI, connecter des données WMS ou effectuer un benchmark de dashboards sans demande métier. Le pilote synthétique de PR #39 provenait d'une interprétation incorrecte ; il n'est **pas** un livrable à poursuivre. Les éventuels résidus dans l'historique Git ou dans le dépôt ne constituent aucune demande de développement.

## Candidats à qualifier — ne pas confondre outils et bibliothèques

| Catégorie | Candidat | Utilité pour les agents | Déclencheur |
| --- | --- | --- | --- |
| Skill de design | `frontend-design` | Concevoir des interfaces lisibles et cohérentes ; **déjà intégré en option** | UI, CSS, responsive, dashboard |
| Worker dédié | `ui-implementer` | Déléguer le périmètre frontend à un spécialiste | Une tâche UI concrète |
| Skill de composants | Skill officiel shadcn/ui | Trouver/configurer les composants adaptés aux besoins UI | Projet utilisant ou choisissant shadcn/ui |
| MCP de composants | MCP officiel shadcn/ui | Découvrir les registres et installer des composants lorsqu'un accès outillé est réellement utile | Besoin de recherche/installation de composants ; optionnel |
| Test navigateur | Playwright MCP ou suite Playwright Test | Vérifier interactions, captures, mobile et accessibilité de base | Frontend exécutable à valider |
| Bibliothèque de graphiques | Recharts, composant Chart shadcn/ui | Implémenter des graphiques React simples/usuels | Besoin de graphiques dans un projet React |
| Bibliothèque de graphiques | Apache ECharts | Graphiques complexes, gros volumes ou flux interactifs si démontrés nécessaires | Volumétrie ou fonctionnalités avancées |
| Plateforme de supervision | Grafana | Dashboards d'infrastructure, métriques et observabilité | Projet de monitoring, pas application React générique |

**Important :** Recharts, ECharts et Grafana ne sont pas des MCP ou skills équivalents. Ils ne doivent pas être installés globalement « pour préparer » le stack. Le worker choisit la bonne technologie selon le contexte de la tâche.

## Fonctionnement attendu de Codex

1. **Détection du besoin :** un projet comporte une vraie tâche UI ou dashboard. Sinon aucun outil dashboard supplémentaire n'est chargé, et aucun projet de démonstration n'est lancé.
2. **Délégation ciblée :** Luna reste orchestrateur ; il affecte la tâche à `ui-implementer` avec des limites de fichiers et des critères d'acceptation.
3. **Chargement paresseux :** le worker prend `frontend-design` s'il est installé ; il utilise le skill shadcn/ui et éventuellement le MCP seulement lorsque la stack et le besoin le justifient. Éviter d'exposer tous les schémas d'outils dans chaque conversation.
4. **Choix des bibliothèques :** en fonction de la stack réelle et des caractéristiques des données, sans imposer React, ECharts ou Grafana à tous les projets.
5. **Vérification :** build, tests, interactions, responsive et accessibilité proportionnés à la demande et au risque. Le résultat est qualifié seulement avec des preuves du worker et des outils effectivement utilisés.
6. **Sécurité :** aucune installation globale, désactivation MCP, extension de permissions, connexion métier ni dépense de quota pour une démonstration non sollicitée.

## Qualification sans développer d'application

**P1.5 (outillage) peut avancer sans créer de dashboard :**
- inventaire de la disponibilité des skills/roles/MCP dans les fichiers du stack et dans les résultats locaux déjà fournis ;
- revue du périmètre officiel des candidats, des compatibilités, versions et conditions d'installation ;
- protocole de chargement à la demande, de sélection par type de projet et de retour arrière ;
- tests statiques pour éviter de charger des skills UI sur les tâches non UI ;
- validation réelle uniquement lorsqu'une **demande de développement UI/dashboards** apparaît, ou si l'utilisateur autorise explicitement un test fonctionnel.

La qualification réelle des workers dépend encore du blocage de délégation `codex exec` dans [l'issue #34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34). Ce blocage ne doit pas être résolu en créant un produit fictif sans objectif.

### Sources à vérifier lors de l'installation

- Skill shadcn/ui : https://ui.shadcn.com/docs/skills
- MCP shadcn/ui : https://ui.shadcn.com/docs/mcp
- Composants Charts : https://ui.shadcn.com/docs/components/base/chart
- Apache ECharts : https://echarts.apache.org/handbook/en/get-started/
- Grafana : https://grafana.com/docs/grafana/latest/
- Playwright : https://playwright.dev/docs/intro

**Critère de fin de P1.5 :** outillage documenté, installable à la demande avec versions et retour arrière connus, règles de dispatch/load conditionnelles correctes et tests statiques verts. Ne pas confondre cette qualification d'outillage avec la réalisation d'un dashboard métier.
