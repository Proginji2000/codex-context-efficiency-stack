# Stack d’optimisation de contexte Codex (Windows)

Guide reproductible pour réduire les tokens/contextes inutiles dans OpenAI Codex **sans baisser le modèle ni l’effort de raisonnement**.

> Testé sous Windows natif en septembre 2026. Les intégrations tierces, surtout les hooks Windows, peuvent évoluer : vérifiez les versions upstream avant de copier un workaround ancien.

## Principe

Le stack traite quatre sources de gaspillage différentes :

```text
Modèle Codex préféré + raisonnement préféré
                    │
        ┌───────────┼───────────┐
        │           │           │
     AGENTS        RTK         CRG
        │           │           │
 comportement   sortie shell   carte du code
        │           │           │
        └───────────┼───────────┘
                    │
        tool_output_token_limit
                    │
                    ▼
             contexte plus propre
```

- **RTK** compresse les sorties terminal.
- **AGENTS.md** impose recherche ciblée, tests ciblés, diffs ciblés et sorties concises.
- **`tool_output_token_limit = 4000`** ajoute une limite native au stockage des sorties d’outils dans le contexte Codex.
- **Code Review Graph** réduit la quantité de code à lire en donnant d’abord au modèle une carte structurelle du dépôt.

## Installation résumée

### 1. Codex

Dans `~/.codex/config.toml` :

```toml
tool_output_token_limit = 4000
```

Gardez votre modèle et votre niveau de raisonnement habituels.

### 2. RTK

Après installation du binaire RTK :

```powershell
rtk init -g --codex
rtk --version
rtk gain
```

Sur Codex/Windows natif, l’intégration est basée sur `AGENTS.md` + `RTK.md` : ne supposez pas une réécriture transparente de toutes les commandes.

### 3. AGENTS global

Utilisez [`templates/AGENTS.md`](templates/AGENTS.md) comme base pour `~/.codex/AGENTS.md`.

Il garde notamment :

- `@RTK.md`
- sorties terminal concises
- recherche avant lecture
- lectures bornées
- tests ciblés pendant l’itération
- validation large aux checkpoints utiles
- diffs ciblés
- pas de relecture inutile
- limitation initiale des sorties inconnues
- CRG en premier quand un graphe existe

### 4. Code Review Graph

```powershell
python.exe -m pip install -U "code-review-graph[communities,enrichment]"
code-review-graph install --platform codex
```

Les extras apportent :

- `igraph` / Leiden pour les communautés
- Jedi pour l’enrichissement Python

Puis, pour chaque dépôt :

```powershell
cd C:\chemin\du\repo
code-review-graph build
code-review-graph status
code-review-graph register C:\chemin\du\repo --alias mon-repo
```

Ensuite privilégiez :

```powershell
code-review-graph update
```

et non des `build` complets répétés.

### 5. Vérifier MCP

Redémarrez Codex après modification du MCP, puis envoyez :

```text
/mcp
```

`code-review-graph` doit apparaître.

### 6. Anciennes sessions

Pour une conversation Codex déjà ouverte avant les nouvelles instructions, envoyez **une seule fois** :

```text
Relis maintenant les instructions globales Codex présentes dans ~/.codex/AGENTS.md ainsi que le RTK.md qu'elles référencent. Applique immédiatement leur version actuelle à cette session et à toutes les étapes suivantes.
```

Ne répétez pas ce texte à chaque prompt.

Si le MCP CRG n’apparaît pas dans `/mcp`, redémarrez Codex ou ouvrez un nouveau runtime/thread.

## Git et CRG

Dans un dépôt Git, CRG indexe les fichiers suivis. Un `.gitignore` propre peut donc réduire énormément le graphe.

Cas anonymisé testé :

```text
Avant nettoyage : ~2 057 fichiers parsés
Après Git + .gitignore : 86 fichiers parsés
```

Soit environ **95,8 % de fichiers retirés du graphe**, tout en conservant le code utile et ses relations.

Le message important : avant d’empiler encore des optimiseurs, nettoyez ce que l’agent peut voir.

## Mesure

```powershell
rtk gain
code-review-graph status
code-review-graph detect-changes --brief
```

Cherchez surtout :

- moins de logs/diffs géants
- moins de relectures inutiles
- CRG avant les scans massifs
- tests ciblés pendant l’itération
- validation complète aux bons moments

## Windows

Deux pièges sont documentés dans le README anglais :

1. Python Microsoft Store peut installer `code-review-graph.exe` dans un dossier `Scripts` absent du PATH.
2. Certaines versions CRG ont généré des hooks shell Unix sous Windows ; inspectez `~/.codex/hooks.json` et utilisez [`templates/hooks.windows.json`](templates/hooks.windows.json) uniquement si nécessaire.

## Vie privée

Avant publication, anonymisez systématiquement :

- noms d’utilisateur
- chemins absolus
- projets privés
- noms de branches internes
- tokens et clés API
- chemins de profils navigateur
- IDs runtime
- exports CRG bruts

Le guide complet, les commandes de diagnostic et les sources sont dans le README anglais.
