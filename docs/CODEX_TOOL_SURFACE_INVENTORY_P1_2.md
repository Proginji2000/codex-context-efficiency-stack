# P1.2 — Audit des surfaces d'outils Codex (constats vs exposition réelle)

**État au 28 octobre 2026 :** première passe documentaire et mesure locale anonymisée **prête**. Aucune modification de la configuration Codex, aucun nouvel appel génératif, aucune désactivation MCP ou de plugin.

## 1. Quatre niveaux de preuve, à ne pas confondre

| Niveau | Signification | Mesure actuelle |
| --- | --- | --- |
| **Configuration déclarée** | Entrées \`mcp_servers\` et politiques dans le TOML local | Mesurable sans lancer Codex via \`Get-CodexMcpPolicyAudit.py\` |
| **Catalogue observé** | Nombres affichés à un instant dans l'interface \`/mcp\` | Historique ci-dessous, **pas** preuve de disponibilité actuelle |
| **Connexion et outils découverts** | Serveurs initialisés / outils disponibles dans un runtime précis | Non mesuré pour le tour échoué ; \`codex doctor\` n'est pas une preuve par outil |
| **Exposition effective au modèle** | Schémas d'outils proposés à **un tour** et à un parent/worker | Inconnue ; aucune attribution du coût en tokens |

Un total de noms visibles ne prouve ni que tous les schémas sont injectés dans le contexte d'un modèle, ni qu'ils sont chargés sur chaque tour. La documentation des outils MCP de la **Responses API** ne démontre pas à elle seule le comportement du CLI Codex. L'inventaire statique ne peut donc pas justifier une estimation de gain.

## 2. Instantané déjà relevé dans le projet

Source : \`docs/QUALIFICATION_ROADMAP_2026.md\`, observation de l'interface \`/mcp\` pendant les vérifications précédentes. Les catégories sont **de provenance**, pas des doublons prouvés :

| Origine | Surface | Outils listés à l'époque | Interprétation |
| --- | --- | ---: | --- |
| MCP locaux | \`code-review-graph\` | 30 | Analyse des dépendances/code |
| MCP locaux | \`context7\` | 2 | Documentation |
| MCP locaux | \`node_repl\` | 4 | Exécution JavaScript |
| MCP locaux | \`playwright\` | 25 | Navigateur/tests UI |
| Apps / connecteurs administrés | \`codex_apps\` | **258** | Catalogue applicatif, non détaillé |
| Intégration Codex | \`codex_tui\` | 12 | Outils TUI |
| Intégration Codex | \`cua_repl\` | 3 | Interaction informatique |
| Inactif | \`codex_app\` | 0 | Désactivé dans cette observation |
| En échec | \`oracle_reflex\` | 0 | Non connecté dans cette observation |

*Le nombre d'outils listés est daté et non dédoublonné.* Par exemple, \`node_repl\`, \`cua_repl\` et \`playwright\` servent potentiellement des workflows voisins, mais **aucun doublon effectif n'est démontré** sans comparer leur identité et leurs capacités. Les 258 outils \`codex_apps\` ne sont pas 258 serveurs MCP et ne signifient pas 258 schémas chargés en permanence.

Autre preuve distincte : l'audit TOML du **27/10/2026** trouvait **4 serveurs locaux déclarés activés** et aucun filtrage \`enabled_tools\`/\`disabled_tools\`. Un précédent compteur « 9 » provenait des sous-tables TOML et non de neuf serveurs distincts. Les profils isolés A/B avaient volontairement **aucun MCP**. Le résultat d'échec de leur délégation ne mesure donc aucun coût des quatre MCP du profil habituel.

## 3. Faire l'inventaire de la configuration locale, sans modèle

Depuis la copie Git à jour :

~~~powershell
cd C:\Dev\codex-context-efficiency-stack
python .\scripts\Test-CodexToolSurfaceInventory.py
if ($LASTEXITCODE -ne 0) { throw 'Tests P1.2 failed' }

python .\scripts\Get-CodexToolSurfaceInventory.py
if ($LASTEXITCODE -ne 0) { throw 'Audit P1.2 failed' }
~~~

La commande lit uniquement le \`config.toml\` du \`CODEX_HOME\` en cours (sinon \`$HOME\.codex\`), importe le parseur éprouvé \`Get-CodexMcpPolicyAudit.py\`, puis affiche un JSON **anonymisé** : nombres actuels de serveurs déclarés, transports, politiques, fonction générique déduite de quelques noms connus, **instantané historique étiqueté** et champs explicitement \`null\` pour les mesures non disponibles.

Elle ne lance **ni Codex ni serveur MCP**, ne consulte ni \`auth.json\` ni session, n'utilise ni réseau ni modèle. Elle **ne révèle pas** noms MCP, commandes, arguments, variables d'environnement, URL, tokens ni chemins locaux. Le fichier de configuration n'est pas modifié. L'option \`--config <chemin>\` permet de viser un autre fichier sans changer le profil. Ne pas publier la sortie brute de \`codex mcp list\` ou \`debug prompt-input\` : elles peuvent contenir des informations plus détaillées.

## 4. Politique de profils : proposition, non déploiement

La PR #20 a déjà fourni des wrappers temporaires \`git\`, \`code\`, \`docs\` et \`ui\` (voir \`docs/CODEX_MCP_SCOPES.md\`). Ils ne changent pas les réglages globaux. Les profils proposés restent inchangés :

- **Git** : pas de MCP local de ce groupe requis pour une simple consultation \`git status\`/\`git diff\`.
- **Code** : conserver CRG et Context7, désactiver Node REPL et Playwright uniquement durant la tâche choisie si elle ne nécessite ni navigateur ni REPL.
- **Documentation** : conserver Context7 uniquement parmi ces quatre MCP locaux.
- **UI** : conserver les quatre pour un scénario navigateur pertinent, à confirmer par les tests.

Ces règles ne filtrent pas automatiquement les outils \`codex_apps\` ou les surfaces internes et **ne prouvent aucune économie de quota**. Elles ne doivent pas s'appliquer aux projets sensibles par défaut.

## 5. Voie de validation après le blocage P1.1

Les limites concrètes du runtime \`codex exec\` sont enregistrées dans [l'issue #34](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/34). Ne pas utiliser de nouveaux appels génératifs uniquement pour compter des outils.

Le [protocole app-server](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md) documente \`mcpServerStatus/list\` pour interroger des capacités de serveurs. **Attention** : sans \`threadId\`, une découverte peut créer une connexion au serveur sélectionné ; ce n'est pas un audit statique à effets nuls. Il faut donc le qualifier séparément dans un environnement jetable et autorisé, sans démarrer de MCP de production. L'identification de tous les outils Apps n'est pas garantie par \`app/list\` ; voir [issue upstream #10750](https://github.com/openai/codex/issues/10750).

**Critères de clôture P1.2 :** inventaire par provenance vérifié, métadonnées réelles des outils du runtime obtenues sur session autorisée, exposition effective au parent et au worker contrôlée, absence de régression fonctionnelle en profil restreint, puis seulement chiffrage A/B prudent des tokens/quota. Les deux premiers niveaux sont préparés ou documentés ; les niveaux « runtime » et « modèle » restent à qualifier.

Sources : [OpenAI Docs MCP](https://developers.openai.com/resources/docs-mcp), [API MCP](https://developers.openai.com/api/docs/guides/tools-connectors-mcp), [app-server README](https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md), [issue Codex #10750](https://github.com/openai/codex/issues/10750).
