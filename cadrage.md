# Cadrage corrige - Portabilisation on-prem vers AWS

## 1. Objectif

L'objectif est de rendre la pipeline portable sans migration big bang. La stack
on-premise actuelle reste fonctionnelle, et une cible AWS peut executer les
memes traitements metier avec des entry points separes.

| Environnement | Stack cible |
|---|---|
| On-premise actuel | Docker Compose, Kafka, Spark Submit vers YARN, HDFS, Hive, Airflow, PostgreSQL Serving |
| AWS cible | ECS/Fargate Producer, Kinesis, Glue Spark, Glue Streaming ETL, EventBridge Scheduler, Step Functions, S3, Glue Data Catalog, Athena, DynamoDB latest metrics, API Gateway/Lambda, Cognito, Streamlit Cloud |

Cette cible AWS est une trajectoire, pas un lot d'implementation unique.
Producer/Kinesis/Glue/S3/Athena doivent etre cadres et implementes avant les
surfaces DynamoDB, API Gateway/Lambda, Streamlit et monitoring/FinOps avances.
Pour l'interface de consultation, Streamlit Cloud est le choix POC par defaut
avec authentification Cognito et acces aux donnees uniquement via API Gateway.
ECS/Fargate reste l'alternative si une interface Streamlit hebergee dans AWS
devient obligatoire. EC2 n'est pas le choix v1 sauf decision explicite.

PostgreSQL reste une cible de serving on-premise. Il n'est pas retenu comme
cible AWS dans ce cadrage. Cote AWS, les restitutions actuellement publiees en
Serving PostgreSQL doivent etre materialisees en tables Gold enrichies sur S3,
cataloguees dans Glue Data Catalog et requetables via Athena.

La chaine AWS apres Kinesis garde Raw et Bronze en Glue Streaming: Raw capture
l'enveloppe Kinesis sur S3, puis Bronze lit Raw S3 en streaming pour produire
Bronze et les rejets techniques. EventBridge Scheduler et Step Functions
orchestrent ensuite les traitements batch Silver, Gold et la projection latest
metrics vers DynamoDB. Le schedule POC cible `rate(1 minute)`, mais il reste
desactive par defaut tant que le runtime AWS n'est pas prouve.

Le document brut `Cahier des charges.docx` reste la source fonctionnelle
initiale. La synthese consultable et versionnable pour les choix de services
AWS, les roles IAM, les decisions FinOps et l'etat de conformite repo vit dans
`docs/aws-service-iam-decisions.md`.

La priorite est:

- garder une logique metier commune;
- isoler les lectures/ecritures dans les entry points ou adapters;
- eviter un framework interne lourd;
- conserver une architecture lisible et debuggable;
- valider chaque etape par tests ou jeux de reference.

## 2. Diagnostic sur l'existant

Le repo possede deja une separation utile:

```text
Raw -> Bronze -> Silver -> Gold -> Serving
```

Dans l'etat actuel:

- Raw et Bronze sont des jobs Spark Structured Streaming sur YARN;
- Silver est une table Hive de candles propres;
- Gold calcule EMA, MACD, RSI et Bollinger dans `gold.market_indicators`;
- Serving lit Gold, applique une registry SQL et reconstruit les tables
  PostgreSQL `market_indicators`, `market_indicators_latest`,
  `market_multitimeframe_signals` et `market_daily_summary`;
- `jobs/utils` contient deja une partie de la logique commune: env, qualite,
  deduplication, schemas, indicateurs, Hive et JDBC.

Conclusion: il ne faut pas creer immediatement un nouveau package
`src/market_pipeline`. Le chemin le plus simple est de consolider `jobs/utils`
comme couche commune, puis de deplacer plus tard seulement si le besoin devient
clair.

## 3. Architecture cible

La regle principale reste:

```text
Les transformations metier ne doivent pas connaitre HDFS, Hive, S3, Glue, YARN,
AWS, PostgreSQL ou DynamoDB.
```

Elles recoivent des DataFrames et retournent des DataFrames. Les sessions Spark,
les chemins, les tables et les ecritures restent dans les entry points ou les
adapters techniques.

| Zone | Role |
|---|---|
| `contracts/` | Contrat Avro et conventions de donnees |
| `config/` | Variables, chemins, tables, timeframes, symboles |
| `jobs/utils/` | Transformations et helpers communs reutilisables |
| `jobs/<etape>/main.py` | Entry point on-premise/local de l'etape |
| `jobs/<etape>/aws.py` | Entry point AWS de l'etape, seulement quand il existe |
| `jobs/serving-datamart/sql/` | Requetes de restitution reutilisables |
| `infra/` | Docker, Spark submit, images, scripts |
| `orchestration/` | DAGs Airflow on-premise |
| `tests/` | Tests unitaires, contrats, non-regression |

Convention de placement:

```text
Un dossier jobs = une etape logique de pipeline.
Plusieurs fichiers d'entry point = plusieurs environnements d'execution.
```

Exemple:

```text
jobs/gold-indicators/main.py  # on-premise: Hive/YARN
jobs/gold-indicators/aws.py   # AWS: S3/Glue/Athena
```

Cette convention evite de creer une deuxieme arborescence AWS parallele et
garde la lecture du repo centree sur les etapes metier.

## 4. Traitement Gold et Serving

La distinction a conserver est la suivante:

| Couche | On-premise | AWS |
|---|---|---|
| Silver | `silver.market_candles` dans Hive | Silver Parquet sur S3 |
| Gold analytique | `gold.market_indicators` dans Hive | `gold.market_indicators` sur S3/Glue |
| Restitution | PostgreSQL `trading_gold.*` via job Serving | tables `trading_gold.*` sur S3/Glue/Athena |

Les indicateurs techniques restent calcules en Gold. Les transformations de
restitution, comme latest metrics, signaux multitimeframe et resume journalier,
sont appliquees apres les indicateurs.

Les tables de restitution cible sont:

```text
trading_gold.market_indicators
trading_gold.market_indicators_latest
trading_gold.market_multitimeframe_signals
trading_gold.market_daily_summary
```

Cote on-premise, ces tables restent publiees dans PostgreSQL par le job
`jobs/serving-datamart`. Cote AWS, elles sont ecrites en Parquet sur S3 et
cataloguees pour Athena. DynamoDB peut etre ajoute ensuite comme cache latest
metrics temps reel, pas comme remplacement de la table historisee Athena.

## 5. Ordre d'execution recommande

Les premieres phases ont deja consolide le socle on-premise, les
transformations communes et la cible AWS statique: producer/Kinesis/ECS,
Kinesis -> S3 Raw/Bronze/Silver, Glue Gold, `trading_gold` S3/Athena, la
surface API/observabilite et l'orchestration batch EventBridge Scheduler/Step
Functions.

La validation runtime AWS globale ne doit venir qu'apres un chemin de
deploiement automatise et verifie: publication d'images ECR, artefacts Glue,
package Lambda, variables Terraform, separation claire entre Terraform et
CI/CD, puis verification statique bout en bout de chaque maillon du flux dans
l'ordre, en commencant par le producer et son infrastructure AWS. Une fois ces
preuves statiques obtenues, la phase suivante peut durcir le chemin GitHub/AWS
et lancer une validation runtime controlee si le bootstrap, les credentials et
les permissions sont disponibles.

Ordre recommande:

1. Phase de cadrage technique AWS core:
   - auditer le producer actuel, son Dockerfile et son contrat Avro;
   - definir comment exploiter le code producer sur AWS: adapter Kinesis,
     packaging ECR, execution ECS/Fargate ou alternative EC2, variables et IAM;
   - definir comment exploiter les jobs Spark existants dans Glue: scripts S3,
     zip `jobs/utils`, `--extra-py-files`, SQL de restitution, arguments Glue;
   - separer clairement les responsabilites Terraform et CI/CD;
   - definir les tests statiques/locaux attendus;
   - ne pas implementer DynamoDB, API Gateway/Lambda, Streamlit, CloudWatch
     alarms ou AWS Budgets dans cette phase.
2. Phase d'implementation AWS core:
   - appliquer le cadrage precedent;
   - ajouter les entry points/adapters AWS necessaires pour le producer,
     Kinesis, Glue/Spark et les artefacts S3;
   - completer Terraform et les tests sans introduire RDS/PostgreSQL AWS;
   - valider statiquement/localement, puis documenter les preuves runtime AWS
     encore manquantes si aucun compte n'est disponible.
3. Phase de cadrage Kinesis -> S3 Raw/Bronze/Silver:
   - definir comment consommer Kinesis pour produire les couches Raw, Bronze et
     Silver sur S3;
   - reutiliser les contrats, schemas, qualite et transformations communes
     existants;
   - cadrer Glue Streaming ETL ou une alternative batch/streaming justifiee,
     IAM, checkpoints, partitions, couts, tests et limites de runtime;
   - garder ce cadrage centre sur le lake, sans DynamoDB, API, dashboard ou
     monitoring avance.
4. Phase d'implementation Kinesis -> S3 Raw/Bronze/Silver:
   - implementer uniquement ce qui a ete cadre dans la phase precedente;
   - produire les datasets Raw, Bronze et Silver S3 necessaires au job
     `jobs/gold-indicators/aws.py`;
   - completer Terraform, packaging et tests statiques sans revendiquer de
     validation runtime AWS globale.
5. Phase de cadrage restitution/applicatif/observabilite:
   - cadrer DynamoDB latest metrics, API Gateway/Lambda, Cognito,
     Streamlit Cloud, CloudWatch alarms et AWS Budgets;
   - definir contrats, responsabilites, IAM, couts, cycle de vie et tests;
   - ne pas implementer avant decision explicite sur ce perimetre.
6. Phase d'implementation restitution/applicatif/observabilite:
   - implementer uniquement ce qui a ete cadre dans la phase precedente;
   - garder DynamoDB comme cache latest metrics, pas comme source historique;
   - garder Athena/S3/Glue comme source analytique historique;
   - garder Streamlit comme interface de consultation via API Gateway, pas
     comme lecteur direct de S3, Athena ou DynamoDB;
   - valider statiquement/localement et ne declarer le runtime AWS prouve
     qu'apres verification dans un vrai compte AWS.
7. Phase d'audit statique qualite/conformite:
   - verifier le code et Terraform sans runtime AWS;
   - confronter l'implementation aux regles du repo, aux bonnes pratiques data
     engineering, software/API, DevOps/IaC et aux recommandations fournisseurs
     officielles;
   - verifier purete, atomicite, lisibilite, source de verite unique et
     absence d'over-engineering;
   - refactorer seulement les ecarts concrets, avec des changements minimaux
     et des tests statiques/locaux;
   - documenter les ecarts restants avant toute validation runtime.
8. Phase de cadrage CI/CD et deploiement automatise:
   - definir le workflow GitHub Actions cible sur `push` vers `main`;
   - utiliser AWS OIDC, pas de cles AWS longues durees dans GitHub comme chemin
     normal;
   - cadrer le bootstrap unique: backend Terraform distant, verrouillage,
     role GitHub OIDC et variables GitHub Environment;
   - comparer Zip/S3 et ECR pour Lambda et retenir Zip/S3 par defaut pour
     `apps/aws-serving-api`;
   - definir les artefacts immuables: image producer ECR, scripts Glue,
     `jobs-utils.zip`, registry SQL, SQL, contrat Avro et package Lambda;
   - garder cette phase sans `terraform apply`, sans job Glue, sans runtime
     ECS/Kinesis et sans deploiement Streamlit Cloud.
9. Phase d'implementation CI/CD et artefacts AWS immuables:
   - implementer le workflow GitHub Actions sur `ubuntu-latest`;
   - publier les artefacts avec une version immuable basee sur le commit SHA;
   - faire consommer a Terraform les tags/cles/hashes produits par la CI/CD;
   - garder le runtime inactif par defaut avant preuve globale:
     `ecs_service_desired_count = 0`, pas de lancement Glue, projection
     schedule desactivee et pas de deploy Streamlit Cloud.
10. Phase de verification statique bout en bout par maillon:
   - verifier le code, Terraform, workflows, tests et docs sans runtime AWS;
   - avancer dans l'ordre du flux: producer/core, Raw, Bronze/Silver,
     Gold/restitution, Serving/API/dashboard/observabilite, puis CI/CD;
   - confronter chaque maillon au cadrage projet, aux regles du repo, aux
     recommandations officielles AWS/GitHub/Terraform et aux bonnes pratiques
     reconnues;
   - utiliser les articles et retours communaute uniquement comme contexte
     secondaire, sans les laisser remplacer les sources officielles ou les
     decisions projet;
   - corriger seulement les ecarts concrets par changements minimaux et
     documenter les preuves statiques et limites restantes.
11. Phase d'orchestration batch planifiee AWS:
   - creer un stack Terraform dedie pour EventBridge Scheduler, Step
     Functions et le verrou DynamoDB de la chaine batch;
   - garder Raw et Bronze en Glue Streaming et orchestrer Silver, Gold puis la
     projection latest metrics;
   - utiliser `rate(1 minute)` comme cadence POC, avec schedule desactive par
     defaut;
   - valider statiquement sans lancer Step Functions ni jobs Glue reels.
12. Phase de deploiement AWS automatise et validation runtime controlee:
   - seulement si la verification statique par maillon ne laisse pas de point
     bloquant;
   - verifier et durcir le chemin DevOps: GitHub Actions OIDC, role AWS
     de deploiement scope, GitHub Environment, backend Terraform distant,
     verrouillage, artefacts immuables et permissions minimales;
   - ne pas utiliser de cles AWS longues durees ni d'utilisateur IAM admin
     comme chemin normal de deploiement GitHub;
   - produire un README de deploiement simple expliquant le bootstrap GitHub/AWS
     et le flux `push main -> validate -> publish -> deploy -> runtime check`;
   - lancer le chemin automatise dev/POC si l'environnement le permet;
   - executer une validation runtime AWS controlee et bornee en cout: ECS
     producer, Kinesis, Glue Raw/Bronze/Silver/Gold, Step Functions,
     EventBridge Scheduler, S3, Glue Catalog, Athena, DynamoDB/API/Cognito/
     Streamlit/observabilite seulement pour les surfaces disponibles et
     configurees;
   - si les credentials, callbacks, droits ou bootstrap manquent, documenter le
     blocage exact et ne pas revendiquer de runtime proof.

## 6. Entry points attendus

### On-premise

Les entry points existants restent la surface de reference:

```text
jobs/raw-consumer/main.py
jobs/bronze-ingestion/main.py
jobs/silver-transformation/main.py
jobs/gold-indicators/main.py
jobs/serving-datamart/main.py
```

Quand une etape dispose aussi d'une execution AWS, elle garde le meme dossier
et ajoute un entry point dedie:

```text
jobs/gold-indicators/aws.py
```

Le job Serving on-premise doit:

1. lire `gold.market_indicators` depuis Hive;
2. appeler les transformations communes de restitution;
3. ecrire les resultats dans PostgreSQL.

### AWS batch et portabilisation progressive

Le premier entry point AWS est `jobs/gold-indicators/aws.py`. Il doit rester
volontairement simple:

1. lire Silver depuis S3;
2. appliquer les transformations communes Gold;
3. ecrire `gold.market_indicators` en Parquet sur S3;
4. materialiser les tables `trading_gold.*`;
5. ecrire chaque table en Parquet sur S3;
6. laisser Glue Data Catalog et Athena exposer les donnees.

Les jobs Raw et Bronze AWS restent des Glue Streaming: Raw consomme Kinesis et
Bronze consomme Raw S3 en continu. Les jobs Silver et Gold restent des jobs
Glue batch lances en chaine par Step Functions quand le schedule EventBridge
est active. Le schedule est configure a `rate(1 minute)` pour le POC, mais il
doit rester desactive avant preuve runtime controlee.

Ce premier lot AWS part de Silver S3 pour reduire le risque. Apres le socle
producer/Kinesis/ECS et le packaging Glue, la phase suivante doit cadrer le
maillon manquant Kinesis -> S3 Raw/Bronze/Silver. DynamoDB, API Gateway/Lambda,
Streamlit, CloudWatch alarms et Budgets ne doivent pas etre implementes avant
ce cadrage lake et son implementation; ils seront cadres dans une phase dediee
apres le socle producer/lake/Glue.

## 7. Regles d'architecture

| Regle | Pourquoi |
|---|---|
| Une transformation retourne un DataFrame | Testabilite et portabilite |
| Pas de SparkSession creee dans les transformations | Separation execution / metier |
| Pas de chemin HDFS/S3 hardcode dans le metier | Portabilite |
| Pas de PostgreSQL dans les transformations | Reutilisation on-prem/AWS |
| Athena lit des tables cataloguees, il n'ecrit pas les donnees | Clarifie le role des briques AWS |
| Contrats, producer/lake et Glue avant le wiring API/dashboard | Les surfaces API et dashboard dependent des schemas et sorties lake |
| Streamlit Cloud + Cognito par defaut pour le dashboard POC | Simple, securise et limite l'exploitation serveur; ECS/Fargate seulement si l'UI doit etre hebergee dans AWS |
| EventBridge Scheduler + Step Functions pour la chaine batch AWS | Declenchement regulier, ordre explicite Silver -> Gold -> projection apres Bronze streaming, erreurs lisibles |
| Cadrage technique avant implementation AWS large | Evite d'empiler les services sans decision claire de packaging, IAM et CI/CD |
| CI/CD automatisee avant runtime AWS global | Evite les validations manuelles non reproductibles |
| Runtime AWS seulement avec preuves reelles | Evite de confondre implementation, tests statiques et deploiement effectif |
| Pas de structure repo parallele inutile | Evite duplication et over-engineering |

## 8. Tests et criteres d'acceptation

Tests attendus:

- tests unitaires des transformations communes;
- tests de rendu des SQL templates de restitution;
- test de contrat pour eviter de reintegrer une cible AWS PostgreSQL;
- golden dataset comparant les sorties metier on-premise et AWS;
- validation on-premise via `run-silver`, `run-gold`, `run-serving`;
- validation statique AWS cible: `terraform fmt`, `terraform validate`, tests
  des entry points/helpers, scans de perimetre et tests de contrats;
- audit statique qualite/conformite avant runtime AWS: structure par domaine,
  fonctions pures et atomiques, source de verite unique, absence
  d'over-engineering, IAM minimal, API read-only et dashboard sans acces direct
  aux services data AWS;
- verification statique bout en bout par maillon apres CI/CD: producer/core,
  Raw, Bronze/Silver, Gold/restitution, Serving/API/dashboard/observabilite et
  CI/CD, avec sources officielles et preuves code/Terraform/workflow;
- validation de deploiement et runtime AWS cible seulement quand le chemin
  retenu est cadre, developpe, audite statiquement, deploye par CI/CD et qu'un
  compte est disponible: GitHub Actions OIDC, artefacts immuables ECR/S3,
  Terraform automatise en dev/POC, Kinesis/ECS, ingestion Raw/Bronze/Silver S3,
  Glue Gold, Step Functions/EventBridge Scheduler, Glue Catalog, Athena et
  seulement les surfaces DynamoDB/API/Cognito/dashboard/observabilite
  configurees.

Criteres d'acceptation:

- la stack on-premise reste fonctionnelle;
- `gold.market_indicators` reste la table analytique Gold;
- PostgreSQL reste limite au Serving on-premise;
- les tables `trading_gold.*` sont implementees cote AWS en S3/Glue/Athena;
- les transformations de restitution sont reutilisables par on-premise et AWS;
- les services AWS sont cadres puis developpes par lots coherents et testables
  statiquement meme avant l'acces au compte AWS;
- la documentation ne confond plus Gold, Serving et exposition applicative.

## 9. Risques

| Risque | Mitigation |
|---|---|
| Dupliquer la logique entre PostgreSQL et AWS | Extraire les transformations dans `jobs/utils` |
| Creer une nouvelle architecture trop lourde | Consolider d'abord l'existant |
| Confondre Athena et moteur d'ecriture | Spark/Glue ecrit S3, Athena lit |
| Casser l'on-premise pendant l'extraction | Rebrancher Serving sans changer son contrat public |
| Survendre la validation | Separer tests unitaires, validation statique et preuve runtime |

## 10. Instruction pour l'agent d'execution

Mission:

```text
Faire evoluer progressivement la pipeline pour partager la logique metier entre
on-premise et AWS, sans casser l'execution Docker Compose/YARN/Hive/PostgreSQL.
```

Contraintes:

- ne pas faire de migration big bang;
- ne pas transformer l'absence de credentials AWS en blocage: developper et
  tester statiquement la cible AWS tant que le runtime n'est pas disponible;
- ne pas ajouter de cible PostgreSQL AWS;
- ne pas implementer DynamoDB, API Gateway/Lambda, Cognito, Streamlit,
  CloudWatch alarms ou AWS Budgets avant une phase de cadrage dediee;
- cadrer d'abord l'exploitation du code existant: producer vers Kinesis/ECS,
  packaging ECR, jobs Spark vers Glue, artefacts S3, Terraform et CI/CD;
- cadrer puis implementer ensuite le maillon Kinesis -> S3 Raw/Bronze/Silver
  avant toute validation runtime AWS globale;
- cadrer puis implementer un systeme CI/CD automatise, puis apres l'audit
  statique AWS durcir le deploiement GitHub/AWS et executer une validation
  runtime AWS controlee seulement avec un vrai compte et des permissions
  disponibles;
- verifier statiquement l'implementation AWS par maillon du flux, en
  commencant par le producer et son infrastructure AWS, avant le deploiement
  et la validation runtime AWS controles;
- viser le contrat Avro canonique aussi cote Kinesis AWS; JSON reste acceptable
  comme simplification POC ponctuelle, mais la cible retenue est Avro binaire
  dans Kinesis et Parquet dans le lake;
- garder `jobs/utils` comme couche commune initiale;
- reutiliser la logique de restitution commune avant d'ajouter les surfaces
  streaming/API qui en dependent;
- exposer Streamlit via API Gateway et Cognito; ne pas donner au dashboard
  d'acces direct a S3, Athena, DynamoDB ou Glue dans le POC par defaut;
- garder les entry points on-premise lisibles et fins;
- documenter explicitement ce qui est valide statiquement et ce qui reste a
  prouver en runtime.

## 11. Methode d'iteration

Le projet avance par phases courtes et verifiables. Chaque phase doit distinguer
clairement:

- ce qui est fait;
- ce qui est seulement prepare;
- ce qui est valide statiquement;
- ce qui est prouve en runtime;
- ce qui reste non prouve.

Avant de demarrer une nouvelle phase, un agent doit lire:

```text
AGENTS.md
cadrage.md
docs/phase-handoff.md
```

Il doit ensuite verifier le repo reel avec `rg`, lectures de fichiers et tests
pertinents. Il ne doit pas demarrer uniquement depuis l'historique de
conversation.

En fin de phase, l'agent doit mettre a jour `docs/phase-handoff.md`. Si la
phase modifie une regle d'architecture ou une pratique durable, il doit aussi
mettre a jour `AGENTS.md`, `cadrage.md` ou la documentation de couche
concernee.
