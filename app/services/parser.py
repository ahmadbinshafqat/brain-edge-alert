import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class ParsedDocument:
    vendor: Optional[str]
    document_date: Optional[date]
    total_amount: Optional[float]


_VENDOR_LABEL_RE = re.compile(
    r"(?:vendor|merchant|company|supplier|billed\s+by|from)\s*[:#-]\s*(?P<vendor>[^\n\r]+)",
    re.IGNORECASE,
)
_DATE_RE = re.compile(
    r"(?P<date>\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b)",
    re.IGNORECASE,
)
_TOTAL_RE = re.compile(
    r"(?:total|amount\s+due|balance\s+due|grand\s+total|paid)\s*[:#-]?\s*\$?\s*(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)",
    re.IGNORECASE,
)
_MONEY_RE = re.compile(r"\$\s*(?P<amount>\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)")


def normalize_vendor_name(value: Optional[str]) -> Optional[str]:
    """Return a clean display/search value for a vendor name.

    The parser sees messy OCR/text snippets. Keeping vendor names consistently
    stripped of labels, punctuation, and excess whitespace makes historical
    search and vendor-based anomaly comparison more reliable.
    """
    if not value:
        return None

    cleaned = value.strip()
    cleaned = re.sub(r"^(vendor|merchant|company|supplier|from|billed\s+by)\s*[:#-]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip(" \t\r\n-–—:;,.#")

    if not cleaned:
        return None

    # Avoid returning an entire OCR line that also contains obvious fields.
    cleaned = re.split(r"\s{2,}|\t|\b(?:date|invoice|receipt|total|amount)\b\s*[:#-]", cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    cleaned = cleaned.strip(" \t\r\n-–—:;,.#")
    return cleaned or None


def parse_document(text: str) -> ParsedDocument:
    text = text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    vendor = _parse_vendor(text, lines)
    document_date = _parse_date(text)
    total_amount = _parse_total(text)

    return ParsedDocument(vendor=vendor, document_date=document_date, total_amount=total_amount)


def _parse_vendor(text: str, lines: list[str]) -> Optional[str]:
    labeled = _VENDOR_LABEL_RE.search(text)
    if labeled:
        return normalize_vendor_name(labeled.group("vendor"))

    # In many receipts/invoices the first meaningful line is the merchant.
    for line in lines[:6]:
        candidate = normalize_vendor_name(line)
        if not candidate:
            continue
        if _TOTAL_RE.search(candidate) or _DATE_RE.search(candidate) or _MONEY_RE.search(candidate):
            continue
        if len(candidate) > 80:
            continue
        return candidate
    return None


def _parse_date(text: str) -> Optional[date]:
    match = _DATE_RE.search(text)
    if not match:
        return None

    raw = match.group("date").replace("/", "-").replace(",", "")
    formats = [
        "%Y-%m-%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%m-%d-%y",
        "%d-%m-%y",
        "%b %d %Y",
        "%B %d %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_total(text: str) -> Optional[float]:
    totals = [_amount_to_float(match.group("amount")) for match in _TOTAL_RE.finditer(text)]
    totals = [amount for amount in totals if amount is not None]
    if totals:
        # The last explicit total is usually the final amount due.
        return totals[-1]

    amounts = [_amount_to_float(match.group("amount")) for match in _MONEY_RE.finditer(text)]
    amounts = [amount for amount in amounts if amount is not None]
    if amounts:
        # Fallback for simple receipts without labels.
        return max(amounts)
    return None


def _amount_to_float(value: str) -> Optional[float]:
    try:
        return float(value.replace(",", ""))
    except (TypeError, ValueError):
        return None
