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
