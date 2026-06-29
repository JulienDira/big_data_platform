from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServingTable:
    name: str
    sql_file: str
    target_env: str
    mode: str = "overwrite"


SERVING_TABLES = (
    ServingTable(
        name="market_indicators",
        sql_file="market_indicators.sql",
        target_env="DATAMART_INDICATORS_TABLE",
    ),
    ServingTable(
        name="market_indicators_latest",
        sql_file="market_indicators_latest.sql",
        target_env="DATAMART_LATEST_TABLE",
    ),
    ServingTable(
        name="market_multitimeframe_signals",
        sql_file="market_multitimeframe_signals.sql",
        target_env="DATAMART_MULTITIMEFRAME_TABLE",
    ),
    ServingTable(
        name="market_daily_summary",
        sql_file="market_daily_summary.sql",
        target_env="DATAMART_DAILY_SUMMARY_TABLE",
    ),
)


def get_serving_tables() -> tuple[ServingTable, ...]:
    return SERVING_TABLES


def read_table_sql(table: ServingTable) -> str:
    for candidate in _sql_file_candidates(table.sql_file):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    searched = ", ".join(str(path) for path in _sql_file_candidates(table.sql_file))
    raise FileNotFoundError(f"SQL file {table.sql_file} not found. Searched: {searched}")


def render_sql(sql: str, context: dict[str, str]) -> str:
    rendered = sql
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)

    if "{{" in rendered or "}}" in rendered:
        raise RuntimeError(f"Unresolved SQL placeholder in query: {rendered[:120]}")
    return rendered


def _sql_file_candidates(name: str) -> tuple[Path, ...]:
    module_dir = Path(__file__).resolve().parent
    candidates = [
        _spark_file(name),
        Path.cwd() / name,
        module_dir / name,
        module_dir / "sql" / name,
    ]
    return tuple(path for path in candidates if path is not None)


def _spark_file(name: str) -> Path | None:
    try:
        from pyspark import SparkFiles
    except Exception:
        return None

    return Path(SparkFiles.get(name))
