# P1.1 — Faisabilité de l'observation TUI et préparation de benchmarks représentatifs

Date : 29/10/2026. **Pas d'appel IA, pas de nouvelle campagne et pas de fusion de la PR #14.** Conclusions fondées sur le code source **épinglé `openai/codex rust-v0.165.0`** et le lanceur P1.1 V3 du dépôt.

## Résultat technique : impossibilité de joindre passivement le backend TUI V3 tel que lancé

Le TUI v0.165.0 connaît trois cibles : `AppServerTarget::Embedded`, `LocalDaemon` et `Remote` ([`tui/src/lib.rs` lignes 328+](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/tui/src/lib.rs)). Le code `start_app_server` instancie un client `InProcessAppServerClient` pour `Embedded`, et une connexion réseau/socket pour `LocalDaemon` ou `Remote`.

La découverte ou réutilisation implicite du démon est **désactivée** par `daemon_startup::config_exclusion` quand les overrides CLI `-c` contiennent autre chose que certains réglages de fonctionnalités et TUI. [Source exacte](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/tui/src/daemon_startup.rs). Le TUI de notre lanceur [`Run-CodexAB-TUI-Canary.py`](../scripts/Run-CodexAB-TUI-Canary.py) utilise `-c windows.sandbox=mxc` et `-c model_reasoning_effort=medium` ; ces deux clés sont **hors allowlist**. Dans [`startup_orchestration.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/tui/src/startup_orchestration.rs), `reuse_implicit_local_daemon = daemon_exclusion.is_none()` et la sélection de la cible retombe alors sur `Embedded` en l'absence d'endpoint distant explicite. Notre wrapper ne fournit aucun endpoint distant.

**Conclusion bornée :** dans le contrat V3 connu, un *nouveau* processus app-server indépendant n'aurait pas accès au flux live des workers du processus TUI **in-process**. Une connexion non destructive et passive à ce TUI particulier n'est **pas une capacité démontrée ni proposée**. Les quatre anciens runs restent des preuves fonctionnelles avec observation humaine, mais **pas des attestations automatiques d'événements workers**. Nous ne tentons pas de lire/rejouer les sessions `CODEX_HOME` pour contourner cela.

Il existe des modes `LocalDaemon` et `Remote`, ainsi que les notifications app-server v2 (`collabAgentToolCall`, `subAgentActivity`, `thread/tokenUsage/updated`), mais leur disponibilité sur un **serveur partagé** ne garantit pas une diffusion à un second client ni la parité des garanties MXC. Un futur banc d'essai pourrait être fondé sur un client app-server supervisé **dès le départ**, sous nouveau contrat, sans supposer une capture passive rétroactive.

## Nouvelle batterie offline : trois classes

`scripts/Plan-CodexAB-RepresentativeFixtures.py` introduit trois fixtures **entièrement synthétiques** :

| Cas | Classe | Files modifiables | Critères initiaux |
|---|---|---|---|
| `arith-control` | Contrôle mécanique, un seul module | `total.py` | Correction de la somme prix × quantité, tests et diff Git |
| `device-reconcile` | Réconciliation multi-module de matériel fictif | `labels.py`, `inventory.py` | IDs normalisés, écarts bidirectionnels, doublons par source, tests |
| `python-fallback-policy` | Diagnostic d'incident et politique d'autocorrection simulée | `fallback.py` | Une tentative de secours uniquement sur `FileNotFoundError`; jamais sur refus politique ou erreur de test |

Les jeux de données de matériel sont **fictifs**, sans lien avec SOTI/Reflex réels ni données professionnelles privées. Les cas B/C sont volontairement cassés ; **leurs unit tests doivent échouer avant correction**. Aucun programme ne commande une installation, un accès réseau, une session Codex, une élévation ou une sandbox.

Le mode défaut affiche uniquement un JSON de plan :

```powershell
Set-Location 'C:\Dev\codex-context-efficiency-stack'
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Plan-CodexAB-RepresentativeFixtures.py
```

`--materialize` est un choix **distinct et explicite**. Il crée trois dossiers jetables **nouveaux**, en dehors du dépôt, chacun comprenant `manifest.json` et `workspace/` Git initialisé/commité. La commande ne doit être utilisée qu'après le préflight et la décision de préparer des fichiers de tests ; **elle ne lance aucun modèle** :

```powershell
& 'C:\Dev\Python31314\python.exe' -B .\scripts\Test-Plan-CodexAB-RepresentativeFixtures.py
if ($LASTEXITCODE -ne 0) { throw 'Offline fixture tests failed' }
# Exemple futur facultatif, jamais lancé automatiquement :
# & 'C:\Dev\Python31314\python.exe' -B .\scripts\Plan-CodexAB-RepresentativeFixtures.py --output-base 'C:\Dev\codex-ab-representative-v1' --materialize
```

Le **contrat `p1.1-representative-fixtures-design-v1` est un DESIGN**, pas un contrat déjà exécuté. Aucun verdict sur AGENTS.md ne peut en découler avant un runner sécurisé **nouveau** offrant prompts et contrôles identiques, espaces distincts baseline/candidate, alternance d'ordre, validations indépendantes et arrêt au premier échec.

## Conditions de la future campagne (non autorisée ici)

1. Confirmer le mécanisme d'événements app-server dans une sandbox isolée ; documenter toute différence TUI/app-server, sandbox Windows, approbations, identité du worker, coût et fuite potentielle de contenu. **Ne pas modifier l'exécution V3 historique.**
2. Ajouter un *shadow oracle* indépendant non présenté au worker, un décompte de retries et des traces d'acceptation strictement anonymisées. Présenter un plan seul par défaut ; ne jamais lancer de modèle sans autorisation spécifique de l'opérateur.
3. Pour chaque cas, appairer des bras ayant le même prompt, effort, CLI, configuration, rôles et état initial ; alterner ordre et conserver un nombre de répétitions défini avant tout essai. Les compteurs TUI ne sont ni quota ni facturation.
4. Stop au premier échec, ne jamais recycler les workspaces, préserver le contenu V2/V3, les logs et restaurations auditées existantes.

Suivi : [issue #61](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/61) et [PR #14](https://github.com/Proginji2000/codex-context-efficiency-stack/pull/14) (ouverte, non fusionnée).
