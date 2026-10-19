import pymupdf as fitz

from .models import Document, DocumentError, Segment
from .text import normalize


def read_pdf(name, data):
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise DocumentError("This PDF could not be opened.") from exc
    with pdf:
        if pdf.is_encrypted:
            raise DocumentError(
                "Password-protected PDFs are not supported. Supply an unlocked copy."
            )
        if pdf.get_sigflags() > 0:
            raise DocumentError(
                "This PDF contains signature fields. Supply an unsigned review copy."
            )
        segments, warnings = [], []
        for pno, page in enumerate(pdf):
            page_chars = 0
            for bno, block in enumerate(page.get_text("rawdict", sort=True)["blocks"]):
                if block["type"] != 0:
                    continue
                chars, refs = [], []
                for lno, line in enumerate(block["lines"]):
                    if abs(line["dir"][1]) > 0.01 or line["dir"][0] < 0:
                        warnings.append(f"Page {pno + 1}: rotated text was not checked.")
                        continue
                    if chars:
                        # The source hyphen remains untouched; only the analysis string is joined.
                        if chars[-1] == "-" and len(chars) > 1 and chars[-2].isalpha():
                            chars.pop()
                            refs.pop()
                        else:
                            chars.append(" ")
                            refs.append(None)
                    for span in line["spans"]:
                        for ch in span["chars"]:
                            chars.append(ch["c"])
                            refs.append((pno, bno, lno, tuple(ch["bbox"])))
                text, mapping = normalize("".join(chars), refs)
                if text.strip():
                    segments.append(Segment(f"p{pno}b{bno}", text, f"Page {pno + 1}", refs=mapping))
                    page_chars += len(text.strip())
            if page_chars < 10:
                warnings.append(
                    f"Page {pno + 1}: little or no selectable text; image text was not checked."
                )
        if not segments:
            raise DocumentError(
                "No selectable text was found. Run OCR first and upload the searchable PDF."
            )
        return Document(name, data, "pdf", segments, list(dict.fromkeys(warnings)), len(pdf))


def annotate_pdf(document, selections):
    if not selections:
        return document.data
    segments = {s.id: s for s in document.segments}
    with fitz.open(stream=document.data, filetype="pdf") as pdf:
        before = [page.get_text() for page in pdf]
        for finding, correction in selections:
            segment = segments[finding.segment_id]
            groups = {}
            for ref in segment.refs[finding.start : finding.end]:
                if ref is None:
                    continue
                pno, bno, lno, box = ref
                key = (pno, bno, lno)
                if key not in groups:
                    groups[key] = fitz.Rect(box)
                else:
                    groups[key] |= fitz.Rect(box)
            if not groups:
                raise DocumentError("A selected finding has no PDF text coordinates.")
            pno = next(iter(groups))[0]
            rects = [r for r in groups.values() if r.width > 0 and r.height > 0]
            if not rects:
                raise DocumentError("A selected finding has an empty highlight area.")
            page = pdf[pno]
            annotation = page.add_highlight_annot(rects)
            annotation.set_colors(stroke=(1.0, 0.84, 0.24))
            annotation.set_opacity(0.28)
            annotation.set_info(content=correction, title="", subject="")
            annotation.update()
        output = pdf.tobytes(garbage=0, deflate=True)
    with fitz.open(stream=output, filetype="pdf") as check:
        if [page.get_text() for page in check] != before:
            raise DocumentError("Output verification failed: PDF text changed.")
        new_comments = [a.info.get("content") for p in check for a in (p.annots() or [])]
        if any(correction not in new_comments for _, correction in selections):
            raise DocumentError("Output verification failed: missing PDF annotation.")
    return output


def _base_font(span):
    name = span.get("font", "").casefold()
    flags = span.get("flags", 0)
    bold, italic = bool(flags & 16), bool(flags & 2)
    if "courier" in name or "mono" in name:
        family = "co"
    elif "times" in name or "serif" in name:
        family = "ti"
    else:
        family = "he"
    style = ("b" if bold else "") + ("i" if italic else "")
    return (
        {"he": "helv", "ti": "tiro", "co": "cour"}[family]
        if not style
        else {
            ("he", "b"): "hebo",
            ("he", "i"): "heit",
            ("he", "bi"): "hebi",
            ("ti", "b"): "tibo",
            ("ti", "i"): "tiit",
            ("ti", "bi"): "tibi",
            ("co", "b"): "cobo",
            ("co", "i"): "coit",
            ("co", "bi"): "cobi",
        }[(family, style)]
    )


def pdf_correction_targets(document, findings):
    segments = {segment.id: segment for segment in document.segments}
    targets = {}
    with fitz.open(stream=document.data, filetype="pdf") as pdf:
        page_text = [page.get_text("dict") for page in pdf]
        page_images = [
            [fitz.Rect(image["bbox"]) for image in page.get_image_info()] for page in pdf
        ]
        for finding in findings:
            if not finding.suggestions:
                continue
            segment = segments[finding.segment_id]
            refs = segment.refs[finding.start : finding.end]
            groups = {}
            for ref in refs:
                if ref is None:
                    continue
                pno, bno, lno, box = ref
                key = (pno, bno, lno)
                groups[key] = groups.get(key, fitz.Rect(box)) | fitz.Rect(box)
            if len(groups) != 1 or any(ref is None for ref in refs):
                targets[finding.id] = {"supported": False, "reason": "Text spans multiple lines."}
                continue
            (pno, bno, lno), rect = next(iter(groups.items()))
            if any(rect.intersects(image) for image in page_images[pno]):
                targets[finding.id] = {"supported": False, "reason": "Text overlaps page artwork."}
                continue
            spans = [
                span
                for block in page_text[pno]["blocks"]
                for line in block.get("lines", [])
                for span in line["spans"]
                if fitz.Rect(span["bbox"]).intersects(rect)
            ]
            if not spans:
                targets[finding.id] = {"supported": False, "reason": "Text style is unavailable."}
                continue
            span = max(
                spans,
                key=lambda item: (
                    fitz.Rect(item["bbox"]).get_area()
                    and (fitz.Rect(item["bbox"]) & rect).get_area()
                ),
            )
            font = _base_font(span)
            fontsize = span["size"]
            correction = finding.suggestions[0]
            width = fitz.get_text_length(correction, fontname=font, fontsize=fontsize)
            available = rect.width * 1.35
            for offset in range(finding.end, len(segment.text)):
                ref = segment.refs[offset]
                if ref is None or segment.text[offset].isspace():
                    continue
                next_pno, next_bno, next_lno, next_box = ref
                if (next_pno, next_bno, next_lno) == (pno, bno, lno):
                    available = max(rect.width, next_box[0] - rect.x0 - 0.5)
                break
            if width > available:
                fontsize *= available / width
            if fontsize < span["size"] * 0.72:
                targets[finding.id] = {
                    "supported": False,
                    "reason": "Correction does not fit the available line space.",
                }
                continue
            color = span["color"]
            targets[finding.id] = {
                "supported": True,
                "page": pno,
                "rect": tuple(rect),
                "baseline": span["origin"][1],
                "font": font,
                "fontsize": fontsize,
                "color": ((color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255),
                "line": (pno, bno, lno),
            }
    return targets


def apply_pdf_changes(document, findings, choices):
    if not choices:
        return document.data
    by_id = {finding.id: finding for finding in findings}
    targets = pdf_correction_targets(document, findings)
    changes = []
    for finding_id, correction in choices.items():
        finding = by_id.get(finding_id)
        target = targets.get(finding_id)
        if finding is None or correction not in finding.suggestions:
            raise DocumentError("Choose one of the available corrections.")
        if not target or not target["supported"]:
            raise DocumentError(
                target["reason"] if target else "This correction cannot be placed safely."
            )
        changes.append((finding, correction, target))
    for index, (finding, _, target) in enumerate(changes):
        rect = fitz.Rect(target["rect"])
        for other_finding, _, other_target in changes[index + 1 :]:
            if target["page"] == other_target["page"] and rect.intersects(
                fitz.Rect(other_target["rect"])
            ):
                raise DocumentError("Selected corrections overlap. Turn one of them off.")
    with fitz.open(stream=document.data, filetype="pdf") as pdf:
        for _, _, target in changes:
            pdf[target["page"]].add_redact_annot(
                fitz.Rect(target["rect"]), fill=None, cross_out=False
            )
        for page_number in {target["page"] for _, _, target in changes}:
            pdf[page_number].apply_redactions(images=0, graphics=0)
        for _, correction, target in changes:
            pdf[target["page"]].insert_text(
                (target["rect"][0], target["baseline"]),
                correction,
                fontname=target["font"],
                fontsize=target["fontsize"],
                color=target["color"],
                overlay=True,
            )
        output = pdf.tobytes(garbage=0, deflate=True)
    with fitz.open(stream=output, filetype="pdf") as checked:
        for _, correction, target in changes:
            rect = fitz.Rect(target["rect"])
            if not any(
                found.intersects(rect) for found in checked[target["page"]].search_for(correction)
            ):
                raise DocumentError("Output verification failed: corrected PDF text is missing.")
    return output
