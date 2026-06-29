from pyspark.sql import DataFrame


def qualified_table_name(table: str, schema: str = "public") -> str:
    if "." in table:
        return table
    return f"{schema}.{table}"


def write_postgres_table(
    frame: DataFrame,
    url: str,
    table: str,
    user: str,
    password: str,
    mode: str = "overwrite",
    schema: str = "public",
) -> None:
    (
        frame.write.mode(mode)
        .format("jdbc")
        .option("url", url)
        .option("dbtable", qualified_table_name(table, schema))
        .option("user", user)
        .option("password", password)
        .option("driver", "org.postgresql.Driver")
        .option("truncate", "true")
        .save()
    )

