# H1.3d — Préqualification d'une cible réseau contrôlée, sans connexion

**Statut : implémentation de l'inventaire d'une cible candidate uniquement, sans socket, DNS, sous-processus, service, envoi réseau, modèle ou tour Codex. Aucun IP ni port opérationnel n'a été approuvé.**

## Pourquoi une cible externe à l'hôte de test ?

Le protocole de qualification H1.3d doit vérifier un refus de **sortie réseau** attribuable à MXC, pas seulement démontrer qu'un processus peut (ou ne peut pas) joindre un service `localhost`. La version épinglée Codex CLI 0.165.0 peut autoriser des connexions loopback/hôte gérées : voir [`mxc-sandbox/src/policy.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/mxc-sandbox/src/policy.rs) et [`config.schema.json`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/core/config.schema.json).

Nous privilégions pour **l'étude de faisabilité** une machine *distincte* dont l'opérateur a le contrôle (p. ex. le serveur secondaire / homelab sur le LAN). Ne pas réutiliser le loopback ni une autre IP affectée à la même machine Windows. Les VM derrière une NAT/règle de pare-feu inaccessible ne conviennent pas tant que leur joignabilité et leur rôle ne sont pas vérifiés.

## Nouvelle porte H1.3d-TARGET : sélection locale, **zéro réseau**

Fichiers : `scripts/Plan-CodexAB-H13DTarget.py` et `scripts/Test-Plan-CodexAB-H13DTarget.py`.

- Le mode par défaut `PLAN_ONLY_NO_NETWORK_OR_PROCESS` ne choisit aucune machine.
- Pour tester **purement mathématiquement** une candidature, l'opérateur doit fournir explicitement une IPv4 dans les trois espaces privés RFC1918, un port non privilégié de **20000 à 60999**, l'ensemble connu des IPv4 **locales** de son PC et une déclaration que l'inventaire est complet, plus deux confirmations que la cible est une *autre machine* et qu'il contrôle l'endpoint.
- Rejets fail-closed : adresse publique, IPv6, loopback, lien-local, documentation/réservé, IP propre du PC, valeurs malformées, doublons d'IP locales, adressage réseau/broadcast vraisemblable en /24, port privilégié, inventaire absent ou incomplet, propriété non confirmée. Les erreurs imprimées sont uniquement des codes fixes, jamais les adresses ou le port.
- La sortie `H13D_TARGET_CANDIDATE_ELIGIBLE_OFFLINE_NOT_RUNTIME` signifie **uniquement** que les éléments déclarés satisfont une présélection réseau. `remote_machine_ownership_operator_declared_only=true` rappelle que l'outil **ne peut pas vérifier l'identité ni la propriété d'un hôte sans contact réseau**.
- Les champs `remote_endpoint_reachability_verified`, `network_policy_effective_verified`, `managed_proxy_topology_verified`, `host_positive_control_observed`, `sandbox_network_attempt_observed`, `independent_os_block_observed` et `real_network_egress_verified` restent tous **false**, même si la présélection est PASS.

Exemple **de syntaxe uniquement, utilisant des IP fictives** pour la validation hors réseau :

```powershell
$repo = 'C:\Dev\codex-context-efficiency-stack'
$py = 'C:\Dev\Python31314\python.exe'
# Ces adresses sont illustratives : adapter à une cible effectivement possédée.
# Lecture de configuration locale seulement, SANS probe ni socket.
$mine = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
  Where-Object { $_.AddressState -eq 'Preferred' } |
  Select-Object -ExpandProperty IPAddress)
$args = @('-B', "$repo\scripts\Plan-CodexAB-H13DTarget.py",
  '--candidate-ip', '192.168.45.72', '--candidate-port', '42589',
  '--controlled-remote-machine', '--endpoint-owned')
foreach ($ip in $mine) { $args += @('--local-ip', $ip) }
# N'ajouter cette option que si l'inventaire obtenu est complet.
$args += '--local-inventory-complete'
& $py @args
```

Ce script d'exemple ne contacte aucune adresse. **Ne pas considérer les adresses d'exemple comme une cible autorisée.** La source réelle peut révéler des IPv4 locales dans la ligne de commande *temporairement*, mais la sortie de l'outil ne les recopie pas. Ne pas capturer les arguments dans des journaux publics.

## Ce que la présélection ne permet pas encore

Il faut ensuite qualifier un service témoin **distinct et éphémère** sur la machine distante et sa joignabilité depuis l'hôte Windows, **avec une autorisation explicite**. Un contrôle positif de connexion côté hôte et un observateur indépendant côté service sont nécessaires, mais ne suffisent pas à attribuer à eux seuls un refus à une règle OS MXC. Il faudra encore confirmer la politique `networkAccess` *effectivement résolue* du profil `:workspace`, la présence ou absence du proxy géré, et une preuve de blocage attribuable à l'OS/proxy. Un timeout, une panne DNS, un serveur absent ou un refus TCP applicatif restent **INCONCLUSIVE**, et les nouvelles commandes ne doivent pas convertir ces erreurs en PASS.

La configuration de profil doit être vérifiée à partir du code épinglé [`core/src/config/permissions.rs`](https://github.com/openai/codex/blob/rust-v0.165.0/codex-rs/core/src/config/permissions.rs). Pour `:workspace`, un paramètre `sandbox_workspace_write.network_access` peut modifier la politique réseau ; il serait erroné de déduire l'interdiction réseau d'un argument `:workspace` seul.

**Prochaine autorisation à demander à l'opérateur :** choisir/valider une machine distincte contrôlée, son adresse privée effective et le droit d'y déployer temporairement un témoin non privilégié. D'ici là **aucune connexion réelle, aucun port ouvert et aucune configuration de pare-feu modifiée**.

PR #14 OPEN/non fusionnée, 12 essais A/B toujours non autorisés ; H1.2 déclaré, H1.3a fichiers et H1.3c processus contrôlés ont leurs preuves propres, sans droit implicite de tester des ressources réseau.
