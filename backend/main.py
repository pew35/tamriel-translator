import base64
import json
import os
import re
from typing import List, Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

from prompts import build_translation_prompt

from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from glossary_models import GlossaryTerm
from glossary_service import lookup_glossary_matches_by_candidates
from import_lang_glossary import import_glossary


SKIP_GLOSSARY_CATEGORIES = {"abbreviation", "role"}
SKIP_GLOSSARY_TERMS = {
    "dd",
    "dps",
    "th",
    "tank",
    "healer",
    "heal",
    "lfm",
    "wts",
    "wtb",
    "hm",
    "vet",
    "normal",
    "exp",
    "prog",
    "cp",
}

ENGLISH_NAMED_TERM_PATTERN = re.compile(
    r"\b[A-Z][a-z]+(?:\s+(?:of|the|and|[A-Z][a-z]+)){1,5}\b"
)
LITERAL_TRANSLATIONS = {
    "Wrath of the Order": "秩序之怒",
}

# 1. Load environment variables from .env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is missing. Please add it to backend/.env")

client = OpenAI(api_key=OPENAI_API_KEY, timeout=25.0)


# 2. Create FastAPI app
app = FastAPI(title="Tamriel Translator API")


@app.on_event("startup")
def prepare_glossary_database():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        has_glossary = db.query(GlossaryTerm.id).first() is not None
    finally:
        db.close()

    if not has_glossary:
        import_glossary()


# 3. Allow frontend to call backend later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP only. Later we can restrict this.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 4. Request / Response models
class TextTranslateRequest(BaseModel):
    text: str
    direction: Literal["zh_to_en", "en_to_zh"]



class CandidateTerm(BaseModel):
    originalTerm: str
    translatedMention: str
    category: str

class GlossaryMatch(BaseModel):
    zh: str
    en: str


class ReplacementOption(BaseModel):
    translatedMention: str
    replacement: str
    zh: str
    en: str


class ChatMessage(BaseModel):
    speaker: str
    original: str
    translation: str
    notes: List[str]
    copyText: str
    candidateTerms: List[CandidateTerm] = []
    glossaryMatches: List[GlossaryMatch] = []
    replacementOptions: List[ReplacementOption] = []

class TranslationResponse(BaseModel):
    inputType: Literal["text","screenshot"]
    direction: Literal["zh_to_en", "en_to_zh"]
    messages: List[ChatMessage]


def image_to_data_url(file_bytes: bytes, content_type: str) -> str:
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


def replace_first_case_insensitive(text: str, old: str, new: str) -> str:
    if not old.strip():
        return text

    pattern = re.compile(re.escape(old), re.IGNORECASE)
    return pattern.sub(new, text, count=1)


def find_first_case_insensitive_span(text: str, needle: str) -> tuple[int, int] | None:
    if not needle.strip():
        return None

    match = re.search(re.escape(needle), text, re.IGNORECASE)
    if not match:
        return None

    return match.start(), match.end()


def spans_overlap(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def apply_non_overlapping_replacements(
    original_text: str,
    replacements: list[dict],
) -> str:
    if not replacements:
        return original_text

    replacements = sorted(
        replacements,
        key=lambda replacement: (
            -(replacement["end"] - replacement["start"]),
            replacement["start"],
        ),
    )

    accepted = []
    occupied_spans: list[tuple[int, int]] = []

    for replacement in replacements:
        span = (replacement["start"], replacement["end"])

        if any(spans_overlap(span, occupied) for occupied in occupied_spans):
            continue

        accepted.append(replacement)
        occupied_spans.append(span)

    accepted.sort(key=lambda replacement: replacement["start"])

    output_parts = []
    cursor = 0

    for replacement in accepted:
        output_parts.append(original_text[cursor : replacement["start"]])
        output_parts.append(replacement["replacement"])
        cursor = replacement["end"]

    output_parts.append(original_text[cursor:])
    return "".join(output_parts)


def build_replacement_plan(
    original_text: str,
    candidate_replacements: list[dict],
) -> list[dict]:
    replacements = []

    for candidate_replacement in candidate_replacements:
        span = find_first_case_insensitive_span(
            original_text,
            candidate_replacement["translatedMention"],
        )

        if not span:
            continue

        replacements.append(
            {
                "start": span[0],
                "end": span[1],
                "replacement": candidate_replacement["replacement"],
            }
        )

    return replacements


def build_replacement_from_matches(matches: list[dict], direction: str) -> str:
    if direction == "zh_to_en":
        values = [match["en"] for match in matches]
    else:
        values = [match["zh"] for match in matches]

    # Remove labels like "Dungeon: "
    cleaned_values = []
    for value in values:
        value = value.replace("Dungeon:", "").replace("地牢：", "").strip()
        cleaned_values.append(value)

    unique_values = []
    for value in cleaned_values:
        if value not in unique_values:
            unique_values.append(value)

    if len(unique_values) == 1:
        return unique_values[0]

    return "[" + " / ".join(unique_values) + "]"    


def clean_glossary_value(value: str) -> str:
    return value.strip()


def build_replacement_option(
    translated_mention: str,
    match: dict,
    direction: str,
) -> dict:
    if direction == "zh_to_en":
        replacement = clean_glossary_value(match["en"])
    else:
        replacement = clean_glossary_value(match["zh"])

    return {
        "translatedMention": translated_mention,
        "replacement": replacement,
        "zh": clean_glossary_value(match["zh"]),
        "en": clean_glossary_value(match["en"]),
    }


def should_lookup_glossary(candidate: dict) -> bool:
    category = candidate.get("category", "").strip().lower()
    original_term = candidate.get("originalTerm", "").strip().lower()
    translated_mention = candidate.get("translatedMention", "").strip().lower()

    if category in SKIP_GLOSSARY_CATEGORIES:
        return False

    if original_term in SKIP_GLOSSARY_TERMS:
        return False

    if translated_mention in SKIP_GLOSSARY_TERMS:
        return False

    return True


def add_literal_notes_for_unexplained_terms(message: dict) -> None:
    original = message.get("original", "")
    notes = message.get("notes", [])
    notes_text = "\n".join(notes)

    for match in ENGLISH_NAMED_TERM_PATTERN.finditer(original):
        term = match.group(0).strip()

        if term in notes_text:
            continue

        literal_translation = LITERAL_TRANSLATIONS.get(term)

        if not literal_translation:
            continue

        notes.append(
            f"{term} literal translation: {literal_translation}. Official Chinese name not confirmed."
        )

    message["notes"] = notes


def enrich_messages_with_glossary(result: dict, db: Session) -> dict:
    direction = result.get("direction")
    messages = result.get("messages", [])

    for message in messages:
        candidate_terms = message.get("candidateTerms", [])
        all_matches = []
        replacement_options = []
        seen_options = set()

        for candidate in candidate_terms:
            if not should_lookup_glossary(candidate):
                continue

            original_term = candidate.get("originalTerm", "")
            translated_mention = candidate.get("translatedMention", "")

            if not original_term or not translated_mention:
                continue

            matches = lookup_glossary_matches_by_candidates(
                db=db,
                candidates=[original_term],
            )

            if not matches:
                continue

            for match in matches:
                option = build_replacement_option(
                    translated_mention,
                    match,
                    direction,
                )
                option_key = (
                    option["translatedMention"],
                    option["replacement"],
                    option["zh"],
                    option["en"],
                )

                if option_key not in seen_options:
                    replacement_options.append(option)
                    seen_options.add(option_key)

            all_matches.extend(matches)

        message["glossaryMatches"] = all_matches
        message["replacementOptions"] = replacement_options
        add_literal_notes_for_unexplained_terms(message)

        if all_matches:
            db_notes = [
                f"Glossary option: {match['zh']} = {match['en']}"
                for match in all_matches
            ]
            message["notes"] = message.get("notes", []) + db_notes

    return result

# 6. Health check
@app.get("/")
def health_check():
    return {"status": "ok", "service": "Tamriel Translator API"}


# 7. Text translation API
@app.post("/translate-text", response_model=TranslationResponse)
def translate_text(request: TextTranslateRequest, db: Session = Depends(get_db)):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    
   


    prompt = build_translation_prompt(
        request.direction, 
        "typed text",
       
        )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt + "\n\nUser message:\n" + request.text,
                        }
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "eso_text_translation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "inputType": {"type": "string", "enum": ["text"]},
                            "direction": {
                                "type": "string",
                                "enum": ["zh_to_en", "en_to_zh"],
                            },
                            "messages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "speaker": {"type": "string"},
                                        "original": {"type": "string"},
                                        "translation": {"type": "string"},
                                        "notes": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "copyText": {"type": "string"},
                                        "candidateTerms": {
                                            "type": "array",
                                            "items": {
                                                "type": "object", 
                                                "additionalProperties": False, 
                                                "properties": {
                                                    "originalTerm": {"type": "string"}, 
                                                    "translatedMention": {"type": "string"}, 
                                                    "category": {"type": "string"}
                                                },
                                                "required": [
                                                    "originalTerm", 
                                                    "translatedMention", 
                                                    "category"
                                                ],
                                                
                                            },
                                        },
                                    },
                                    "required": [
                                        "speaker",
                                        "original",
                                        "translation",
                                        "notes",
                                        "copyText",
                                        "candidateTerms",
                                    ],
                                },
                            },
                        },
                        "required": ["inputType", "direction", "messages"],
                    },
                }
            },
        )

        result = json.loads(response.output_text)
        result = enrich_messages_with_glossary(result, db)
        return result

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/translate-screenshot", response_model=TranslationResponse)
async def translate_screenshot(
    image: UploadFile = File(...),
    direction: Literal["zh_to_en", "en_to_zh"] = Form(...),
    db: Session = Depends(get_db),
):
    if image.content_type not in ["image/png", "image/jpeg", "image/jpg", "image/webp"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload PNG, JPG, JPEG, or WEBP.",
        )

    file_bytes = await image.read()

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image is empty.")

    image_url = image_to_data_url(file_bytes, image.content_type)
    prompt = build_translation_prompt(direction, "screenshot")

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                        },
                    ],
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "eso_screenshot_translation",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "inputType": {
                                "type": "string",
                                "enum": ["screenshot"],
                            },
                            "direction": {
                                "type": "string",
                                "enum": ["zh_to_en", "en_to_zh"],
                            },
                            "messages": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "speaker": {"type": "string"},
                                        "original": {"type": "string"},
                                        "translation": {"type": "string"},
                                        "notes": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                        },
                                        "copyText": {"type": "string"},
                                        "candidateTerms": {
                                            "type": "array",
                                            "items": {
                                                "type": "object", 
                                                "additionalProperties": False, 
                                                "properties": {
                                                    "originalTerm": {"type": "string"}, 
                                                    "translatedMention": {"type": "string"}, 
                                                    "category": {"type": "string"}
                                                },
                                                "required": [
                                                    "originalTerm", 
                                                    "translatedMention", 
                                                    "category"
                                                ],
                                                
                                            },
                                        },
                                    },
                                    "required": [
                                        "speaker",
                                        "original",
                                        "translation",
                                        "notes",
                                        "copyText",
                                        "candidateTerms",
                                    ],
                                },
                            },
                        },
                        "required": ["inputType", "direction", "messages"],
                    },
                }
            },
        )

        result = json.loads(response.output_text)
        result = enrich_messages_with_glossary(result, db)
        return result

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Model returned invalid JSON.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
