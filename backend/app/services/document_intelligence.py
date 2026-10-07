from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class DocumentClassification:
    document_type: str
    confidence: float
    reasons: list[str]


DOCUMENT_TYPES = (
    "maintenance_plan",
    "work_order",
    "road_inspection_report",
    "bill_of_quantities",
    "contract",
    "payment_certificate",
    "budget",
    "machinery_log",
    "material_request",
    "material_delivery_note",
    "official_letter",
    "general_report",
    "unknown",
)


KEYWORDS: dict[str, tuple[str, ...]] = {
    "maintenance_plan": ("maintenance plan", "work plan", "annual plan", "maintenance program"),
    "work_order": ("work order", "job order", "work instruction", "repair order"),
    "road_inspection_report": ("road inspection", "condition survey", "road condition", "inspection report"),
    "bill_of_quantities": ("bill of quantities", "boq", "quantity takeoff", "schedule of quantities"),
    "contract": ("contract agreement", "contractor", "contract no", "contract number"),
    "payment_certificate": ("payment certificate", "interim payment", "certificate of payment", "ipc"),
    "budget": ("budget", "budget allocation", "allocated budget", "financial plan"),
    "machinery_log": ("machinery log", "equipment log", "machine hours", "operating hours", "fuel log"),
    "material_request": ("material request", "request for material", "material requisition", "material requirement"),
    "material_delivery_note": ("delivery note", "material delivery", "goods received", "delivery receipt"),
    "official_letter": ("official letter", "ref no", "reference no", "subject:"),
    "general_report": ("report", "monthly report", "progress report", "summary report"),
}


def _normalize(value: str) -> str:
    return re.sub(r"\\s+", " ", value.lower()).strip()


def classify_document(filename: str, text: str = "") -> DocumentClassification:
    """Classify a road-maintenance document using transparent keyword evidence.

    This is intentionally deterministic. An LLM can later explain or enrich the
    result, but it must not replace the evidence used for the initial class.
    """
    name = _normalize(Path(filename).stem.replace("_", " ").replace("-", " "))
    body = _normalize(text)
    combined = f"{name} {body}".strip()

    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}

    for document_type, keywords in KEYWORDS.items():
        for keyword in keywords:
            if _normalize(keyword) in combined:
                scores[document_type] = scores.get(document_type, 0) + 1
                matched.setdefault(document_type, []).append(keyword)

    if not scores:
        return DocumentClassification("unknown", 0.0, ["No known document-type keywords were found."])

    best_type = max(scores, key=lambda item: (scores[item], item))
    best_score = scores[best_type]
    total_score = sum(scores.values())
    confidence = min(0.98, 0.55 + 0.10 * best_score + 0.05 * (best_score / max(total_score, 1)))
    confidence = round(confidence, 2)

    reasons = [f"Matched: {', '.join(matched[best_type][:5])}."]
    if len(scores) > 1:
        alternatives = sorted(
            ((score, kind) for kind, score in scores.items() if kind != best_type),
            reverse=True,
        )
        reasons.append(f"Top alternative: {alternatives[0][1]} ({alternatives[0][0]} match(es)).")

    return DocumentClassification(best_type, confidence, reasons)
