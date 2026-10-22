# Audit de sortie bêta OpenRouter — PyAgentsKit 0.2.0b1

Date de clôture : 2026-09-05  
Cible corrective : `0.2.0rc1`

## Verdict

La bêta fournit une architecture saine et découplée, mais cinq écarts devaient être fermés avant
la release candidate. Ils sont tous corrigés dans `0.2.0rc1`.

| ID | Constat bêta | Risque | Correction RC1 |
|---|---|---|---|
| OR-01 | Preflight limité au modèle principal | Fallback incompatible après validation | Vérification de toute la chaîne et intersection des capabilities |
| OR-02 | Métadonnées absentes de l'événement terminal SSE | Fallback streaming non observable | Hook provider et métadonnées terminales filtrées |
| OR-03 | HTTP 403 toujours interprété comme authentification | Guardrail/invalid prompt mal classé | Auth uniquement si type auth ou 403 sans type stable |
| OR-04 | Snapshot « offline » nécessitant une clé fictive | Mauvaise ergonomie et faux secret | `OpenRouterCatalog.from_snapshot(...)` sans transport réseau |
| OR-05 | Snapshot sans contrôle d'intégrité | Altération silencieuse du catalogue | Schéma v2, nombre de modèles et SHA-256 canonique |

## Contrôles complémentaires

- catalogue vide refusé ;
- format snapshot v1 toujours lisible ;
- profil inconnu et objet de routage incorrect refusés ;
- allowlist possible pour figer un profil d'évaluation ;
- erreurs de choix HTTP 200 conservent le contexte de route sûr ;
- événement d'échec distingue exception PyAgentsKit et `provider_error_type` ;
- aucune donnée libre `summary`, `pipeline`, prompt ou liste d'essais n'est conservée.

## Risques résiduels acceptés

- le catalogue et les politiques OpenRouter restent dynamiques ;
- SHA-256 assure l'intégrité, pas l'authenticité du snapshot ;
- ZDR s'applique à l'inférence et non automatiquement aux plugins/outils tiers ;
- les coûts et capacités live dépendent du compte, du modèle et des endpoints disponibles ;
- aucune qualification live n'est revendiquée sans exécution explicite des gates fournies.
