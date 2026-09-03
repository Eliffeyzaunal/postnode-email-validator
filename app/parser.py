import csv
import io
from pathlib import Path


EMAIL_HEADERS = {"email", "e-mail", "mail", "eposta", "e_posta", "e-posta"}


class InputError(ValueError):
    pass


def parse_bytes(content: bytes, filename: str, max_rows: int = 10_000) -> list[str]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputError("Dosya UTF-8 kodlamasında olmalıdır.") from exc
    suffix = Path(filename).suffix.casefold()
    if suffix == ".txt":
        values = [line.strip() for line in text.splitlines() if line.strip()]
    elif suffix == ".csv":
        values = _parse_csv(text)
    else:
        raise InputError("Yalnızca .csv ve .txt dosyaları desteklenir.")
    if not values:
        raise InputError("Dosyada e-posta adresi bulunamadı.")
    if len(values) > max_rows:
        raise InputError(f"Dosya en fazla {max_rows} adres içerebilir.")
    return values


def _parse_csv(text: str) -> list[str]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    if not rows:
        return []
    header = [cell.strip().casefold() for cell in rows[0]]
    email_index = next((i for i, value in enumerate(header) if value in EMAIL_HEADERS), 0)
    start = 1 if any(value in EMAIL_HEADERS for value in header) else 0
    return [
        row[email_index].strip()
        for row in rows[start:]
        if len(row) > email_index and row[email_index].strip()
    ]

