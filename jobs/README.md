# Jobs Spark

Les jobs sont organises par etape du pipeline:

| Job | Role |
|---|---|
| `raw-consumer` | Lit Kafka et ecrit l'enveloppe Raw dans HDFS |
| `bronze-ingestion` | Decode Raw, applique les controles techniques et ecrit Bronze |
| `silver-transformation` | Reconstruit la table Hive des bougies propres |
| `gold-indicators` | Calcule les indicateurs analytiques dans Hive |
| `serving-datamart` | Reconstruit les tables PostgreSQL de consultation |
| `utils` | Fonctions partagees: env, schemas, qualite, dedup, indicateurs, Hive, JDBC |

Tous les jobs passent par:

```text
spark-submit --master yarn --deploy-mode cluster
```

Les scripts de `infra/scripts` chargent la configuration depuis l'environnement
et creent l'archive `/tmp/jobs-utils.zip` pour `--py-files`.
