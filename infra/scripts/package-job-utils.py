from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: package-job-utils.py <output-zip>")

    output = Path(sys.argv[1])
    root = Path(__file__).resolve().parents[2]
    source = root / "jobs" / "utils"
    if not source.is_dir():
        raise SystemExit(f"Missing utils package: {source}")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*.py")):
            archive.write(path, path.relative_to(source.parent))


if __name__ == "__main__":
    main()
