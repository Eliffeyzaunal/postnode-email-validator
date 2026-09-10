import argparse
import json
from collections import Counter
from pathlib import Path

from app.bounce_classifier.classifier import EventClassifier
from app.bounce_classifier.io import read_events, write_jsonl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SES bounce/sikayet olaylarini siniflandirir.")
    parser.add_argument("input", type=Path, help="JSON veya JSONL olay dosyasi")
    parser.add_argument("--output", type=Path, required=True, help="Guvenli JSONL sonuc dosyasi")
    parser.add_argument("--report", type=Path, help="Ozet ve bilinmeyen oruntu JSON raporu")
    parser.add_argument("--rules", type=Path, help="Varsayilan yerine kullanilacak kural JSON dosyasi")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    classifier = EventClassifier(args.rules)
    response = classifier.classify_many(read_events(args.input))
    rows = [result.model_dump(mode="json") for result in response.results]
    write_jsonl(args.output, rows)
    if args.report:
        patterns = Counter(
            result.unknown_pattern
            for result in response.results
            if result.unknown_pattern
        )
        report = {
            "total": response.total,
            "category_counts": response.category_counts,
            "unknown_rate": response.unknown_rate,
            "top_unknown_patterns": [
                {"pattern": pattern, "count": count}
                for pattern, count in patterns.most_common(20)
            ],
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"output": str(args.output), **response.model_dump(exclude={"results"})}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
