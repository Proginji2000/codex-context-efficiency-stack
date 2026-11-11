# Qualification Claude Code + Codex en VM isolée — état au 11 novembre 2026

> **Statut : EN QUALIFICATION — GO Core non atteint.** Point de situation documentaire, non une autorisation de déploiement ou d'accès étendu. Les résultats ci-dessous proviennent des sorties de terminal fournies par l'opérateur et des vérifications GitHub ; ils ne constituent pas une observation indépendante de l'hyperviseur.

## Décision active

- **Architecture de référence :** Claude Code orchestre ; Codex CLI réalise les délégations via le plugin officiel `openai/codex-plugin-cc`. Kandev ne sera étudié qu'après mesure d'une valeur ajoutée réelle.
- **Budget :** abonnements Claude Pro et ChatGPT Plus, aucune clé API dans l'environnement contrôlé, aucun achat de crédits autorisé. La consommation et l'absence de frais additionnels devront être qualifiées par des preuves de facturation lors des tests.
- **Sécurité :** CLI installés sous un compte de qualification sans sudo, répertoires d'authentification isolés, revue automatique du plugin désactivée, canaris en permissions restreintes. Aucun accès étendu ni accès implicite à l'infrastructure.
- **Tentatives :** maximum deux exécutions automatiques par opération, tous modèles confondus ; troisième uniquement sur accord humain. La protection déterministe et l'escalade intelligente sont **prévues, non qualifiées**.
- **Source des règles :** cahier de qualification Claude Code + Codex v1.1 et décisions du propriétaire des 10–11 novembre 2026. Le présent état prévaut sur les descriptions d'architecture antérieures pour ce cycle, sans modifier rétroactivement les rapports historiques.

## État par lot

| Lot / test | Statut au 11/11/2026 | Éléments de preuve et limites |
| --- | --- | --- |
| L6 — Infrastructure Homelab | **PASS fonctionnel (rapporté par Homelab)** | VM Linux isolée, SSH/QGA, DNS/HTTPS, CPU virtuel corrigé pour SSE4.2/AVX2, snapshot de référence. Persistance après reboot physique de l'hôte encore non qualifiée. Aucun détail réseau ou d'accès privé reproduit ici. |
| L0 / A-00 — Audit | **PARTIAL** | Contrôle local `A00_LOCAL_CHECKS=PASS` ; répertoires isolés à permissions 700, absence de variables API contrôlées, état Git et versions vérifiés. L'inventaire exhaustif et les preuves pré-installation exigés par le cahier ne sont pas tous attestés. |
| L1 / A-01–A-04 | **PASS sur les contrôles rapportés** | Claude Code connecté par `claude.ai`, Codex CLI connecté par ChatGPT ; plugin chargé, `/codex:setup` prêt, review gate désactivé. |
| L2 / A-05 | **BLOCKED — quota Codex** | Revue `/codex:review --base main --wait` démarrée, mais refusée avant analyse à cause de la limite d'usage ; aucune détection du défaut démontrée. Branche et commit de test inchangés après l'appel. |
| L2 / A-06 | **NON DÉMARRÉ** | Dépend de la disponibilité du quota Codex. |
| L3 / A-07–A-08 | **NON DÉMARRÉ** | Aucune délégation d'implémentation qualifiée. |
| L4 / A-11 | **NON DÉMARRÉ** | Fixtures M1–M3 préparées, mais aucun benchmark de modèle ou orchestrateur exécuté. |
| L5 et phases B–E | **NON DÉMARRÉS** | Respecter les conditions d'entrée et l'ordre du cahier. |

## Versions et contrôles observés

| Élément | Valeur |
| --- | --- |
| Système invité | Ubuntu 24.04 LTS |
| Node.js / npm | `24.22.2` / `11.19.1` |
| Claude Code | `2.1.311` ; session de qualification Sonnet 5.5 |
| Codex CLI | `0.167.0` |
| Plugin Claude `codex` | `1.0.6` ; 1 plugin / 11 skills chargés |
| Variables `OPENAI_API_KEY` et `ANTHROPIC_API_KEY` | Absentes dans le contrôle d'environnement |
| Permission Claude lors du test A-05 | Mode manuel |
| Dépôt Codex public, branche `main` | `0eb9f78ebbf76acb611a127b7c6de0203e0e3607` au préflight |

**Notes :** sept paquets Ubuntu sont restés non mis à jour après l'upgrade initial, dont des métapaquets du noyau. Aucun changement réseau/hyperviseur n'est demandé au projet Codex pendant cette pause. Ne pas interpréter l'absence de variables API comme un audit complet de facturation.

## Fixtures Git locales figées, sans push

| Mission | Référence locale | État déterministe |
| --- | --- | --- |
| M1 — Ajouter `normalize_sku` | `qualif-base-M1` / `cc2b4e5` | Échec attendu vérifié |
| M2 — Corriger `total` | `qualif-base-M2` / `420790c` | Échec attendu vérifié |
| M3 — Refactoriser `summarize_orders` | `qualif-base-M3` / `3c8c607` | Cinq tests réussis |
| A-05 — Défaut `total` | branche `qualif/A-05` / `2879ed2` | Diff attendu conservé ; caches Python non suivis déjà présents |

Ces commits et tags appartiennent au **dépôt local jetable**. Ils ne sont pas publiés sur GitHub ; les hashes ne constituent pas des références téléchargeables depuis ce dépôt public.

## Incident et prochain point d'entrée

Le 11 novembre 2026, le plugin a créé un fil de revue, mais le moteur Codex a retourné une erreur de **limite d'utilisation**. Le message annonçait une possibilité de reprise le **12 novembre 2026 à 17 h 30** (heure de la VM, UTC ; **18 h 30 Europe/Paris**). Un rappel utilisateur est planifié à **18 h 35 Europe/Paris**.

**À la reprise :**
1. Vérifier la disponibilité réelle du quota Codex ; ne pas acheter de crédits.
2. Vérifier branche/HEAD et état Git du canari A-05.
3. Relancer **une seule** revue A-05 en lecture seule si le quota est revenu.
4. Vérifier le rapport et l'absence de modification ; enregistrer le verdict `PASS`, `FAIL` ou `BLOCKED` avec preuves.
5. Si A-05 passe, poursuivre **A-06 puis A-07**, dans l'ordre du cahier. Ne pas sauter directement aux phases Kandev, MCP ou full access.

**Pendant la pause :** aucun nouveau test Codex, aucune réinstallation, aucune modification d'infrastructure ni tentative de contournement du quota. Le plugin documente `/codex:rescue --model … --effort …`, mais l'application effective de ces paramètres reste à vérifier en E-01.
