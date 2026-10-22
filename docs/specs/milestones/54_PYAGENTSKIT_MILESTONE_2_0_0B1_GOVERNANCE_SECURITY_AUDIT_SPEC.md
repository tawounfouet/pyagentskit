# PyAgentsKit 2.0.0b1 — Governance, Security & Audit

**Document :** `54_PYAGENTSKIT_MILESTONE_2_0_0B1_GOVERNANCE_SECURITY_AUDIT_SPEC.md`  
**Version du document :** 1.0  
**Date :** 22 octobre 2026  
**Release cible :** `2.0.0b1`  
**Statut :** **PLANNED**  
**Projet :** PyAgentsKit V2

> **Rendre explicites l’identité, l’autorisation, les approvals, l’isolation tenant et la preuve d’audit autour de toutes les actions sensibles.**

---

# 1. Rôle du milestone

Rendre explicites l’identité, l’autorisation, les approvals, l’isolation tenant et la preuve d’audit autour de toutes les actions sensibles.

Ce jalon n’est pas un simple regroupement de features. Il constitue une **preuve progressive** que l’architecture V2 peut être transformée en logiciel exécutable sans perdre ses garanties.

## Pourquoi ce milestone existe

- Un agent peut être techniquement capable d’agir sans être autorisé à le faire.
- Les Approvals doivent autoriser une action exacte et ne jamais être confondues avec AuthN/AuthZ.
- Les décisions critiques doivent être explicables et auditées.

---

# 2. Position dans la roadmap

```text
1.6.x
  │
  ▼
2.0.0a1 — Domain Foundations
  │
  ▼
2.0.0a2 — Runtime Abstraction
  │
  ▼
2.0.0a3 — Effects & Recovery Core
  │
  ▼
2.0.0a4 — Persistence V2
  │
  ▼
2.0.0b1 — Governance, Security & Audit
  │
  ▼
2.0.0b2 — External Runtimes & Connectors
  │
  ▼
2.0.0rc1 — Public Contracts, Migration & Qualification
  │
  ▼
2.0.0 — Production Qualified
```

**Jalon courant de cette spécification : `2.0.0b1`.**

---

# 3. Objectif produit

À la fin de `2.0.0b1`, PyAgentsKit doit disposer de suffisamment de matière exécutable pour que le jalon suivant puisse se construire **sans revenir sur les invariants fondamentaux** définis ici.

La priorité reste :

```text
safety
→ correctness
→ recoverability
→ interoperability
→ performance
→ convenience
```

---

# 4. Scope fonctionnel et technique

- Principal et SecurityContext.
- IdentityProviderPort.
- AuthorizationPort.
- PolicyEvaluator.
- Approval V2 complet et scope/fingerprint.
- Tenant isolation.
- AuditStore et domain AuditEvent.
- SecretReference / SecretProvider integration.
- Fail-closed high-assurance profile.

---

# 5. Invariants obligatoires

Les invariants suivants doivent être considérés comme des contraintes de conception, pas comme de simples recommandations :

- Authentication != Authorization != Approval.
- Approval is bound to an exact scope.
- Free text is never an Approval.
- Runtime output is not authority.
- Lease ownership does not imply authorization.
- Secrets are never persisted resolved.
- Cross-tenant reads/writes are forbidden.

Ils doivent être protégés par :

```text
domain rules
+
application orchestration
+
persistence constraints when relevant
+
contract tests
+
failure tests when relevant
```

---

# 6. Livrables attendus

- Security primitives V2.
- Authorization application gates.
- Approval fingerprint validation.
- Tenant-aware repository policies.
- Audit append path.
- Security and tenant isolation test suites.
- Administrative audit events.

---

# 7. Work Breakdown Structure

## 7.1 Architecture

- [ ] Vérifier que les composants du milestone respectent la topologie DDD/hexagonale.
- [ ] Vérifier les dépendances autorisées entre Domain, Application, Adapters, API et Bootstrap.
- [ ] Introduire un ADR uniquement si une décision structurante n’est pas déjà couverte.
- [ ] Éviter tout couplage à un provider spécifique dans le Domain.

## 7.2 Domaine / contrats

- [ ] Implémenter les objets et contracts explicitement inclus dans le scope.
- [ ] Rendre les transitions critiques explicites.
- [ ] Stabiliser les Value Objects nécessaires au milestone.
- [ ] Préserver les distinctions sémantiques V2.

## 7.3 Application

- [ ] Créer les use cases nécessaires.
- [ ] Orchestrer les Ports sans importer d’adapter concret.
- [ ] Définir clairement les boundaries transactionnelles.
- [ ] Rendre WAITING / MANUAL_INTERVENTION possibles lorsqu’ils constituent la réponse sûre.

## 7.4 Adapters

- [ ] Implémenter uniquement les adapters requis par ce milestone.
- [ ] Normaliser leurs erreurs vers les erreurs PyAgentsKit.
- [ ] Ne pas exposer les types SDK/providers au Domain.
- [ ] Ajouter les Contract Tests associés.

## 7.5 Tests

- [ ] Tests unitaires.
- [ ] Tests de transitions invalides.
- [ ] Tests de contracts.
- [ ] Tests de failure si applicables.
- [ ] Tests d’architecture.
- [ ] Tests de packaging.

## 7.6 Documentation

- [ ] Mettre à jour le `../../ROADMAP.md`.
- [ ] Mettre à jour le changelog.
- [ ] Documenter les APIs nouvelles ou modifiées.
- [ ] Documenter les limitations connues.
- [ ] Ajouter au moins un exemple minimal représentatif.

---

# 8. Plan de tests

Les scénarios minimum pour `2.0.0b1` sont :

- Cross-tenant Run access rejected.
- Approval for SHA A cannot authorize SHA B.
- Expired Approval cannot be consumed.
- Principal authorized before Effect execution.
- Lease owner without AuthZ cannot execute protected Effect.
- Secrets absent from durable payloads/logs/events.
- High-assurance profile fails closed.

## Niveaux de test

Selon le milestone, appliquer autant que nécessaire :

```text
TL0 Static
TL1 Unit
TL2 State / Property
TL3 Contract
TL4 Integration
TL5 Concurrency
TL6 Failure Injection
TL7 Distributed
TL8 Performance / Soak
TL9 Production Qualification
```

---

# 9. Critères de sortie

Le milestone ne peut être considéré terminé que si :

- AuthN/AuthZ/Approval are structurally separate.
- Tenant isolation tests pass.
- Approval drift is rejected.
- Critical operations are auditable.
- Security P0 tests are green.

---

# 10. Definition of Done

- [ ] Le scope obligatoire du milestone est implémenté.
- [ ] Les invariants P0 associés possèdent des tests exécutables.
- [ ] Les tests CI du niveau requis sont verts.
- [ ] Les dépendances de packages respectent les règles d’architecture.
- [ ] Les erreurs provider/infrastructure sont normalisées.
- [ ] Les nouvelles surfaces publiques sont documentées.
- [ ] Le package se construit de manière reproductible.
- [ ] Un environnement propre peut installer/importer la release.
- [ ] Le changelog contient les changements du milestone.
- [ ] Les limites et non-goals sont explicitement documentés.

---

# 11. Non-goals

Ce milestone ne doit pas dériver vers :

- Building a generic IAM product.
- Replacing enterprise IdPs.
- Building a secrets manager.

Le principe est de ne pas anticiper artificiellement le milestone suivant.

---

# 12. Compatibilité V1

La migration V1 → V2 suit un **Strangler Pattern**.

Règles :

```text
V1.6.x remains a maintenance baseline.
V2 Domain never imports compat.v1.
compat.v1 may depend on V2.
V1 behavior is preserved through tests and facades where required.
```

Toute rupture sémantique volontaire doit être :

1. explicite ;
2. testée ;
3. documentée ;
4. couverte par la migration.

---

# 13. Packaging et release

La release `2.0.0b1` doit produire au minimum :

```text
wheel
sdist
SHA-256 checksums
release notes
test evidence
```

Checklist :

- [ ] version `pyproject.toml` mise à jour ;
- [ ] build wheel ;
- [ ] build sdist ;
- [ ] installation en environnement vierge ;
- [ ] smoke import ;
- [ ] tests verts ;
- [ ] checksums ;
- [ ] tag Git correspondant ;
- [ ] release notes.

---

# 14. CI attendue

Pipeline minimum :

```text
lint
→ typecheck
→ architecture checks
→ unit/property
→ contract/integration where required
→ package build
→ fresh-install smoke test
```

Les milestones plus avancés ajoutent :

```text
concurrency
failure injection
distributed
migration
security
performance
qualification
```

---

# 15. Règles de développement

## 15.1 Pas de magic fallback

Une garantie requise ne doit jamais être silently downgraded.

## 15.2 Pas de provider leakage

Un SDK externe reste derrière son Adapter.

## 15.3 Pas de remote I/O dans une transaction longue

Les external Effects sont en dehors des transactions DB longues.

## 15.4 Pas d’exactly-once universel

PyAgentsKit privilégie :

```text
idempotency
deduplication
fencing
reconciliation
```

## 15.5 Pas de réécriture V1

Réutiliser ce qui est solide ; extraire les responsabilités qui changent.

---

# 16. Observabilité minimale

Tout nouveau chemin critique doit pouvoir produire :

```text
structured logs
metrics
trace correlation
audit evidence when relevant
```

Les identifiants à corréler incluent selon le contexte :

```text
run_id
effect_id
approval_id
runtime_invocation_id
lease_id
reconciliation_case_id
```

---

# 17. Sécurité

Le milestone doit préserver :

```text
tenant isolation
no resolved secrets in durable state
explicit authority
fail-closed behavior where required
```

Un adapter ou runtime tiers n’acquiert jamais automatiquement :

```text
authorization
approval authority
ownership
```

par le seul fait d’être connecté.

---

# 18. Performance

Le milestone doit éviter toute optimisation prématurée qui détruit la clarté des semantics.

Ordre de priorité :

```text
Safety
Correctness
Recoverability
Predictability
Throughput
Latency
```

Les benchmarks pertinents sont ajoutés quand le milestone possède des chemins suffisamment stables.

---

# 19. Risques principaux

Risques communs à surveiller :

- fuite des semantics V1 dans le Domain V2 ;
- abstraction trop générique avant preuve par usage ;
- coupling runtime/provider ;
- retries utilisés à la place de reconciliation ;
- réduction d’un état ambigu vers FAILED ;
- transaction DB étendue autour d’I/O externe ;
- ajout de fonctionnalités du milestone suivant avant stabilisation du courant ;
- documentation non synchronisée avec le comportement réel.

---

# 20. Gate de revue d’architecture

Avant clôture :

```text
[ ] Le milestone conserve les bounded contexts.
[ ] Le Domain ne dépend d’aucune infrastructure.
[ ] Les Ports sont au bon niveau.
[ ] Les Adapters restent remplaçables.
[ ] Les invariants critiques sont testés.
[ ] Aucun raccourci provider-specific n’a contaminé le Core.
[ ] Le modèle de failure est explicite.
[ ] Les non-goals sont respectés.
```

---

# 21. Gate de release

Avant tag :

```text
[ ] CI green
[ ] tests requis green
[ ] package build green
[ ] fresh install green
[ ] changelog à jour
[ ] docs à jour
[ ] aucun P0 defect ouvert
[ ] migration/compat vérifiée si applicable
[ ] checksums générés
```

---

# 22. Dépendances vers le milestone suivant

La sortie de `2.0.0b1` doit devenir une **foundation**, pas une dette que le milestone suivant doit contourner.

Aucun jalon ne doit être déclaré terminé si le jalon suivant nécessite :

```text
breaking the core invariants
rewriting the new abstractions immediately
bypassing the public/internal contracts
```

---

# 23. Definition of Success

`2.0.0b1 — Governance, Security & Audit` est réussi lorsque :

> **Rendre explicites l’identité, l’autorisation, les approvals, l’isolation tenant et la preuve d’audit autour de toutes les actions sensibles.**

et que cette promesse est soutenue par :

```text
code
+
tests
+
contracts
+
failure evidence when relevant
+
documentation matching reality
```

---

# 24. Résumé exécutable

```text
SPECIFICATION
    │
    ▼
IMPLEMENTATION
    │
    ▼
INVARIANT TESTS
    │
    ▼
CONTRACT / FAILURE TESTS
    │
    ▼
PACKAGE
    │
    ▼
RELEASE GATE
    │
    ▼
2.0.0b1
    │
    ▼
NEXT MILESTONE
```

---

## Références structurantes

Ce milestone s’inscrit dans le corpus V2 existant, notamment :

- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`
- `../../planning/49_PYAGENTSKIT_V2_IMPLEMENTATION_NEXT_STEPS.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`


---

# 25. Principe final

> **Un milestone PyAgentsKit n’est terminé ni lorsqu’une liste de features est cochée, ni lorsqu’une démo fonctionne une fois ; il est terminé lorsque les garanties qu’il introduit sont devenues des contrats exécutables, testés et suffisamment stables pour servir de fondation au jalon suivant.**
