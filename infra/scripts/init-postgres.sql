CREATE USER hive WITH PASSWORD 'hive';
CREATE DATABASE hive_metastore OWNER hive;

CREATE USER trading WITH PASSWORD 'trading';
CREATE DATABASE trading_gold OWNER trading;

CREATE USER airflow WITH PASSWORD 'airflow';
CREATE DATABASE airflow OWNER airflow;
