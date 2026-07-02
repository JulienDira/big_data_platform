from __future__ import annotations

import argparse
import base64
import hashlib
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


GLUE_JOB_SCRIPTS = (
    "jobs/raw-consumer/aws.py",
    "jobs/bronze-ingestion/aws.py",
    "jobs/silver-transformation/aws.py",
    "jobs/gold-indicators/aws.py",
)

SERVING_SQL_FILES = (
    "market_daily_summary.sql",
    "market_indicators.sql",
    "market_indicators_latest.sql",
    "market_multitimeframe_signals.sql",
)

LAMBDA_PACKAGE_NAME = "aws-serving-api.zip"


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def write_zip_from_directory(
    *,
    source_dir: Path,
    output_zip: Path,
    archive_base: Path,
) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*.py")):
            archive.write(path, path.relative_to(archive_base).as_posix())


def write_zip_from_file(
    *,
    source_file: Path,
    output_zip: Path,
    archive_name: str,
) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output_zip, "w", ZIP_DEFLATED) as archive:
        archive.write(source_file, archive_name)


def source_hash_base64(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).digest()
    return base64.b64encode(digest).decode("ascii")


def copy_required_file(source: Path, target: Path) -> None:
    if not source.is_file():
        raise SystemExit(f"Missing required file: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def package_artifacts(repo_root: Path, output_dir: Path) -> dict[str, str]:
    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()

    if output_dir.exists():
        shutil.rmtree(output_dir)

    glue_dir = output_dir / "glue"
    lambda_dir = output_dir / "lambda"

    for relative_path in GLUE_JOB_SCRIPTS:
        copy_required_file(repo_root / relative_path, glue_dir / relative_path)

    copy_required_file(
        repo_root / "contracts/market-candle/v1.avsc",
        glue_dir / "contracts/market-candle-v1.avsc",
    )

    for sql_file in SERVING_SQL_FILES:
        copy_required_file(
            repo_root / "jobs/serving-datamart/sql" / sql_file,
            glue_dir / "sql" / sql_file,
        )

    write_zip_from_directory(
        source_dir=repo_root / "jobs/utils",
        output_zip=glue_dir / "python/jobs-utils.zip",
        archive_base=repo_root / "jobs",
    )
    write_zip_from_file(
        source_file=repo_root / "jobs/serving-datamart/registry.py",
        output_zip=glue_dir / "python/serving-registry.zip",
        archive_name="registry.py",
    )
    write_zip_from_directory(
        source_dir=repo_root / "apps/aws-serving-api",
        output_zip=lambda_dir / LAMBDA_PACKAGE_NAME,
        archive_base=repo_root / "apps/aws-serving-api",
    )

    lambda_hash = source_hash_base64(lambda_dir / LAMBDA_PACKAGE_NAME)
    (lambda_dir / f"{LAMBDA_PACKAGE_NAME}.base64sha256").write_text(
        f"{lambda_hash}\n",
        encoding="ascii",
    )

    return {
        "glue_dir": str(glue_dir),
        "lambda_zip": str(lambda_dir / LAMBDA_PACKAGE_NAME),
        "lambda_source_hash": lambda_hash,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Package AWS CI/CD artifacts.")
    parser.add_argument(
        "--output-dir",
        default="build/aws-artifacts",
        help="Directory where Glue and Lambda artifacts are written.",
    )
    args = parser.parse_args()

    result = package_artifacts(default_repo_root(), Path(args.output_dir))
    for name, value in result.items():
        print(f"{name}={value}")


if __name__ == "__main__":
    main()
