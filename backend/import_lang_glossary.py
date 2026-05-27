import csv
from pathlib import Path

from database import Base, SessionLocal, engine
from glossary_models import GlossaryTerm


Base.metadata.create_all(bind=engine)

EN_FILE = Path("glossary_data/en.lang.csv")
ZH_FILE = Path("glossary_data/zh.lang.csv")


def load_lang_file(path: Path) -> dict[tuple[str, str, str], str]:
    data = {}

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            key = (
                row["ID"].strip(),
                row["Unknown"].strip(),
                row["Index"].strip(),
            )

            text = row["Text"].strip()

            if text:
                data[key] = text

    return data


def import_glossary():
    if not EN_FILE.exists():
        raise FileNotFoundError(f"Missing file: {EN_FILE}")

    if not ZH_FILE.exists():
        raise FileNotFoundError(f"Missing file: {ZH_FILE}")

    en_data = load_lang_file(EN_FILE)
    zh_data = load_lang_file(ZH_FILE)

    shared_keys = set(en_data.keys()) & set(zh_data.keys())

    db = SessionLocal()

    inserted = 0
    updated = 0
    skipped = 0

    try:
        for key in shared_keys:
            eso_id, unknown, lang_index = key
            en_text = en_data[key]
            zh_text = zh_data[key]

            if not en_text or not zh_text:
                skipped += 1
                continue

            existing = (
                db.query(GlossaryTerm)
                .filter(
                    GlossaryTerm.eso_id == eso_id,
                    GlossaryTerm.unknown == unknown,
                    GlossaryTerm.lang_index == lang_index,
                )
                .first()
            )

            if existing:
                existing.en = en_text
                existing.zh = zh_text
                updated += 1
            else:
                term = GlossaryTerm(
                    eso_id=eso_id,
                    unknown=unknown,
                    lang_index=lang_index,
                    en=en_text,
                    zh=zh_text,
                    category="eso_term",
                )
                db.add(term)
                inserted += 1

        db.commit()

    finally:
        db.close()

    print("Import completed.")
    print(f"English rows: {len(en_data)}")
    print(f"Chinese rows: {len(zh_data)}")
    print(f"Matched rows: {len(shared_keys)}")
    print(f"Inserted: {inserted}")
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")


if __name__ == "__main__":
    import_glossary()