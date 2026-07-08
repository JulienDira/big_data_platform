# Deploiement AWS

Ce dossier contient les stacks Terraform de la cible AWS dev/POC.

## Flux normal

```text
push main
-> validate
-> publish immutable artifacts
-> terraform apply
-> deployment summary
```

Le chemin normal utilise GitHub Actions OIDC avec un role AWS dedie. Ne pas
utiliser `AWS_ACCESS_KEY_ID` ou `AWS_SECRET_ACCESS_KEY` comme methode de
deploiement recurrente.

## Stacks

| Dossier | Contenu |
|---|---|
| `core` | Kinesis, ECR, ECS/Fargate, IAM producer, logs |
| `batch` | S3 lake, Glue jobs, Glue Catalog, Athena |
| `serving` | DynamoDB, Lambda/API, Cognito, alarms, Budget |
| `orchestration` | Step Functions, EventBridge Scheduler, verrou DynamoDB |

## Bootstrap unique

Avant le premier deploiement GitHub:

1. Creer le bucket S3 de state Terraform avec chiffrement, versioning et acces
   public bloque.
2. Autoriser les lockfiles S3 Terraform sur les cles `.tflock`.
3. Creer le bucket S3 des artefacts CI.
4. Creer le provider OIDC GitHub dans AWS si absent.
5. Creer un role AWS de deploiement limite au repo et a l'environnement
   GitHub `dev`.
6. Configurer les variables GitHub Environment `dev`.

Variables GitHub attendues:

| Variable | Role |
|---|---|
| `AWS_ACCOUNT_ID` | Compte AWS autorise |
| `AWS_DEPLOY_ROLE_ARN` | Role assume par GitHub OIDC |
| `AWS_REGION` | Region AWS |
| `AWS_ARTIFACT_BUCKET` | Bucket artefacts Glue/Lambda |
| `TF_STATE_BUCKET` | Bucket state Terraform |
| `TF_STATE_REGION` | Region du bucket state |
| `VPC_ID` | VPC ECS/Fargate |
| `FARGATE_SUBNET_IDS` | Liste Terraform des subnets |
| `STREAMLIT_CALLBACK_URLS` | URLs callback Cognito |
| `STREAMLIT_LOGOUT_URLS` | URLs logout Cognito |
| `API_CORS_ALLOWED_ORIGINS` | Origines CORS autorisees |
| `ALERT_EMAIL` | Optionnel, notifications budget/alarmes |

## Artefacts

La CI publie des artefacts immuables bases sur le commit SHA:

- image producer dans ECR;
- scripts Glue;
- `jobs-utils.zip`;
- registry SQL Serving;
- contrat Avro;
- package Lambda `apps/aws-serving-api`.

Terraform consomme ces tags et cles S3. En mode CI, il ne doit pas construire
les zips depuis le working tree.

## Synthese de deploiement

Le workflow ecrit une synthese courte apres le `terraform apply`:

```powershell
python infra/scripts/aws-runtime-validate.py
```

Le script lit les outputs Terraform, verifie que les artefacts immuables
attendus existent et ecrit `build/aws-runtime-evidence.json`. Cette synthese ne
demarre pas ECS, ne lance pas les jobs Glue, ne requete pas Athena et ne prouve
pas le runtime complet.

## Verifications runtime manuelles

La validation AWS complete reste a faire dans un vrai compte AWS, pendant une
fenetre controlee. Elle doit verifier au minimum:

- image ECR disponible;
- ECS producer stable puis ramene a `0`;
- records dans Kinesis;
- Raw et Bronze Glue Streaming ecrivent dans S3;
- Silver et Gold Glue batch terminent avec succes;
- tables Glue visibles;
- requetes Athena valides;
- projection DynamoDB latest metrics;
- API Gateway/Lambda avec auth Cognito;
- logs, alarmes et Budget.

## Nettoyage

Detruire dans l'ordre inverse des dependances:

```powershell
terraform -chdir=infra/aws/orchestration destroy
terraform -chdir=infra/aws/serving destroy
terraform -chdir=infra/aws/batch destroy
terraform -chdir=infra/aws/core destroy -var="ecr_force_delete=true"
```

Avant de supprimer `core`, vider le repository ECR si des images immuables ont
ete publiees.

## References utiles

- GitHub OIDC pour AWS: https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- Terraform S3 backend: https://developer.hashicorp.com/terraform/language/backend/s3
- AWS IAM OIDC: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html
