# A11/P21 — Qualification du sandbox Claude et Bubblewrap (checkpoint du 13 novembre 2026)

**Source :** résultats d'un opérateur dans une VM de qualification Ubuntu 24.04.5, transmis à la documentation. Aucun test natif réexécuté par cette mise à jour documentaire.  
**Statut :** **PARTIAL** : S5J A/B PASS ; Claude Bash en confinement systemd **BLOCKED** ; A11-M3 suspendue.

## Contexte non sensible

- Claude Code `2.1.311`, Codex CLI `0.167.0`, Bubblewrap `0.9.0`, systemd `255`.
- Missions A11-M1 et M2 fonctionnelles, mais **débordement d'écriture M2 confirmé** : sécurité M2 FAIL ; preuve conservée hors worktrees. A11-M3 ne doit pas démarrer.
- Le sandbox Bash natif Claude avait d'abord échoué dans `apply-seccomp` sur `/proc/self/setgroups`. Le contournement `allowAllUnixSockets=true` n'a été essayé **que sous une frontière systemd indépendante** et n'est pas une approbation de production.
- Limites système du canari : utilisateur non-root ; `NoNewPrivileges=yes`, bounding/ambient capabilities vides, filesystem principalement RO et seul scratch jetable writable, répertoires temporaires RO, masquage ciblé des sockets privilégiés. Le plugin Codex n'a pas encore été qualifié dans cette enveloppe.

## Résultats déterminants

| Jalons | Preuve | Qualification |
|---|---|---|
| S3 | systemd canari non privilégié ; écriture autorisée et refus de fixtures externes | PASS limité à ce test |
| S4 | démarrage CLI Claude et Codex ; métadonnées plugin disponibles | PASS démarrage, pas d'appel modèle |
| S5–S5F | échecs progressifs : observabilité, AF_UNIX absent, contrôle erroné des sockets, tentative de masque /run/systemd trop large | NON QUALIFIÉS ; ne pas rejouer |
| S5G | chemin systemd/D-Bus remplacés par le socket factice inaccessible, identité inode/dev contrôlée ; privilèges contrôlés | PASS **sur les deux chemins**, pas IPC abstraits |
| S5H | Bash tool_use présent ; tool_result en erreur ; sonde jamais atteinte | BLOCKED |
| S5I | `bwrap: can't mount proc on <PATH> operation not permitted` dans **tool_result**. Les marqueurs d'écriture absents ne valent pas preuve de refus. | BLOCKED |
| **S5J** | A/B bwrap minimal : `ProtectKernelTunables=yes` → code 1 / `BWRAP_PROC_MOUNT_DENIED=True` ; `ProtectKernelTunables=no` → code 0 / `BWRAP_STARTED`. Aucun appel Claude/Codex, aucune modification système persistante, fichiers témoins inchangés. | **PASS A/B uniquement** |

Commande reproductrice S5J (par unité temporaire non-root, autres propriétés constantes) : `bwrap --ro-bind / / --dev /dev --unshare-pid --unshare-user --cap-drop ALL --proc /proc -- /usr/bin/true`. Une seule différence A/B : `ProtectKernelTunables=yes` versus `no`.

**Interprétation :** la propriété systemd `ProtectKernelTunables` provoque le conflit procfs dans cet essai. Le succès du cas `no` n'est **ni** une validation de Claude Code **ni** une validation du niveau de sécurité d'un profil permanent. [Incident amont comparable](https://github.com/anthropics/sandbox-runtime/issues/743) ; [documentation systemd.exec](https://www.freedesktop.org/software/systemd/man/255/systemd.exec.html).

## Garde-fous et suite

1. Conserver AppArmor, les restrictions noyau, l'absence de `CAP_SYS_ADMIN`, `NoNewPrivileges`, le principe d'une frontière systemd indépendante, le filtrage réseau et les protections des secrets.
2. Analyser la compatibilité entre les montages `/proc` de systemd et Bubblewrap ; préparer **une seule proposition de profil de test éphémère** avec barrières et risques documentés. Ne pas faire de `ProtectKernelTunables=no` une valeur de production par simple raccourci.
3. Sur candidate qualifiée, mesurer un unique canari **Claude appelle Bash** : `tool_result` sans erreur, marqueur positif de write autorisé, témoin explicite de refus EROFS/EACCES sur un chemin possédé par le même UID mais hors `ReadWritePaths`, vérification extérieure des empreintes. Protéger les logs (extraits expurgés, aucun token).
4. Ensuite seulement, tester outils Claude natifs Read/Edit/Write, délégation plugin vers Codex, MCP, protections des secrets et IPC (notamment sockets UNIX abstraits). Tant que cela manque, M3 reste BLOCKED.
5. Ne pas relancer S5J ni d'anciens canaris, ne pas déclarer un succès du Bash sur la seule base d'un exit 0 du CLI et ne pas utiliser danger-full-access.

**Suivi :** [issue #136](https://github.com/Proginji2000/codex-context-efficiency-stack/issues/136). Les chemins, IP, journaux complets et empreintes de preuve privés sont dans le dépôt Homelab **privé**.
