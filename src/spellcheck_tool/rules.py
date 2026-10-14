import re

from .models import Finding
from .text import anchor_replacement


def _finding(segment, match, replacement, rule, category="typography"):
    start, end, suggestions = anchor_replacement(
        segment.text, match.start(), match.end(), [replacement]
    )
    return Finding(
        segment.id,
        start,
        end,
        segment.text[start:end],
        suggestions,
        rule,
        category,
        "Document rules",
    )


def check_rules(segment, options):
    text = segment.text
    result = []
    patterns = [
        (r"\b([^\W\d_]+)\s+\1\b", lambda m: m.group(1), "REPEATED_WORD", "grammar"),
        (r"(?<=\S) {2,}(?=\S)", lambda m: " ", "EXTRA_SPACES", "typography"),
        (r" +([,;:!?])", lambda m: m.group(1), "SPACE_BEFORE_PUNCTUATION", "typography"),
    ]
    if options.thorough:
        patterns += [
            (
                r"\b(\d+) ?(km|kg|cm|mm|kW|MW|Hz|kWh)\b",
                lambda m: f"{m.group(1)} {m.group(2)}",
                "UNIT_SPACING",
                "typography",
            ),
            (
                r"(?<=[a-zäöå]),(?=[A-Za-zÄÖÅäöå])",
                lambda m: ", ",
                "SPACE_AFTER_COMMA",
                "typography",
            ),
        ]
    for pattern, replacement, rule, category in patterns:
        for m in re.finditer(pattern, text, re.IGNORECASE if rule == "REPEATED_WORD" else 0):
            value = replacement(m)
            if value != m.group():
                result.append(_finding(segment, m, value, rule, category))
    for wrong, preferred in options.terminology.items():
        if not wrong or not preferred:
            continue
        for m in re.finditer(r"(?<!\w)" + re.escape(wrong) + r"(?!\w)", text, re.IGNORECASE):
            if m.group() != preferred:
                result.append(_finding(segment, m, preferred, "TERMINOLOGY", "terminology"))
    return result
