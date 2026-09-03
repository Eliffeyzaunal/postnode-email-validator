import argparse
import csv
import json
from pathlib import Path

from app.config import Settings
from app.parser import parse_bytes
from app.privacy import email_hash, mask_email
from app.repository import Repository
from app.validator import EmailValidatorService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Postnode e-posta liste doğrulayıcısı")
    parser.add_argument("input", type=Path, help="CSV veya TXT girdi dosyası")
    parser.add_argument("--output", type=Path, default=Path("outputs/results.csv"))
    parser.add_argument(
        "--database-url",
        help="İsteğe bağlı SQLAlchemy bağlantı adresi; verilmezse .env içindeki DATABASE_URL kullanılır.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = Settings(**({"database_url": args.database_url} if args.database_url else {}))
    emails = parse_bytes(args.input.read_bytes(), args.input.name, settings.max_batch_size)
    repository = Repository(settings.database_url)
    service = EmailValidatorService(settings, repository)
    try:
        batch_id, summary, results = service.validate_many(emails, args.input.name)
    finally:
        repository.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["row_number", "masked_email", "email_hash", "domain", "status", "reason_codes", "suggestion"])
        for item in results:
            source = item.normalized or item.original
            writer.writerow([
                item.row_number,
                mask_email(source),
                email_hash(source),
                item.domain or "",
                item.status.value,
                "|".join(code.value for code in item.reason_codes),
                mask_email(item.suggestion) if item.suggestion else "",
            ])
    print(json.dumps({"batch_id": batch_id, "summary": summary, "output": str(args.output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
