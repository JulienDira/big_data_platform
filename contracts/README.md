# Contrats de donnees

`market-candle/v1.avsc` est le contrat Avro canonique des bougies de marche.
Les producteurs et consommateurs le chargent au runtime.

Regles:

- ne pas maintenir de copie privee du schema;
- garder la compatibilite Schema Registry en `BACKWARD`;
- ajouter un champ avec une valeur par defaut ou un type nullable;
- creer une nouvelle version de sujet/topic pour une rupture de contrat.
