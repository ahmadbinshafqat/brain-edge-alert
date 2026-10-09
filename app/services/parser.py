import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParsedFields:
    vendor: str
    total: float | None
    date: str | None


def parse_document_fields(text: str, filename: str) -> ParsedFields:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    vendor = _parse_vendor(lines, filename)
    total = _parse_total(text)
    date = _parse_date(text)
    return ParsedFields(vendor=vendor, total=total, date=date)


def _parse_vendor(lines: list[str], filename: str) -> str:
    ignored = ("invoice", "receipt", "bill", "date", "total", "amount")
    for line in lines[:8]:
        cleaned = re.sub(r"[^A-Za-z0-9 &'.-]", "", line).strip()
        if len(cleaned) >= 3 and not cleaned.lower().startswith(ignored):
            return cleaned[:255]
    return Path(filename).stem.replace("_", " ").title()[:255]


def _parse_total(text: str) -> float | None:
    patterns = [
        r"(?:total due|amount due|grand total|balance due|total|amount)\s*[:\-]?\s*(?:USD|US\$|\$)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
        r"(?:USD|US\$|\$)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?)",
    ]
    candidates: list[float] = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            try:
                candidates.append(float(match.group(1).replace(",", "")))
            except ValueError:
                pass
        if candidates:
            return candidates[-1]
    nums = re.findall(r"\b[0-9]+\.[0-9]{2}\b", text)
    if nums:
        return max(float(n) for n in nums)
    return None


def _parse_date(text: str) -> str | None:
    patterns = [
        r"\b(20[0-9]{2}[-/][01]?[0-9][-/][0-3]?[0-9])\b",
        r"\b([01]?[0-9][-/][0-3]?[0-9][-/]20[0-9]{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace("/", "-")
    return None
