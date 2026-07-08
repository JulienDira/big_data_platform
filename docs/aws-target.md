# Cible AWS

Cette page decrit la cible AWS du projet et son etat actuel.

## Flux cible

```text
Binance
-> ECS/Fargate producer
-> Kinesis Data Stream
-> Glue Streaming Raw S3
-> Glue Streaming Bronze S3
-> Glue batch Silver S3
-> Glue Spark Gold S3
-> trading_gold S3
-> Glue Data Catalog + Athena
-> DynamoDB latest metrics
-> API Gateway/Lambda
-> Cognito + Streamlit
```

Raw et Bronze sont penses comme des flux streaming. Silver, Gold et la
projection latest metrics restent des traitements bornes.

## Services

| Besoin | Service retenu | Etat repo |
|---|---|---|
| Producteur Binance | ECS/Fargate + ECR | Prepare |
| Ingestion streaming | Kinesis Data Streams | Prepare |
| Raw/Bronze/Silver/Gold | S3 + Glue | Prepare |
| Catalogue et SQL | Glue Data Catalog + Athena | Prepare |
| Latest metrics | DynamoDB | Prepare |
| API | API Gateway + Lambda | Prepare |
| Authentification | Cognito | Prepare |
| Dashboard | Streamlit Cloud via API | Prepare |
| Logs et alertes | CloudWatch + Budget | Prepare |
| Deploiement | GitHub Actions OIDC + Terraform | Prepare |

Prepare signifie que le code ou Terraform existe dans le repo. Cela ne signifie
pas que le service a ete deploye ou valide dans AWS.

## Stacks Terraform

| Chemin | Role |
|---|---|
| `infra/aws/core` | Kinesis, ECR, ECS/Fargate, IAM producer, logs |
| `infra/aws/batch` | Bucket lake, Glue jobs, Glue Catalog, Athena |
| `infra/aws/serving` | DynamoDB, Lambda/API, Cognito, alarms, Budget |
| `infra/aws/orchestration` | Step Functions, EventBridge Scheduler, verrou DynamoDB |

Le schedule EventBridge reste desactive par defaut. Il ne doit etre active que
pendant une fenetre de validation controlee.

## Jobs AWS

| Job | Role |
|---|---|
| `apps/binance-producer/aws.py` | Publie les candles Avro dans Kinesis |
| `jobs/raw-consumer/aws.py` | Lit Kinesis et ecrit Raw S3 |
| `jobs/bronze-ingestion/aws.py` | Lit Raw S3, decode Avro, ecrit Bronze et rejets |
| `jobs/silver-transformation/aws.py` | Reconstruit Silver S3 |
| `jobs/gold-indicators/aws.py` | Calcule Gold et materialise `trading_gold.*` |
| `apps/aws-serving-api` | Expose l'API et projette les latest metrics |

## Deploiement

Le chemin normal est:

```text
push main -> validate -> publish artifacts -> terraform apply -> deployment summary
```

Le deploiement GitHub doit utiliser OIDC avec un role AWS dedie. Les cles AWS
longue duree ne sont pas le chemin normal du projet.

Les artefacts publies par CI sont versionnes par commit:

- image producer ECR;
- scripts Glue;
- zips Python;
- SQL de restitution;
- contrat Avro;
- package Lambda.

Apres le `terraform apply`, `infra/scripts/aws-runtime-validate.py` ecrit une
synthese de deploiement. Elle verifie les outputs Terraform et les artefacts
versionnes, mais ne lance pas de producer, de jobs Glue, de requetes Athena ou
de Lambdas runtime.

## Ce qui reste a prouver

La validation AWS complete n'est pas prouvee tant que ces points n'ont pas ete
verifies dans un vrai compte AWS:

- role GitHub OIDC et backend Terraform operationnels;
- image producer publiee dans ECR;
- `terraform apply` reussi;
- ECS producer stable et capable d'ecrire dans Kinesis;
- Raw et Bronze Glue Streaming ecrivent dans S3;
- Silver et Gold Glue batch terminent avec succes;
- tables Glue et requetes Athena lisibles;
- projection DynamoDB latest metrics executee;
- API Gateway/Lambda repondent avec Cognito;
- dashboard Streamlit configure;
- logs, alarmes et Budget visibles;
- preuve runtime complete documentee apres execution manuelle des controles.

## Regles a conserver

- Pas de RDS/PostgreSQL cote AWS.
- Pas d'acces direct Streamlit vers S3, Athena, DynamoDB ou Glue.
- Pas de recalcul d'indicateurs dans l'API.
- IAM par composant, avec privileges minimaux.
- Runtime desactive par defaut hors fenetre de validation.
