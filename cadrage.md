# Cadrage du projet

Ce document resume les regles d'architecture du projet. Il sert a comprendre la
direction technique sans relire l'historique des travaux.

## Objectif

Faire evoluer une plateforme big data locale vers une cible AWS progressive,
en gardant la chaine on-premise utilisable pendant toute la transition.

Chaine locale actuelle:

```text
Binance REST -> Kafka -> Raw HDFS -> Bronze HDFS
-> Silver Hive -> Gold Hive -> Serving PostgreSQL
```

Chaine AWS visee:

```text
Binance -> Kinesis -> Raw/Bronze/Silver/Gold S3
-> Glue Data Catalog -> Athena
-> DynamoDB latest metrics -> API Gateway/Lambda -> Streamlit
```

PostgreSQL est uniquement une cible Serving locale. Le projet ne prevoit pas de
RDS/PostgreSQL cote AWS.

## Principes

- Une etape de pipeline correspond a un dossier dans `jobs/`.
- `main.py` porte l'execution locale/on-premise.
- `aws.py` porte l'execution AWS quand elle existe.
- Les transformations metier prennent un DataFrame et retournent un DataFrame.
- Les chemins, sessions Spark, lectures, ecritures, IAM et parametres runtime
  restent dans les entry points ou les helpers IO.
- La logique commune vit d'abord dans `jobs/utils`.
- Les contrats, chemins, tables, symboles et intervalles doivent avoir une
  source de verite claire dans `contracts/`, `config/` ou un helper partage.
- Les changements doivent rester petits, lisibles et compatibles avec la
  plateforme locale.

## Couches de donnees

| Couche | Role |
|---|---|
| Raw | Conserve l'enveloppe source et les metadonnees techniques |
| Bronze | Decode les payloads et isole les rejets techniques |
| Silver | Garde les candles fermees, propres, typees et dedupliquees |
| Gold | Calcule les indicateurs analytiques |
| Serving | Publie les vues de consultation |

Gold contient les indicateurs techniques: EMA, MACD, RSI et Bollinger.
Serving ne recalcule pas les indicateurs. Il projette les resultats pour la
consultation.

## Organisation

| Zone | Contenu |
|---|---|
| `apps/` | Producteur, API AWS et dashboard |
| `contracts/` | Contrat Avro canonique |
| `config/` | Valeurs locales et noms de chemins/tables |
| `jobs/` | Jobs Spark par couche |
| `jobs/utils/` | Schemas, qualite, deduplication, indicateurs, IO |
| `jobs/serving-datamart/sql/` | SQL des restitutions |
| `infra/compose/` | Runtime Docker local |
| `infra/aws/` | Terraform AWS |
| `orchestration/` | DAGs Airflow locaux |
| `docs/` | Documentation de couches et cible AWS |

## Validation

Validation locale standard:

```powershell
.\platform.ps1 test
```

Validation batch locale complete, apres ingestion de donnees:

```powershell
.\platform.ps1 run-silver
.\platform.ps1 run-gold
.\platform.ps1 run-serving
```

Une validation statique ou des tests unitaires ne prouvent pas le runtime. Pour
dire qu'une chaine est validee, il faut avoir verifie les surfaces reelles:
YARN, HDFS/Hive, PostgreSQL ou les services AWS concernes.

## Etat actuel

- La chaine locale Raw -> Bronze -> Silver -> Gold -> Serving existe.
- Les jobs Silver, Gold et Serving locaux ont deja ete valides en runtime dans
  l'environnement projet.
- La cible AWS est preparee dans le code et Terraform: producer Kinesis,
  Raw/Bronze streaming, Silver/Gold Glue, `trading_gold`, API, Cognito,
  Streamlit et observabilite.
- La validation runtime AWS reste a faire dans un vrai compte AWS avec le
  bootstrap GitHub/AWS en place.

Voir [docs/aws-target.md](docs/aws-target.md) pour le detail AWS.
