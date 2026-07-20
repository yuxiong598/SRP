import base64
import json
import mimetypes
import os
import re
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from difflib import SequenceMatcher


AI_OCR_API_URL = os.getenv("AI_OCR_API_URL", "https://api.openai.com/v1/chat/completions")
AI_OCR_API_KEY = os.getenv("AI_OCR_API_KEY", "")
AI_OCR_MODEL = os.getenv("AI_OCR_MODEL", "gpt-4o-mini")
AI_OCR_TIMEOUT = float(os.getenv("AI_OCR_TIMEOUT", "30"))


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


def clean_text(text):
    text = str(text or "").replace("\n", " ")
    text = re.sub(r"[|_`~]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalise(value):
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(value or "").lower())


def _split_aliases(alias):
    if not alias:
        return []
    return [item.strip() for item in re.split(r"[;,/，；、]+", str(alias)) if item.strip()]


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
            for word in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", str(raw_text or "")):
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


def _image_data_url(image_path):
    mime_type = mimetypes.guess_type(image_path)[0] or "image/jpeg"
    with open(image_path, "rb") as image_file:
        image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    return f"data:{mime_type};base64,{image_base64}"


def _candidate_prompt(db_chemicals=None):
    candidates = []
    for chem in (db_chemicals or [])[:80]:
        parts = [
            f"name={chem.get('name') or ''}",
            f"alias={chem.get('alias') or ''}",
            f"cas_no={chem.get('cas_no') or ''}",
            f"specification={chem.get('specification') or ''}",
            f"location={chem.get('location') or ''}",
        ]
        candidates.append("; ".join(parts))
    return "\n".join(candidates)


def _build_ai_payload(image_path, db_chemicals=None):
    candidate_text = _candidate_prompt(db_chemicals)
    prompt = (
        "你是化学品试剂瓶标签识别助手。请直接识别图片中的标签文字，"
        "提取化学品名称、别名/CAS号、试剂瓶规格或体积、危险性、存放位置等信息。"
        "如果数据库候选中有匹配项，优先使用候选里的标准名称。"
        "只返回 JSON，不要解释。字段必须包含："
        "name, confidence, specification, bottle_volume, cas_no, hazard, location, raw_text, extra。"
        "confidence 为 0 到 1 的数字；不能确定的字段填空字符串。\n\n"
        f"数据库候选：\n{candidate_text or '无'}"
    )
    return {
        "model": AI_OCR_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": _image_data_url(image_path)}},
                ],
            }
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def _extract_response_text(response_json):
    if isinstance(response_json, dict):
        if isinstance(response_json.get("output_text"), str):
            return response_json["output_text"]
        choices = response_json.get("choices")
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "".join(item.get("text", "") for item in content if isinstance(item, dict))
        if any(key in response_json for key in ("name", "raw_text", "specification", "bottle_volume")):
            return json.dumps(response_json, ensure_ascii=False)
    return ""


def _parse_json_text(text):
    text = clean_text(text)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _call_ai_ocr(image_path, db_chemicals=None):
    if not AI_OCR_API_KEY:
        raise RuntimeError("AI_OCR_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {AI_OCR_API_KEY}",
        "Content-Type": "application/json",
    }
    body = json.dumps(_build_ai_payload(image_path, db_chemicals), ensure_ascii=False).encode("utf-8")
    request = Request(
        AI_OCR_API_URL,
        headers=headers,
        data=body,
        method="POST",
    )
    try:
        with urlopen(request, timeout=AI_OCR_TIMEOUT) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AI OCR request failed: HTTP {exc.code} {detail}") from exc

    return _parse_json_text(_extract_response_text(response_json))


def _best_db_match(ai_result, db_chemicals=None):
    raw_parts = [
        ai_result.get("name"),
        ai_result.get("cas_no"),
        ai_result.get("raw_text"),
        ai_result.get("extra"),
    ]
    return identify_chemical_name(" ".join(str(part or "") for part in raw_parts), db_chemicals)


def _normalise_result(ai_result, db_chemicals=None):
    if not isinstance(ai_result, dict):
        ai_result = {"raw_text": str(ai_result or "")}

    ai_result = {key: (clean_text(value) if isinstance(value, str) else value) for key, value in ai_result.items()}
    db_match = _best_db_match(ai_result, db_chemicals)
    chemical = db_match.get("chemical") or {}

    try:
        confidence = float(ai_result.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0
    confidence = max(confidence, db_match.get("confidence", 0))

    specification = ai_result.get("specification") or ai_result.get("bottle_volume") or chemical.get("specification", "")
    bottle_volume = ai_result.get("bottle_volume") or specification
    raw_text = ai_result.get("raw_text") or ai_result.get("extra") or ""

    return {
        "name": db_match["name"] if db_match.get("confidence", 0) >= 0.58 else ai_result.get("name", ""),
        "confidence": round(min(confidence, 0.99), 3),
        "matched_token": db_match.get("matched_token"),
        "source": db_match.get("source", "ai"),
        "specification": specification,
        "bottle_volume": bottle_volume,
        "cas_no": ai_result.get("cas_no") or chemical.get("cas_no", ""),
        "hazard": ai_result.get("hazard") or chemical.get("hazard", ""),
        "location": ai_result.get("location") or chemical.get("location", ""),
        "extra": ai_result.get("extra") or raw_text,
        "raw_text": raw_text,
    }


def extract_text_from_image(image_path, lang=None):
    result = recognize_chemical_label(image_path)
    return result.get("raw_text") or result.get("extra") or result.get("name") or ""


def parse_chemical_label(raw_text, db_chemicals=None):
    text = clean_text(raw_text)
    match = identify_chemical_name(text, db_chemicals)
    chemical = match.get("chemical") or {}
    specification_match = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|mL|L|g|kg|mg))", text)
    cas_match = re.search(r"\b(\d{2,7}-\d{2}-\d)\b", text)

    return {
        "name": match["name"] if match["confidence"] >= 0.58 else "",
        "confidence": match["confidence"],
        "matched_token": match.get("matched_token"),
        "source": match["source"],
        "specification": specification_match.group(1).replace(" ", "") if specification_match else chemical.get("specification", ""),
        "bottle_volume": specification_match.group(1).replace(" ", "") if specification_match else chemical.get("specification", ""),
        "cas_no": cas_match.group(1) if cas_match else chemical.get("cas_no", ""),
        "hazard": chemical.get("hazard", ""),
        "location": chemical.get("location", ""),
        "extra": text,
        "raw_text": text,
    }


def recognize_chemical_label(image_path, db_chemicals=None, lang=None):
    ai_result = _call_ai_ocr(image_path, db_chemicals=db_chemicals)
    return _normalise_result(ai_result, db_chemicals=db_chemicals)
