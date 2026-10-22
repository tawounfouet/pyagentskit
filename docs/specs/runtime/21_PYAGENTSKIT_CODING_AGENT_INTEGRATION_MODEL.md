# PyAgentsKit — Coding Agent Integration Model

**Document :** `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — Coding Agent Integration  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`

---

# 1. Objet

Ce document définit le modèle d’intégration des **coding agents** dans PyAgentsKit.

Il couvre notamment :

- Codex ;
- Claude Code ;
- OpenCode ;
- Antigravity CLI (`agy`) ;
- futurs agents de code programmables ;
- runtimes internes de génération/modification de code.

Le principe directeur est :

> **PyAgentsKit ne devient pas un coding agent ; il encadre les actions d’un coding agent avec les mêmes garanties de durabilité, contrôle, sécurité, audit et reprise que pour tout autre runtime.**

---

# 2. Positionnement

Un coding agent est traité comme un runtime spécialisé :

```text
Coding Agent Runtime
        │
        ▼
AgentRuntimeAdapter
        │
        ▼
PyAgentsKit Core
        │
        ├── Run
        ├── Effect
        ├── Approval
        ├── Lease
        ├── Artifact
        └── Audit
```

---

# 3. Runtimes cibles

Exemples :

```text
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
Custom Coding Runtime
```

---

# 4. Non-objectifs

PyAgentsKit ne doit pas devenir :

```text
IDE
Git client généraliste
patch engine
diff viewer
code review UI
package manager
CI/CD platform
deployment orchestrator
source code search engine
```

Il fournit les garde-fous autour de ces systèmes.

---

# 5. Principes architecturaux

```text
CA-PR-01 Coding agents use AgentRuntimeAdapter.
CA-PR-02 Coding-specific concepts stay outside the core.
CA-PR-03 Workspace mutation is not automatically a Protected Effect.
CA-PR-04 Persistent remote mutation usually is.
CA-PR-05 Git-native concurrency controls complement PyAgentsKit leases.
CA-PR-06 Shell execution is policy-controlled.
CA-PR-07 Production effects require stronger controls.
CA-PR-08 Repository state must be inspectable and auditable.
CA-PR-09 Credentials are brokered, not broadly exposed.
CA-PR-10 Recovery must avoid repeating persistent external actions.
```

---

# 6. Concepts spécifiques

Objets/Value Objects candidats :

```text
CodingWorkspace
RepositoryResource
RepositoryReference
BranchReference
CommitReference
PullRequestReference
CodeChange
DiffReference
PatchReference
CommandInvocation
TestExecution
BuildArtifactReference
DeploymentReference
```

Ils appartiennent à un module spécialisé et non au core généraliste.

---

# 7. CodingWorkspace

Un `CodingWorkspace` représente l’environnement de travail local d’un coding agent.

Attributs conceptuels :

```text
workspace_id
run_id
path_reference
repository_reference?
branch_reference?
isolation_level
status
created_at
expires_at?
metadata
```

---

# 8. États du Workspace

Valeurs candidates :

```text
CREATING
READY
DIRTY
LOCKED
ARCHIVED
DELETED
FAILED
```

---

# 9. Workspace lifecycle

```text
create
↓
clone / prepare
↓
READY
↓
agent edits
↓
DIRTY
↓
tests / commit / artifact
↓
archive or delete
```

---

# 10. Workspace isolation

Le workspace doit être isolé du système hôte autant que nécessaire.

Options :

```text
temporary directory
git worktree
container
microVM
remote sandbox
```

---

# 11. Ephemeral workspaces

Par défaut, un workspace de coding agent devrait tendre vers :

```text
ephemeral
reconstructible
isolated
```

---

# 12. RepositoryReference

Structure conceptuelle :

```text
provider
owner
repository
remote_url_reference?
```

Exemples :

```text
github / openai / project
gitlab / org / repo
local / path / project
```

---

# 13. BranchReference

Structure :

```text
repository_reference
branch_name
expected_remote_sha?
```

---

# 14. CommitReference

Structure :

```text
repository_reference
commit_sha
```

---

# 15. PullRequestReference

Structure :

```text
provider
repository_reference
number
head_branch
base_branch
```

---

# 16. RepositoryResource

Une ressource logique peut être :

```text
repository
branch
worktree
tag
release
```

et peut être protégée par lease si une vraie exclusivité est nécessaire.

---

# 17. ResourceIdentity coding

Exemple :

```text
resource_type = repository_branch
resource_id = github:org/repo:feature/x
```

---

# 18. Run lease vs repository lease

Le `Run` protège :

```text
logical execution ownership
```

Un `repository_branch` lease protège :

```text
concurrent branch mutation
```

Les deux peuvent coexister.

---

# 19. Quand utiliser un repository lease

Utile si :

```text
multiple workers share same mutable workspace
multiple agents may edit same branch
shared deployment branch
```

Pas nécessaire pour :

```text
isolated worktree per Run
```

---

# 20. Git-native concurrency

PyAgentsKit doit exploiter les mécanismes Git existants :

```text
expected SHA
fast-forward checks
--force-with-lease
protected branches
PR merge checks
```

---

# 21. Lease != Git concurrency replacement

Le lease PyAgentsKit complète :

```text
Git remote state validation
```

Il ne la remplace pas.

---

# 22. AgentRuntimeAdapter

Les coding agents passent par le même contrat :

```text
start
resume
cancel
status
events
checkpoint
```

---

# 23. Coding capabilities

Capabilities candidates :

```text
WORKSPACE
FILE_READING
FILE_EDITING
COMMAND_EXECUTION
TEST_EXECUTION
GIT_STATUS
GIT_DIFF
GIT_COMMIT
GIT_PUSH
PR_CREATION
PR_MERGE
PACKAGE_PUBLISH
DEPLOYMENT
```

---

# 24. Capability declaration

Un adapter doit déclarer ce qu’il sait réellement contrôler.

Exemple :

```text
FILE_EDITING = yes
TOOL_INTERCEPTION = partial
GIT_PUSH_CONTROL = full
```

---

# 25. CodingAgentAdapter

Une spécialisation peut exister :

```python
class CodingAgentAdapter(AgentRuntimeAdapter, Protocol):
    ...
```

mais seulement si les différences contractuelles deviennent réelles.

---

# 26. Préférence initiale

Préférer :

```text
AgentRuntimeAdapter
+
RuntimeCapabilities
+
coding metadata
```

avant de créer une nouvelle hiérarchie.

---

# 27. RuntimeHandle

Exemples :

```text
Codex thread
Claude Code session
OpenCode session
CLI process/session id
```

Le handle reste opaque au core.

---

# 28. Runtime events coding

Événements candidats :

```text
FILE_READ
FILE_WRITTEN
FILE_DELETED
COMMAND_STARTED
COMMAND_COMPLETED
TEST_STARTED
TEST_COMPLETED
GIT_STATUS
GIT_DIFF_AVAILABLE
GIT_COMMIT_CREATED
GIT_PUSH_REQUESTED
PR_CREATION_REQUESTED
DEPLOYMENT_REQUESTED
```

---

# 29. NormalizedRuntimeEvent

Les événements coding spécifiques peuvent être conservés comme :

```text
payload spécialisé
```

sans devenir des entités core.

---

# 30. File reads

Lire un fichier local est généralement :

```text
READ
```

et pas un `Effect`.

---

# 31. File edits

Modifier un fichier dans un workspace éphémère local est généralement :

```text
workspace-local mutation
```

et pas nécessairement un Protected Effect.

---

# 32. Pourquoi file edit != external Effect

Un fichier local dans un workspace isolé peut être :

```text
discarded
recreated
reviewed
```

sans conséquence externe durable.

---

# 33. Exceptions

Un file edit peut devenir sensible si le workspace est :

```text
shared
mounted into production
directly consumed by another system
```

La classification dépend du contexte.

---

# 34. Shell command

Une `CommandInvocation` représente :

```text
executable
arguments
cwd
environment references
timeout
exit code
stdout reference
stderr reference
```

---

# 35. Command classification

Catégories :

```text
READ_ONLY
LOCAL_MUTATION
NETWORKED
REMOTE_MUTATION
CRITICAL
```

---

# 36. Exemples

```text
git status
→ READ_ONLY

pytest
→ LOCAL_MUTATION / COMPUTE

pip install
→ NETWORKED

git push
→ REMOTE_MUTATION

terraform apply
→ CRITICAL
```

---

# 37. Shell policy

La policy peut considérer :

```text
executable
arguments
cwd
network target
environment
principal
risk
```

---

# 38. shell=True

À éviter lorsque possible.

Préférer :

```text
argv execution
```

pour limiter command injection.

---

# 39. Working directory

Toute commande doit être exécutée sous un workspace explicitement autorisé.

---

# 40. Environment variables

Éviter d’injecter globalement des secrets dans l’environnement du runtime.

Préférer :

```text
scoped command/tool execution
```

---

# 41. File boundary

Avant accès fichier :

```text
normalize
resolve symlink
verify allowed root
```

---

# 42. Diff

Un `DiffReference` peut pointer vers :

```text
git diff
patch artifact
structured change set
```

---

# 43. CodeChange

Concept candidat :

```text
change_id
workspace_id
base_commit
head_commit?
diff_reference
files_changed
created_at
```

---

# 44. Patch

Un patch peut être stocké comme :

```text
Artifact
```

plutôt qu’objet métier complet.

---

# 45. Tests

Une `TestExecution` peut enregistrer :

```text
command
framework
duration
exit_code
summary
artifact references
```

---

# 46. Test output

Les sorties volumineuses doivent être stockées comme :

```text
Artifact
```

et non injectées intégralement dans logs.

---

# 47. Build

Un build peut produire :

```text
Artifact
```

avec :

```text
checksum
content type
source commit
build metadata
```

---

# 48. Artifact provenance

Pour publish/deploy :

```text
repository
commit SHA
build artifact checksum
```

doivent pouvoir être liés.

---

# 49. Git commit

Créer un commit local peut être classé :

```text
LOCAL_PERSISTENT
```

Il devient durable dans le repository local mais pas encore distant.

---

# 50. Commit as Effect?

Décision recommandée :

```text
local git commit
→ not necessarily Protected Effect
```

tant qu’il est confiné au workspace.

---

# 51. Git push

`git push` produit un effet externe durable.

Donc :

```text
Effect
```

---

# 52. Git push EffectKind

Exemple :

```text
github.git_push
git.remote_push
```

---

# 53. Git push Protected Effect

Selon branch :

```text
feature/*
→ HIGH or configurable

main
→ CRITICAL
```

---

# 54. Protected branches

PyAgentsKit doit respecter et compléter :

```text
GitHub/GitLab branch protection
```

---

# 55. `--force-with-lease`

Pour push forcé :

```text
expected remote SHA
```

doit être utilisé quand applicable.

---

# 56. Commit SHA as ExternalReference

Après push :

```text
ExternalReference(
    system="git",
    kind="commit",
    value=<sha>
)
```

---

# 57. Push reconciliation

Si timeout :

```text
inspect remote branch SHA
```

Puis :

```text
expected SHA present
→ Effect SUCCEEDED
```

---

# 58. PR creation

Créer une PR est un :

```text
Effect
```

car elle produit une ressource distante durable.

---

# 59. PR idempotency

Clé logique candidate :

```text
repository + head branch + base branch
```

---

# 60. PR reconciliation

Après timeout :

```text
lookup open PR by head/base
```

---

# 61. PR ExternalReference

```text
provider
repository
PR number
```

---

# 62. PR merge

`merge_pull_request` est généralement :

```text
Protected Effect
```

---

# 63. Merge controls

Avant merge :

```text
Authorization
Policy
Approval
expected head SHA
required CI status
branch protection
ownership
```

---

# 64. Merge approval scope

Peut inclure :

```text
repository
PR number
head SHA
base branch
merge strategy
```

---

# 65. Merge reconciliation

Après résultat ambigu :

```text
query PR state
query merge commit SHA
```

---

# 66. Package publish

`publish_package` est un :

```text
Protected Effect
```

---

# 67. Publish identity

Scope :

```text
package name
version
artifact checksum
registry
```

---

# 68. Publish idempotency

La combinaison :

```text
package + version
```

fournit souvent une identité métier forte.

---

# 69. Publish reconciliation

Après timeout :

```text
query registry
↓
version exists?
checksum matches?
```

---

# 70. CI trigger

Déclencher un pipeline peut être :

```text
Effect
```

si cela crée une exécution distante.

---

# 71. CI status

Lire un statut CI :

```text
READ
```

---

# 72. CI approval

Certaines organisations peuvent exiger :

```text
approval before production pipeline
```

---

# 73. Deployment

Déployer est :

```text
CRITICAL Protected Effect
```

dans la plupart des environnements production.

---

# 74. Deployment scope

Inclure :

```text
environment
artifact checksum
version
target
strategy
```

---

# 75. Deployment reconciliation

Après timeout :

```text
query deployment platform
```

et vérifier :

```text
deployment reference
artifact checksum
status
```

---

# 76. Infrastructure changes

Actions :

```text
terraform plan
terraform apply
terraform destroy
```

---

# 77. Terraform plan

Généralement :

```text
READ / COMPUTE
```

mais peut accéder à des APIs/cloud state.

---

# 78. Terraform apply

Toujours traité comme :

```text
CRITICAL Effect
```

---

# 79. Terraform plan binding

Une approval de `apply` doit idéalement être liée à :

```text
plan checksum
workspace
environment
```

---

# 80. Terraform state lock

Le lease PyAgentsKit complète :

```text
Terraform native state lock
```

---

# 81. Terraform destroy

Par défaut :

```text
DENY
```

ou :

```text
break-glass + explicit approval
```

selon policy.

---

# 82. Database migrations

Une migration DB peut être :

```text
HIGH / CRITICAL Effect
```

selon environnement.

---

# 83. Migration scope

Inclure :

```text
database
environment
migration id/version
checksum
```

---

# 84. Coding workflow nominal

```text
Issue / Request
↓
Run
↓
Coding Agent starts
↓
Workspace prepared
↓
Files read/edited
↓
Tests
↓
Diff produced
↓
Commit
↓
git_push Effect
↓
PR creation Effect
↓
Run completes
```

---

# 85. Workflow avec approval

```text
Agent proposes merge
↓
Effect reserved
↓
Policy → REQUIRE_APPROVAL
↓
Run WAITING
↓
Human approves
↓
new worker may resume
↓
merge Effect executes
```

---

# 86. Workflow production deploy

```text
code change
↓
tests
↓
build artifact
↓
publish
↓
deployment proposed
↓
approval
↓
deployment
↓
reconciliation if ambiguous
```

---

# 87. Coding recovery

Après crash, le système doit reconstituer :

```text
Run
Workspace reference
Repository state
latest commit
diff artifact
Effects
Approvals
runtime handle
```

---

# 88. Workspace recoverability

Trois modèles :

```text
LOCAL_EPHEMERAL
DURABLE_VOLUME
RECONSTRUCTIBLE
```

---

# 89. Reconstructible workspace

Modèle recommandé :

```text
base repository reference
+
base commit SHA
+
patch/diff artifact
+
generated artifacts
```

permettent de recréer le workspace.

---

# 90. Workspace local loss

Si workspace perdu mais :

```text
commit/patch persisted
```

le Run peut parfois être repris.

---

# 91. Workspace unrecoverable

Si aucune donnée n’a été persistée :

```text
MANUAL_INTERVENTION
```

ou restart logique depuis dernier recovery boundary.

---

# 92. Runtime restart

Un coding agent peut être relancé avec :

```text
repository context
conversation context
latest diff
test results
Effect outcomes
```

---

# 93. Non-deterministic coding recovery

Le nouvel agent peut produire un code différent.

PyAgentsKit garantit :

```text
safety of external actions
```

pas :

```text
identical code generation
```

---

# 94. File edit replay

Les edits locaux peuvent être rejoués si le workspace est reconstruit.

---

# 95. External action replay

Ne jamais rejouer aveuglément :

```text
git push
PR create
merge
publish
deploy
apply
```

---

# 96. Coding Effects Registry

Exemple :

```text
git.remote_push
git.pull_request.create
git.pull_request.merge
registry.package.publish
ci.pipeline.trigger
deployment.execute
terraform.apply
terraform.destroy
database.migrate
```

---

# 97. Risk classification defaults

Suggestion initiale :

```text
git.remote_push(feature) → HIGH
git.remote_push(main) → CRITICAL
git.pull_request.create → MEDIUM/HIGH
git.pull_request.merge → HIGH/CRITICAL
registry.publish → HIGH
deployment.prod → CRITICAL
terraform.apply.prod → CRITICAL
terraform.destroy → CRITICAL
```

Configurable.

---

# 98. Policy example

```text
git push feature branch
→ ALLOW

create PR
→ ALLOW

merge PR to main
→ REQUIRE_APPROVAL

publish package
→ REQUIRE_APPROVAL

deploy production
→ REQUIRE_APPROVAL

terraform destroy
→ DENY
```

---

# 99. Credential brokering

Un coding agent ne devrait pas recevoir un token GitHub global.

Préférer :

```text
Runtime
↓
Tool request
↓
ToolGateway
↓
scoped Git credential
↓
specific Git operation
```

---

# 100. Git credentials

Privilèges minimaux :

```text
contents:read
contents:write only if push required
pull_requests:write if PR required
```

---

# 101. CI credentials

Ne pas exposer :

```text
deployment secret
```

au runtime si le ToolGateway peut exécuter l’action à sa place.

---

# 102. Cloud credentials

Préférer :

```text
workload identity
short-lived role assumption
environment-specific role
```

---

# 103. Repo secrets

Le workspace peut contenir :

```text
.env
credentials
certificates
```

Ils doivent être exclus ou protégés.

---

# 104. Sensitive file policy

Exemples :

```text
.env
*.pem
id_rsa
credentials.json
```

peuvent être :

```text
deny read
redacted read
approval required
```

---

# 105. Git diff leakage

Un diff peut contenir des secrets accidentels.

Avant :

```text
PR
push
publish
```

un secret scan peut être exécuté.

---

# 106. Secret scanning

Intégrations possibles :

```text
gitleaks
trufflehog
provider-native scanners
custom scanners
```

---

# 107. Static analysis

Peut être exécutée avant effets persistants :

```text
lint
type check
SAST
dependency scan
```

---

# 108. Tests as policy input

La policy peut exiger :

```text
tests pass
```

avant :

```text
merge
publish
deploy
```

---

# 109. Test evidence

Le résultat de tests peut être lié via :

```text
ArtifactReference
```

---

# 110. CI status as guard

Avant merge/deploy :

```text
required checks = green
```

peut être un prérequis.

---

# 111. Human review

PyAgentsKit peut référencer :

```text
code review approval
```

mais ne doit pas remplacer GitHub/GitLab review systems.

---

# 112. External review systems

Leurs décisions peuvent être intégrées comme :

```text
ExternalReference
```

ou comme preuve dans une `Approval`.

---

# 113. Review ≠ Approval

Une review Git :

```text
LGTM
```

ne devient pas automatiquement une `PyAgentsKit Approval` sauf mapping explicite de policy.

---

# 114. Workspace lease

Si plusieurs agents collaborent sur un même workspace :

```text
workspace lease
```

peut être utilisé.

---

# 115. Agent-to-agent collaboration

Deux coding agents peuvent :

```text
share Conversation
use separate Workspaces
exchange Messages
exchange Artifacts
```

sans partager le même process.

---

# 116. Parent/child Runs

Exemple :

```text
Parent Run = feature implementation
Child Run 1 = code generation
Child Run 2 = tests
Child Run 3 = review
```

---

# 117. Avoid workflow over-modeling

Ne pas transformer automatiquement :

```text
edit
test
commit
push
PR
```

en un moteur DAG générique.

---

# 118. Coding task semantics

Les tasks internes du runtime restent :

```text
runtime-specific
```

sauf si elles portent une importance durable PyAgentsKit.

---

# 119. Audit coding

Événements candidats :

```text
coding.workspace.created
coding.workspace.deleted
coding.command.executed
coding.tests.completed
coding.diff.created
coding.commit.created
effect.git_push.succeeded
effect.pr_created.succeeded
effect.deploy.succeeded
```

---

# 120. Coding audit payload

Inclure :

```text
repository
branch
commit SHA
workspace id
command category
artifact references
principal
worker
runtime adapter
```

sans secrets.

---

# 121. Observability coding

Métriques candidates :

```text
coding_runs_total
coding_commands_total
coding_tests_total
coding_test_failures_total
coding_workspaces_active
coding_git_push_total
coding_pr_creation_total
coding_deployments_total
```

---

# 122. Command latency

```text
coding_command_duration_seconds
test_duration_seconds
build_duration_seconds
```

---

# 123. Artifact metrics

```text
diff_artifacts_total
build_artifacts_total
test_artifacts_total
```

---

# 124. Security metrics

```text
coding_command_denied_total
workspace_boundary_violations_total
secret_scan_failures_total
protected_branch_denials_total
```

---

# 125. Coding traces

Spans candidats :

```text
coding.workspace.prepare
coding.command.execute
coding.tests.run
coding.diff.compute
coding.commit.create
coding.push
coding.pr.create
coding.deploy
```

---

# 126. Repository timeline

Vue opérateur :

```text
workspace prepared
base SHA
files changed
tests
commit SHA
push
PR
merge
deploy
```

---

# 127. Command output policy

Ne pas enregistrer toute sortie shell dans logs par défaut.

Préférer :

```text
exit code
duration
summary
artifact reference
```

---

# 128. Large logs

Stocker :

```text
Artifact
```

pour :

```text
test logs
build logs
command transcripts
```

---

# 129. Runtime transcript

Un transcript complet du coding agent peut être :

```text
sensitive
large
provider-specific
```

et ne doit pas être obligatoire pour la durabilité.

---

# 130. Minimal durable coding state

Pour recovery :

```text
Run state
RuntimeHandle
Workspace reference
Repository reference
base SHA
current SHA if committed
Diff/Patch artifact
Effect state
Approval state
```

---

# 131. Sandbox baseline

Baseline recommandée :

```text
non-root
isolated workspace
bounded filesystem
bounded process execution
no Docker socket
no host home
controlled network
resource limits
```

---

# 132. Higher-assurance sandbox

Peut utiliser :

```text
microVM
remote isolated execution
ephemeral credentials
strict egress
```

---

# 133. Container caveat

Un container n’est pas automatiquement un sandbox fort.

---

# 134. Workspace cleanup

Après Run terminal :

```text
archive required artifacts
revoke credentials
delete ephemeral workspace
```

---

# 135. Cleanup failure

Un échec de cleanup ne doit pas masquer le résultat métier, mais doit être :

```text
observable
audited if sensitive
retried safely
```

---

# 136. Orphan workspace

Un sweeper peut détecter :

```text
expired workspaces
```

---

# 137. Repo cleanliness

Avant start :

```text
expected base state
```

doit être vérifié.

---

# 138. Dirty shared repo

Si workspace préexistant est dirty :

```text
fail
isolate
or explicit policy
```

---

# 139. Branch creation

Créer une branche locale est généralement non critique.

Créer une branche distante est un :

```text
Effect
```

---

# 140. Tag creation

Local :

```text
local mutation
```

Remote push du tag :

```text
Effect
```

---

# 141. Release creation

Créer une release distante est :

```text
Effect
```

---

# 142. Release publish

Peut être `HIGH` ou `CRITICAL`.

---

# 143. Issue creation

Créer/modifier une issue distante est un Effect, généralement moins risqué.

---

# 144. Comment posting

Poster un commentaire sur PR/issue est un Effect.

---

# 145. Review submission

Soumettre :

```text
APPROVE
REQUEST_CHANGES
COMMENT
```

sur une plateforme Git est un Effect.

---

# 146. Code review impersonation

Un agent ne doit pas soumettre une review humaine sous une identité humaine sans autorisation explicite.

---

# 147. Agent identity on Git provider

Préférer :

```text
bot/service identity
```

distincte d’un humain.

---

# 148. Attribution

Chaque mutation distante doit pouvoir indiquer :

```text
human initiator
agent runtime
service principal
worker
```

dans l’audit PyAgentsKit.

---

# 149. External attribution

Si provider le permet, utiliser :

```text
bot account
commit metadata
PR labels
comments
```

sans falsifier une identité humaine.

---

# 150. Commit author

La policy doit définir :

```text
agent service author
human author
committer identity
```

---

# 151. Signed commits

Peuvent être intégrés comme contrôle supplémentaire.

---

# 152. Signing credentials

Doivent être protégés comme secrets et idéalement brokerés.

---

# 153. Branch naming policy

Peut être contrôlée :

```text
agent/<run-id>/<slug>
```

ou autre convention.

---

# 154. Commit message policy

Peut inclure :

```text
run reference
issue reference
```

sans données sensibles.

---

# 155. PR metadata

Peut inclure :

```text
Run ID
summary
test evidence
risk
artifact references
```

---

# 156. Human override

Un humain peut reprendre le workspace ou le PR.

PyAgentsKit doit alors :

```text
detect external changes
revalidate base/head SHA
```

avant poursuivre.

---

# 157. External repository drift

Le remote peut changer pendant que l’agent travaille.

Avant push/merge :

```text
fetch
compare expected SHA
```

---

# 158. Drift strategy

Options :

```text
rebase
merge
restart
manual intervention
```

selon policy.

---

# 159. Auto-rebase risk

Une rebase automatique peut modifier le code.

Elle doit être traitée comme :

```text
new change state
```

et potentiellement re-tester.

---

# 160. Test invalidation

Après rebase/merge :

```text
previous test evidence may no longer be valid
```

---

# 161. Approval invalidation

Si code/artifact change :

```text
existing approval fingerprint mismatch
→ new approval required
```

---

# 162. CI invalidation

Après nouveau commit :

```text
previous CI success
```

peut ne plus être suffisant.

---

# 163. Merge guards

Avant merge :

```text
head SHA unchanged
required tests green
required approvals valid
branch protection satisfied
```

---

# 164. Publish guards

Avant publish :

```text
artifact checksum unchanged
version expected
registry namespace authorized
approval valid
```

---

# 165. Deploy guards

Avant deploy :

```text
artifact checksum
environment
approval
current deployment state
ownership
fencing
```

---

# 166. Cost controls

Coding agents peuvent être coûteux.

Budgets :

```text
runtime duration
LLM tokens
commands
network
artifact size
```

---

# 167. Command budget

Exemple :

```text
max_commands_per_run
```

---

# 168. Tool budget

```text
max_remote_effects_per_run
```

---

# 169. Runtime budget

```text
max_runtime_duration
max_model_tokens
```

---

# 170. Infinite loop protection

Détecter :

```text
same command repeatedly
same failing test loop
same patch oscillation
```

peut être utile.

---

# 171. Human escalation

Si agent boucle :

```text
PAUSE
WAITING
manual intervention
```

---

# 172. Adapter mapping — Codex

Conceptuellement :

```text
thread → RuntimeHandle
turn → RuntimeInvocation
file edits → coding events
command exec → CommandInvocation
git push → Effect
PR → Effect
```

---

# 173. Adapter mapping — Claude Code

```text
session → RuntimeHandle
tool use → TOOL_REQUESTED
file edits → workspace activity
shell commands → command classification
git/deploy → Effects
```

---

# 174. Adapter mapping — OpenCode

```text
session → RuntimeHandle
server/CLI events → NormalizedRuntimeEvent
tools → ToolGateway
remote writes → Effects
```

---

# 175. Adapter mapping — agy

Si CLI contrôlable :

```text
process/session → RuntimeHandle
structured stdout/events → RuntimeEvents
workspace operations → coding activities
remote mutations → Effects
```

---

# 176. Adapter conformance coding

Tests supplémentaires :

```text
workspace setup
file boundary
command execution
event normalization
tool interception
resume behavior
cleanup
```

---

# 177. FULL_TOOL_CONTROL

Pour un coding adapter, nécessite idéalement :

```text
all remote side effects intercepted
shell/tool requests observable
effect classification enforceable
credential brokering possible
```

---

# 178. PARTIAL_CONTROL

Si runtime peut exécuter :

```text
arbitrary shell/network
```

hors contrôle du ToolGateway, il doit être déclaré :

```text
PARTIAL_CONTROL
```

---

# 179. OBSERVE_ONLY

Si PyAgentsKit peut seulement observer sans bloquer :

```text
OBSERVE_ONLY
```

---

# 180. Safety disclosure

L’UI/CLI doit exposer clairement le niveau réel de contrôle.

---

# 181. Coding Threats

Menaces principales :

```text
prompt injection from repository
malicious README
secret exfiltration
path traversal
symlink escape
command injection
unsafe network access
malicious dependency
CI abuse
protected branch bypass
sandbox escape
```

---

# 182. Repository Content Is Untrusted

Le contenu du repo peut contenir :

```text
prompt injection
malicious scripts
poisoned tests
malicious build files
```

---

# 183. Test Execution Is Code Execution

Exécuter :

```text
pytest
npm test
make test
```

peut exécuter du code hostile.

Il doit donc se faire dans un environnement isolé.

---

# 184. Build Execution Is Code Execution

Même règle pour :

```text
pip install
npm install
make
gradle
maven
```

---

# 185. Dependency Installation

Peut déclencher :

```text
post-install scripts
native builds
network access
```

La policy doit le prendre en compte.

---

# 186. Network isolation for tests

Dans un profil high-assurance :

```text
tests/builds may run with no network
```

ou réseau allowlisté.

---

# 187. Package manager credentials

Ne jamais injecter des registry tokens globaux dans un environnement de test non fiable.

---

# 188. CI as isolation layer

Une stratégie peut être :

```text
agent edits locally
↓
push branch
↓
CI runs tests in hardened environment
```

plutôt que tout exécuter dans le worker.

---

# 189. Local tests vs CI tests

Les deux peuvent produire des preuves distinctes.

---

# 190. Human review boundary

Pour certaines organisations :

```text
agent may create PR
but never merge
```

C’est une policy valide et simple.

---

# 191. Agent autonomy profiles

Profils candidats :

```text
READ_ONLY
EDIT_ONLY
PR_AUTHOR
MERGE_WITH_APPROVAL
FULL_RELEASE_WITH_APPROVAL
CUSTOM
```

---

# 192. READ_ONLY

Autorise :

```text
read
analyze
suggest
```

Pas :

```text
write
commit
push
```

---

# 193. EDIT_ONLY

Autorise :

```text
workspace edits
tests
diff
```

Pas de mutation distante.

---

# 194. PR_AUTHOR

Autorise :

```text
edit
test
commit
push feature branch
create PR
```

Pas de merge.

---

# 195. MERGE_WITH_APPROVAL

Ajoute :

```text
merge after explicit approval
```

---

# 196. FULL_RELEASE_WITH_APPROVAL

Ajoute :

```text
publish
deploy
```

avec contrôles renforcés.

---

# 197. CodingAgentPolicyProfile

Concept candidat :

```text
profile
allowed_actions
approval_rules
sandbox_tier
network_policy
credential_policy
```

---

# 198. Public API candidates

```text
create_coding_run(...)
inspect_workspace(...)
list_changes(...)
approve_git_push(...)
approve_merge(...)
resume_coding_run(...)
```

---

# 199. CLI candidates

```text
pyagentskit coding inspect <run_id>
pyagentskit coding diff <run_id>
pyagentskit coding workspace <run_id>
pyagentskit coding effects <run_id>
```

---

# 200. Store considerations

Coding-specific state peut être stocké via :

```text
ArtifactStore
RuntimeStore
specialized CodingStore if justified
```

---

# 201. Avoid premature CodingStore

Ne pas créer un store spécialisé tant que :

```text
Artifact + Runtime + Run references
```

suffisent.

---

# 202. Artifact candidates

```text
diff.patch
test-report.json
build.log
coverage.xml
package.whl
deployment-plan.json
```

---

# 203. Artifact checksums

Indispensables pour :

```text
publish
deploy
approval scope
reconciliation
```

---

# 204. Retention

Workspace peut être court terme.

Artifacts critiques peuvent être conservés plus longtemps.

---

# 205. Privacy

Code source peut être sensible.

Les traces/logs ne doivent pas capturer automatiquement des fichiers complets.

---

# 206. Multi-tenancy

Repository, workspace et artifacts doivent être tenant-scoped si PyAgentsKit est multi-tenant.

---

# 207. Cross-tenant workspace

Interdit.

---

# 208. External Git account

Un tenant doit utiliser :

```text
its own configured integration
```

ou un scope explicitement autorisé.

---

# 209. Coding invariants

```text
CODING-INV-01
Coding-specific concepts stay outside the generic core.

CODING-INV-02
Local file edits are not automatically Protected Effects.

CODING-INV-03
Remote persistent mutations are modeled as Effects.

CODING-INV-04
Successful remote Effects are never blindly replayed.

CODING-INV-05
Approvals bind to immutable references/fingerprints.

CODING-INV-06
Runtime credentials are least-privileged and scoped.

CODING-INV-07
Repository content is treated as untrusted input.

CODING-INV-08
Tests/builds are treated as code execution.

CODING-INV-09
Workspace boundaries are enforced.

CODING-INV-10
External Git/CI controls complement PyAgentsKit controls.
```

---

# 210. Anti-patterns

À éviter :

```text
coding-agent concepts in domain core
agent gets full GitHub admin token
direct push to main by default
deploy from unverified workspace
tests executed on host without isolation
approval not tied to SHA/checksum
blind retry of git push
trusting repository instructions
logging full source code by default
```

---

# 211. Test Strategy

Tests nécessaires :

```text
workspace creation
workspace isolation
file boundary
command classification
tool interception
git push idempotency
PR reconciliation
merge approval
publish checksum binding
deployment approval
recovery after crash
```

---

# 212. Test — Workspace Escape

Agent tente :

```text
../../outside
```

Résultat :

```text
BLOCK
```

---

# 213. Test — Symlink Escape

Créer symlink vers :

```text
/etc
```

puis tenter lecture.

Résultat :

```text
BLOCK
```

---

# 214. Test — Git Push Timeout

```text
push remote accepted
response lost
```

Recovery :

```text
inspect remote SHA
↓
mark SUCCEEDED
↓
do not replay
```

---

# 215. Test — PR Creation Timeout

```text
create PR
timeout
lookup by head/base
```

---

# 216. Test — Merge Scope Mismatch

Approval head SHA A, PR now head SHA B.

Résultat :

```text
BLOCK
new approval
```

---

# 217. Test — Publish Checksum Mismatch

Approval artifact checksum A, artifact now B.

Résultat :

```text
BLOCK
```

---

# 218. Test — Deployment Takeover

Worker A obtient approval puis crash.

Worker B :

```text
takeover
revalidate approval
verify artifact checksum
deploy
```

---

# 219. Test — Malicious Repository

Repository contient instruction de voler secrets.

Résultat attendu :

```text
no implicit secret exposure
no unauthorized external request
```

---

# 220. Test — Network Denial

Runtime tente endpoint non autorisé.

Résultat :

```text
blocked by sandbox/network policy
```

---

# 221. Test — Command Budget

Agent boucle sur commandes.

Résultat :

```text
budget exhausted
pause/fail/manual intervention
```

---

# 222. Test — External Drift

Remote branch change pendant Run.

Résultat :

```text
expected SHA mismatch
safe stop/rebase/manual path
```

---

# 223. Test — Rebase invalidates approval

Après rebase :

```text
new diff / SHA
```

ancienne approval doit être invalidée si scope ne correspond plus.

---

# 224. Test — Runtime restart

Perdre process adapter puis reprendre avec :

```text
Run
workspace
diff
Effects
```

sans répéter les remote Effects.

---

# 225. Production Qualification

Un coding adapter est production-ready lorsque :

```text
workspace isolation tested
shell boundary tested
tool interception qualified
Git Effect reconciliation tested
credentials least-privileged
takeover tested
security audit passed
```

---

# 226. Acceptance Criteria

Le modèle Coding Agent Integration est opérationnel si :

1. les coding agents passent par `AgentRuntimeAdapter` ;
2. les concepts coding restent hors du core ;
3. le workspace est explicitement modélisé ;
4. les boundaries filesystem sont contrôlées ;
5. les commandes sont classifiées ;
6. les remote mutations deviennent des Effects ;
7. git push, PR, merge, publish et deploy disposent de stratégies de recovery ;
8. approvals peuvent être liées à SHA/checksum ;
9. les credentials sont scoped ;
10. les branches protégées restent une défense externe ;
11. recovery après crash ne rejoue pas les remote Effects ;
12. les coding agents disposent d’une baseline de sandbox ;
13. repository content est traité comme non fiable ;
14. tests/builds sont traités comme exécution de code ;
15. le niveau `OBSERVE_ONLY/PARTIAL_CONTROL/FULL_TOOL_CONTROL` est exposé ;
16. audit et observabilité couvrent le flux jusqu’aux mutations distantes.

---

# 227. Architecture cible

```text
                   Issue / User Request
                           │
                           ▼
                          Run
                           │
                           ▼
                 Coding Runtime Adapter
                           │
                           ▼
                     Coding Agent
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          Workspace      Commands      Tests
              │            │            │
              └────────────┼────────────┘
                           ▼
                      Diff / Build
                           │
                           ▼
                      ToolGateway
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
     git_push          PR / Merge        Publish / Deploy
        │                  │                  │
        └──────────────────┼──────────────────┘
                           ▼
                 Effect Safety Layer
                           │
                    Policy / Approval
                           │
                 Ownership / Fencing
                           │
                           ▼
                 Git / CI / Registry / Cloud
```

---

# 228. Flux nominal

```text
Run starts
↓
workspace prepared
↓
agent edits
↓
tests
↓
diff artifact
↓
local commit
↓
git_push Effect
↓
PR create Effect
↓
audit
↓
Run complete
```

---

# 229. Flux avec human governance

```text
Agent proposes merge
↓
Effect reserved
↓
Policy requires approval
↓
Run WAITING
↓
Human approves exact head SHA
↓
Run wakes
↓
lease acquired
↓
approval revalidated
↓
merge Effect
```

---

# 230. Flux recovery

```text
Worker crash after git push
↓
new worker takeover
↓
load Run / Effect / workspace refs
↓
push Effect = STARTED stale
↓
query remote branch SHA
↓
confirmed success
↓
resume coding runtime
```

---

# 231. Flux deploy

```text
build artifact
↓
checksum
↓
publish
↓
deployment Effect proposed
↓
ApprovalScope(environment + checksum)
↓
approved
↓
deploy
↓
reconcile if ambiguous
```

---

# 232. Questions ouvertes

```text
Q-CODE-01 CodingAgentAdapter dédié ou capabilities seulement ?
Q-CODE-02 CodingWorkspace doit-il être une entité core extension ?
Q-CODE-03 Quel sandbox tier minimum pour production ?
Q-CODE-04 Git commit local doit-il être un Effect ?
Q-CODE-05 Quels coding Effects sont P0 ?
Q-CODE-06 Repository lease nécessaire dès v1 ?
Q-CODE-07 Quel modèle standard de DiffReference ?
Q-CODE-08 Faut-il formaliser TestExecution ?
Q-CODE-09 Quel modèle d’autonomy profile public ?
Q-CODE-10 Comment conserver/reconstruire les workspaces ?
Q-CODE-11 Quel niveau de command observability ?
Q-CODE-12 Comment intégrer les review systems Git externes ?
```

---

# 233. ADR induits

```text
ADR-CODE-001 Coding concepts outside core
ADR-CODE-002 Coding workspace model
ADR-CODE-003 Shell command classification
ADR-CODE-004 Git push as Effect
ADR-CODE-005 PR create/merge semantics
ADR-CODE-006 Publish/deploy Effect model
ADR-CODE-007 Sandbox baseline
ADR-CODE-008 Repository concurrency strategy
ADR-CODE-009 Coding autonomy profiles
ADR-CODE-010 Credential brokering for coding agents
ADR-CODE-011 Workspace recovery strategy
ADR-CODE-012 Coding adapter conformance
```

---

# 234. Definition of Done

L’intégration coding-agent est mature lorsque :

1. au moins un coding runtime implémente l’adapter ;
2. workspace et repository sont explicitement gérés ;
3. filesystem et shell sont isolés ;
4. git push est un Effect protégé ;
5. PR create/merge sont couverts ;
6. package publish est couvert ;
7. deployment est couvert ;
8. approval SHA/checksum binding fonctionne ;
9. credential brokering est disponible ;
10. crash autour d’un push/publish/deploy est qualifié ;
11. takeovers sont testés ;
12. secret scanning et boundary tests existent ;
13. le contrôle réel de l’adapter est déclaré ;
14. observability/audit est complet ;
15. les contrôles Git/CI natifs sont utilisés plutôt que remplacés ;
16. le core reste framework-neutral et coding-agent-neutral.

---

# 235. Résumé

L’intégration des coding agents repose sur :

```text
AGENT RUNTIME ADAPTER
+
ISOLATED WORKSPACE
+
COMMAND POLICY
+
ARTIFACT / DIFF REFERENCES
+
PROTECTED REMOTE EFFECTS
+
APPROVAL
+
OWNERSHIP / FENCING
+
SCOPED CREDENTIALS
+
AUDIT
```

La frontière principale est :

```text
LOCAL / REVERSIBLE WORK
        vs
REMOTE / PERSISTENT EFFECTS
```

Ainsi :

```text
read file
edit file
run tests
local commit
```

peuvent rester dans le domaine du workspace,

alors que :

```text
git push
create PR
merge
publish
deploy
terraform apply
```

sont traités comme des Effects dont la sûreté doit être explicitement garantie.

Le principe central est :

> **PyAgentsKit ne doit pas apprendre à coder à la place du coding agent ; il doit savoir quand ce code quitte le workspace pour produire une conséquence réelle.**

Le document suivant naturel est :

```text
../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md
```
