"""Collect delivery evidence on a local development MySQL database only."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy.engine import make_url
from app.config import Settings


def main() -> None:
    settings = Settings()
    url = make_url(settings.database_url)
    if url.get_backend_name() != "mysql" or url.host not in {"localhost", "127.0.0.1", "mysql"}:
        raise SystemExit("Ölçüm yalnızca yerel geliştirme MySQL'i üzerinde çalışır. DATABASE_URL ayarını kontrol edin.")
    env = dict(os.environ, DATABASE_URL=settings.database_url,
               TEST_MYSQL_DATABASE_URL=settings.database_url, BLOCKLIST_DNS_MODE="fake")
    output = ROOT / "outputs/evidence"
    output.mkdir(parents=True, exist_ok=True)
    commands = [
        ["-m", "pytest", "--junitxml=outputs/evidence/tests.xml"],
        ["scripts/evaluate.py", "--output", "outputs/evidence/evaluation.json", "--markdown", "outputs/evidence/evaluation.md"],
        ["scripts/benchmark.py", "--require-mysql", "--output", "outputs/evidence/mysql-benchmark.json", "--markdown", "outputs/evidence/mysql-benchmark.md"],
    ]
    for command in commands:
        subprocess.run([sys.executable, *command], cwd=ROOT, env=env, check=True)
    print(f"Test, değerlendirme ve gerçek MySQL ölçüm dosyaları hazır: {output}")


if __name__ == "__main__":
    main()
