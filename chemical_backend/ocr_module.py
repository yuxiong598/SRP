import os
import re
from difflib import SequenceMatcher

import cv2
import numpy as np
import pytesseract
from PIL import Image


DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(DEFAULT_TESSERACT):
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT


COMMON_CHEMICALS = [
    {"name": "sulfuric acid", "aliases": ["sulphuric acid", "H2SO4", "硫酸"]},
    {"name": "hydrochloric acid", "aliases": ["HCl", "盐酸"]},
    {"name": "nitric acid", "aliases": ["HNO3", "硝酸"]},
    {"name": "sodium hydroxide", "aliases": ["NaOH", "caustic soda", "氢氧化钠"]},
    {"name": "ethanol", "aliases": ["ethyl alcohol", "C2H5OH", "乙醇"]},
    {"name": "methanol", "aliases": ["methyl alcohol", "CH3OH", "甲醇"]},
    {"name": "acetone", "aliases": ["propanone", "丙酮"]},
    {"name": "sodium chloride", "aliases": ["NaCl", "氯化钠"]},
    {"name": "ammonia", "aliases": ["NH3", "氨水"]},
    {"name": "hydrogen peroxide", "aliases": ["H2O2", "过氧化氢"]},
]


def _resize_for_ocr(gray):
    height, width = gray.shape[:2]
    longest = max(height, width)
    if longest < 1400:
        scale = 1400 / longest
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return gray


def preprocess_variants(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"cannot read image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = _resize_for_ocr(gray)
    denoised = cv2.fastNlMeansDenoising(gray, None, 18, 7, 21)
    sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
    sharpened = cv2.filter2D(denoised, -1, sharpen_kernel)

    variants = [
        sharpened,
        cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 9),
    ]
    return variants


def clean_text(text):
    text = text.replace("\n", " ")
    text = re.sub(r"[|_`~]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_image(image_path, lang="chi_sim+eng"):
    texts = []
    config = "--oem 3 --psm 6"
    for image in preprocess_variants(image_path):
        text = pytesseract.image_to_string(Image.fromarray(image), lang=lang, config=config)
        text = clean_text(text)
        if text and text not in texts:
            texts.append(text)

    return max(texts, key=len) if texts else ""


def _normalise(value):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", value.lower())


def _split_aliases(alias):
    if not alias:
        return []
    return [item.strip() for item in re.split(r"[;,/，；、]+", alias) if item.strip()]


def _candidate_names(db_chemicals=None):
    candidates = []
    for item in COMMON_CHEMICALS:
        candidates.append({"name": item["name"], "token": item["name"], "source": "built_in"})
        for alias in item["aliases"]:
            candidates.append({"name": item["name"], "token": alias, "source": "built_in"})

    for chem in db_chemicals or []:
        if chem.get("name"):
            candidates.append({"name": chem["name"], "token": chem["name"], "source": "database", "chemical": chem})
        for alias in _split_aliases(chem.get("alias")):
            candidates.append({"name": chem["name"], "token": alias, "source": "database", "chemical": chem})
        if chem.get("cas_no"):
            candidates.append({"name": chem["name"], "token": chem["cas_no"], "source": "database", "chemical": chem})
    return candidates


def identify_chemical_name(raw_text, db_chemicals=None):
    normalized_text = _normalise(raw_text)
    if not normalized_text:
        return {"name": "", "confidence": 0, "source": "empty"}

    best = {"name": "", "confidence": 0, "source": "none"}
    for candidate in _candidate_names(db_chemicals):
        token = _normalise(candidate["token"])
        if not token:
            continue
        if token in normalized_text:
            confidence = min(0.99, 0.82 + len(token) / max(len(normalized_text), 1))
        else:
            confidence = SequenceMatcher(None, token, normalized_text).ratio()
            for word in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", raw_text):
                confidence = max(confidence, SequenceMatcher(None, token, _normalise(word)).ratio())
        if confidence > best["confidence"]:
            best = {
                "name": candidate["name"],
                "confidence": round(confidence, 3),
                "source": candidate["source"],
                "matched_token": candidate["token"],
                "chemical": candidate.get("chemical"),
            }
    return best


def parse_chemical_label(raw_text, db_chemicals=None):
    text = clean_text(raw_text)
    match = identify_chemical_name(text, db_chemicals)
    specification_match = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|mL|L|g|kg|mg))", text)
    cas_match = re.search(r"\b(\d{2,7}-\d{2}-\d)\b", text)

    hazard_words = {
        "corrosive": ["corrosive", "腐蚀"],
        "flammable": ["flammable", "易燃"],
        "toxic": ["toxic", "有毒"],
        "oxidizer": ["oxidizer", "氧化"],
        "irritant": ["irritant", "刺激"],
    }
    hazards = [name for name, words in hazard_words.items() if any(word.lower() in text.lower() for word in words)]

    chemical = match.get("chemical") or {}
    return {
        "name": match["name"] if match["confidence"] >= 0.58 else "",
        "confidence": match["confidence"],
        "matched_token": match.get("matched_token"),
        "source": match["source"],
        "specification": specification_match.group(1).replace(" ", "") if specification_match else chemical.get("specification", ""),
        "cas_no": cas_match.group(1) if cas_match else chemical.get("cas_no", ""),
        "hazard": ",".join(hazards) if hazards else chemical.get("hazard", ""),
        "location": chemical.get("location", ""),
        "extra": text,
        "raw_text": text,
    }


def recognize_chemical_label(image_path, db_chemicals=None, lang="chi_sim+eng"):
    raw_text = extract_text_from_image(image_path, lang=lang)
    return parse_chemical_label(raw_text, db_chemicals=db_chemicals)
