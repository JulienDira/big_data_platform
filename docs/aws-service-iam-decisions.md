# Decisions AWS et IAM

Ce fichier garde les choix de services et les limites IAM du projet.

## Services retenus

| Besoin | Choix | Commentaire |
|---|---|---|
| Ingestion Binance | ECS/Fargate + Kinesis | Le producer publie des candles Avro avec la cle `symbol|interval` |
| Raw et Bronze | Glue Streaming + S3 | Raw garde l'enveloppe, Bronze decode et isole les rejets |
| Silver et Gold | Glue Spark batch + S3 | Silver nettoie, Gold calcule les indicateurs |
| SQL analytique | Glue Data Catalog + Athena | Athena lit les tables S3 cataloguees |
| Latest metrics | DynamoDB | Cache latest uniquement, pas source historique |
| API | API Gateway + Lambda | Lecture des donnees preparees |
| Auth | Cognito | Hosted UI et JWT authorizer API Gateway |
| Dashboard | Streamlit Cloud | Appelle l'API, ne lit pas AWS data services directement |
| Observabilite | CloudWatch + Budget | Logs, alarmes simples et budget POC |
| Deploiement | GitHub Actions OIDC + Terraform | Pas de cles AWS longue duree comme chemin normal |

Services explicitement hors perimetre pour cette cible: RDS/PostgreSQL AWS,
MSK, EMR, Redshift et Lake Formation.

## Roles IAM

| Role | Acces attendu |
|---|---|
| Producer ECS task | Ecrire dans Kinesis et ses logs |
| Producer execution role | Pull ECR et logs ECS |
| Raw Glue role | Lire Kinesis, ecrire Raw S3, checkpoints et logs |
| Lake transform role | Lire Raw/Bronze, ecrire Bronze/Silver/rejets et logs |
| Glue batch role | Lire/ecrire les prefixes S3 batch et le Glue Catalog utile |
| Step Functions role | Lancer Silver, Gold et la projection latest metrics |
| Scheduler role | Declencher la state machine |
| API Lambda role | Lire DynamoDB latest et interroger Athena |
| Projection Lambda role | Lire `trading_gold.market_indicators_latest` et ecrire DynamoDB |

Regle importante: un role ne doit pas recevoir les droits d'une autre couche
par confort. Raw ne modifie pas Bronze/Silver/Gold. L'API ne modifie pas le
lake. Streamlit n'a pas de droits AWS data.

## Etat de validation

La chaine locale est validee sur l'environnement projet. La cible AWS est
preparee dans le repo, mais la preuve runtime AWS reste a faire.

Voir [aws-target.md](aws-target.md) pour le flux cible et les preuves
manquantes.
