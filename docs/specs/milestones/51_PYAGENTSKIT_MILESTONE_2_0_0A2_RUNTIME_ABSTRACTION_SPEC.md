# PyAgentsKit 2.0.0a2 — Runtime Abstraction

**Document :** `51_PYAGENTSKIT_MILESTONE_2_0_0A2_RUNTIME_ABSTRACTION_SPEC.md`  
**Version du document :** 1.0  
**Date :** 22 octobre 2026  
**Release cible :** `2.0.0a2`  
**Statut :** **IMPLEMENTED**
**Projet :** PyAgentsKit V2

> **Rendre les runtimes agentiques interchangeables via un contrat explicite, négocié par capabilities et indépendant des marques/frameworks.**

---

# 1. Rôle du milestone

Rendre les runtimes agentiques interchangeables via un contrat explicite, négocié par capabilities et indépendant des marques/frameworks.

Ce jalon n’est pas un simple regroupement de features. Il constitue une **preuve progressive** que l’architecture V2 peut être transformée en logiciel exécutable sans perdre ses garanties.

## Pourquoi ce milestone existe

- Le Core V2 ne doit plus être confondu avec le Runner historique.
- Les runtimes externes doivent pouvoir être intégrés sans branches spécifiques dans l’Application Layer.
- La fiabilité doit dépendre des garanties démontrées par un runtime, pas de son nom.

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

**Jalon courant de cette spécification : `2.0.0a2`.**

---

# 3. Objectif produit

À la fin de `2.0.0a2`, PyAgentsKit doit disposer de suffisamment de matière exécutable pour que le jalon suivant puisse se construire **sans revenir sur les invariants fondamentaux** définis ici.

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

- AgentRuntimeAdapter contract.
- RuntimeDescriptor, RuntimeHandle, RuntimeCapability.
- RuntimeRequirements et CapabilityNegotiator.
- RuntimeRegistry et InMemoryRuntimeRegistry.
- SideEffectControlLevel : FULL, BOUNDED, OPAQUE.
- Runtime qualification levels L0 → L4.
- RuntimeBinding durable et distinction avec RuntimeInvocation.
- NativeRuntimeAdapter au-dessus du Runner V1 reclassifié en NativeRuntimeEngine.

---

# 5. Invariants obligatoires

Les invariants suivants doivent être considérés comme des contraintes de conception, pas comme de simples recommandations :

- Native runtime is not privileged.
- Runtime selection is capability-driven.
- Required capabilities are never silently downgraded.
- RuntimeBinding != RuntimeInvocation.
- A Run does not silently switch runtime family.
- Capability declarations must be contract-tested.
- Side-effect control level is explicit.
- Provider-specific SDK types do not enter Domain.

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

- AgentRuntimeAdapter Protocol stabilisé en alpha.
- RuntimeDescriptor et RuntimeCapability.
- RuntimeRegistry + capability negotiation déterministe.
- NativeRuntimeAdapter.
- Runtime contract test suite.
- Runtime compatibility/version metadata.
- Documentation des capabilities réelles du runtime natif.

---

# 7. Work Breakdown Structure

## 7.1 Architecture

- [x] Vérifier que les composants du milestone respectent la topologie DDD/hexagonale.
- [x] Vérifier les dépendances autorisées entre Domain, Application, Adapters, API et Bootstrap.
- [x] Introduire un ADR uniquement si une décision structurante n’est pas déjà couverte.
- [x] Éviter tout couplage à un provider spécifique dans le Domain.

## 7.2 Domaine / contrats

- [x] Implémenter les objets et contracts explicitement inclus dans le scope.
- [x] Rendre les transitions critiques explicites.
- [x] Stabiliser les Value Objects nécessaires au milestone.
- [x] Préserver les distinctions sémantiques V2.

## 7.3 Application

- [x] Créer les ports et services de registry/négociation nécessaires.
- [x] Orchestrer les Ports sans importer d’adapter concret.
- [x] Définir clairement les boundaries transactionnelles.
- [x] Préserver les réponses WAITING et les erreurs fail-closed pour les garanties absentes.

## 7.4 Adapters

- [x] Implémenter uniquement les adapters requis par ce milestone.
- [x] Normaliser leurs erreurs vers les erreurs PyAgentsKit.
- [x] Ne pas exposer les types SDK/providers au Domain.
- [x] Ajouter les Contract Tests associés.

## 7.5 Tests

- [x] Tests unitaires.
- [x] Tests de transitions invalides.
- [x] Tests de contracts.
- [x] Tests de failure si applicables.
- [x] Tests d’architecture.
- [x] Tests de packaging.

## 7.6 Documentation

- [x] Mettre à jour le `../../ROADMAP.md`.
- [x] Mettre à jour le changelog.
- [x] Documenter les APIs nouvelles ou modifiées.
- [x] Documenter les limitations connues.
- [x] Ajouter au moins un exemple minimal représentatif.

---

# 8. Plan de tests

Les scénarios minimum pour `2.0.0a2` sont :

- START / RESUME / CANCEL / STATUS contract tests.
- Capability mismatch fail-fast.
- FULL requis / BOUNDED offert → rejet.
- Runtime exact demandé mais indisponible → erreur sans fallback.
- Même requirements + même registry → même sélection.
- Native adapter passe exactement le même contrat qu’un adapter externe.
- Upgrade incompatible → la négociation refuse le candidat avant resume.

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

- NativeRuntimeAdapter passe la contract suite.
- CapabilityNegotiator est déterministe et explicable.
- Aucun if/elif par nom de runtime dans Application.
- RuntimeBinding est snapshoté et exploitable par recovery.
- Le Runner V1 reste utilisable via compatibilité.

---

# 10. Definition of Done

- [x] Le scope obligatoire du milestone est implémenté.
- [x] Les invariants P0 associés possèdent des tests exécutables.
- [x] Les tests CI du niveau requis sont verts.
- [x] Les dépendances de packages respectent les règles d’architecture.
- [x] Les erreurs provider/infrastructure sont normalisées.
- [x] Les nouvelles surfaces publiques sont documentées.
- [x] Le package se construit de manière reproductible.
- [x] Un environnement propre peut installer/importer la release.
- [x] Le changelog contient les changements du milestone.
- [x] Les limites et non-goals sont explicitement documentés.

---

# 11. Non-goals

Ce milestone ne doit pas dériver vers :

- Support de nombreux runtimes externes.
- Recovery V2 complet.
- Persistence PostgreSQL V2.
- Dynamic plugin marketplace.

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

La release `2.0.0a2` doit produire au minimum :

```text
wheel
sdist
SHA-256 checksums
release notes
test evidence
```

Checklist :

- [x] version `pyproject.toml` mise à jour ;
- [x] build wheel ;
- [x] build sdist ;
- [x] installation en environnement vierge ;
- [x] smoke import ;
- [x] tests verts ;
- [x] checksums ;
- [ ] tag Git correspondant ;
- [x] release notes.

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
[x] Le milestone conserve les bounded contexts.
[x] Le Domain ne dépend d’aucune infrastructure.
[x] Les Ports sont au bon niveau.
[x] Les Adapters restent remplaçables.
[x] Les invariants critiques sont testés.
[x] Aucun raccourci provider-specific n’a contaminé le Core.
[x] Le modèle de failure est explicite.
[x] Les non-goals sont respectés.
```

---

# 21. Gate de release

Avant tag :

```text
[x] CI green
[x] tests requis green
[x] package build green
[x] fresh install green
[x] changelog à jour
[x] docs à jour
[x] aucun P0 defect ouvert
[x] migration/compat vérifiée si applicable
[x] checksums générés
```

---

# 22. Dépendances vers le milestone suivant

La sortie de `2.0.0a2` doit devenir une **foundation**, pas une dette que le milestone suivant doit contourner.

Aucun jalon ne doit être déclaré terminé si le jalon suivant nécessite :

```text
breaking the core invariants
rewriting the new abstractions immediately
bypassing the public/internal contracts
```

---

# 23. Definition of Success

`2.0.0a2 — Runtime Abstraction` est réussi lorsque :

> **Rendre les runtimes agentiques interchangeables via un contrat explicite, négocié par capabilities et indépendant des marques/frameworks.**

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
2.0.0a2
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
