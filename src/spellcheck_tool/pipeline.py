import re
from dataclasses import asdict
from pathlib import Path

from .engines import detect_language
from .models import DocumentError, Segment
from .pdf import annotate_pdf, read_pdf
from .rules import check_rules
from .text import PROTECTED
from .word import annotate_word, read_word


def load_document(name, data):
    if len(data) > 30 * 1024 * 1024:
        raise DocumentError("Please use a document smaller than 30 MB.")
    suffix = Path(name).suffix.lower()
    if suffix == ".pdf":
        return read_pdf(name, data)
    if suffix == ".docx":
        return read_word(name, data)
    raise DocumentError("Choose a PDF or .docx document. Convert legacy .doc files in Word first.")


def chunks(segment, limit=4500):
    start = 0
    while start < len(segment.text):
        end = min(len(segment.text), start + limit)
        if end < len(segment.text):
            candidates = list(re.finditer(r"[.!?]\s+|\n", segment.text[start:end]))
            split = (
                start + candidates[-1].end()
                if candidates
                else segment.text.rfind(" ", start + limit // 2, end)
            )
            if split > start:
                end = split
        yield (
            start,
            Segment(segment.id, segment.text[start:end], segment.location, segment.language),
        )
        start = end


def combine(findings, segments, options):
    by_id = {s.id: s for s in segments}
    glossary = {word.casefold() for word in options.glossary}
    protected = {s.id: [(m.start(), m.end()) for m in PROTECTED.finditer(s.text)] for s in segments}
    merged = {}
    for f in findings:
        s = by_id[f.segment_id]
        if f.rule in options.ignore_rules or f.end <= f.start or f.end > len(s.text):
            continue
        if s.text[f.start : f.end] != f.original:
            raise DocumentError("A proofreading engine returned invalid text offsets.")
        if f.category == "spelling":
            if f.original.casefold() in glossary:
                continue
            if options.ignore_uppercase and f.original.isupper():
                continue
        if (
            options.ignore_codes
            and f.category == "spelling"
            and any(f.start < end and f.end > start for start, end in protected[s.id])
        ):
            continue
        f.suggestions = list(
            dict.fromkeys(s for s in f.suggestions if s.strip() and s != f.original)
        )
        f.selected = bool(f.suggestions)
        key = (f.segment_id, f.start, f.end)
        if key in merged:
            previous = merged[key]
            previous.suggestions = list(dict.fromkeys(previous.suggestions + f.suggestions))[:5]
            previous.selected = bool(previous.suggestions)
        else:
            merged[key] = f
    # Keep alternatives visible, but initially select only a non-overlapping set.
    ordered = sorted(
        merged.values(),
        key=lambda f: (
            f.segment_id,
            f.start,
            0 if f.category == "terminology" else 1,
            -(f.end - f.start),
        ),
    )
    ends = {}
    for f in ordered:
        if f.start < ends.get(f.segment_id, -1):
            f.selected = False
        elif f.selected:
            ends[f.segment_id] = f.end
    return ordered


def review(document, options, engines, progress=None):
    all_findings, notes = [], list(document.warnings)
    if sum(len(s.text) for s in document.segments) > 1_000_000:
        raise DocumentError(
            "This document exceeds the one-million-character review limit. Split it into sections."
        )
    for i, segment in enumerate(document.segments):
        if options.language == "mixed":
            language, uncertain = detect_language(segment.text, engines.get_finnish())
            segment.language = language
            if uncertain:
                notes.append(
                    f"{segment.location}: uncertain language, checked as {'Finnish' if language == 'fi' else 'English'}. Choose a fixed language to override."
                )
        else:
            segment.language = options.language
        for offset, chunk in chunks(segment):
            for f in engines.check(chunk, options):
                f.start += offset
                f.end += offset
                f.original = segment.text[f.start : f.end]
                f.id = ""
                f.__post_init__()
                all_findings.append(f)
        all_findings.extend(check_rules(segment, options))
        if progress:
            progress(i + 1, len(document.segments), segment.location)
    findings = combine(all_findings, document.segments, options)
    return {
        "filename": document.name,
        "kind": document.kind,
        "pages": document.pages,
        "segments": [
            {"id": s.id, "text": s.text, "location": s.location, "language": s.language}
            for s in document.segments
        ],
        "findings": [f.to_dict() for f in findings],
        "warnings": list(dict.fromkeys(notes)),
        "options": asdict(options),
        "characters_checked": sum(len(s.text) for s in document.segments),
    }, findings


def export(document, findings, choices):
    by_id = {f.id: f for f in findings}
    selected, seen = [], set()
    for choice in choices:
        if choice["id"] not in by_id or choice["id"] in seen:
            raise DocumentError("Invalid or duplicate finding selection.")
        seen.add(choice["id"])
        f = by_id[choice["id"]]
        correction = choice.get("correction")
        if correction not in f.suggestions:
            raise DocumentError("Choose one of the available corrections.")
        selected.append((f, correction))
    previous = {}
    for f, _ in sorted(selected, key=lambda pair: (pair[0].segment_id, pair[0].start)):
        if f.start < previous.get(f.segment_id, -1):
            raise DocumentError("Two selected findings overlap. Select only one for that passage.")
        previous[f.segment_id] = f.end
    return (
        annotate_pdf(document, selected)
        if document.kind == "pdf"
        else annotate_word(document, selected)
    )
