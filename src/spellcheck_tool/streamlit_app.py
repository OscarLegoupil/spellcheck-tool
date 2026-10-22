import base64
from hashlib import sha256
from pathlib import Path

import pymupdf as fitz
import streamlit as st
import streamlit.components.v1 as components

from spellcheck_tool.engines import Engines
from spellcheck_tool.models import DocumentError, EngineError, Options
from spellcheck_tool.pdf import apply_pdf_changes, pdf_correction_targets
from spellcheck_tool.pipeline import export, load_document, review

PDF_PREVIEW = components.declare_component(
    "spellcheck_pdf_preview",
    path=str(Path(__file__).parent / "static" / "pdf_preview"),
)


@st.cache_resource
def get_engines():
    return Engines()


@st.cache_data(show_spinner=False, max_entries=32)
def render_pdf_page(pdf_data, page_number):
    with fitz.open(stream=pdf_data, filetype="pdf") as pdf:
        page = pdf[page_number]
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
        return base64.b64encode(pixmap.tobytes("png")).decode("ascii"), page.rect.width, page.rect.height


st.set_page_config(page_title="Spellcheck Tool", layout="centered")
st.title("Document Spellcheck")
st.write(
    "Upload a searchable PDF or Word document to check it locally. Download a reviewed copy "
    "with suggested corrections as comments, or accept and reject Word edits with Track Changes."
)

with st.form("document-review"):
    uploaded = st.file_uploader("PDF or Word document", type=["pdf", "docx"])
    language_label = st.selectbox("Language", ["Mixed", "Finnish", "English"])
    english_label = st.selectbox("English variety", ["British English", "American English"])
    submitted = st.form_submit_button("Check document", type="primary")

language = {"Mixed": "mixed", "Finnish": "fi", "English": "en"}[language_label]
english = "en-GB" if english_label == "British English" else "en-US"

if submitted and uploaded:
    data = uploaded.getvalue()
    if len(data) > 30 * 1024 * 1024:
        st.error("Please use a document smaller than 30 MB.")
    else:
        try:
            with st.spinner("Checking your document..."):
                document = load_document(uploaded.name, data)
                options = Options(language=language, english=english)
                report, findings = review(document, options, get_engines())
                choices = [
                    {"id": finding.id, "correction": finding.suggestions[0]}
                    for finding in findings
                    if finding.selected
                ]
                output = export(document, findings, choices)
            st.session_state.reviewed_document = {
                "key": (sha256(data).hexdigest(), language, english),
                "bytes": output,
                "findings": len(choices),
                "warnings": report["warnings"],
                "name": f"{Path(uploaded.name).stem}_reviewed{Path(uploaded.name).suffix.lower()}",
                "original": data,
                "document": document,
                "issues": findings,
            }
        except (DocumentError, EngineError) as exc:
            st.error(str(exc))
        except Exception:
            st.error("The document could not be checked. Try a smaller or searchable file.")

if uploaded:
    current_key = (sha256(uploaded.getvalue()).hexdigest(), language, english)
    result = st.session_state.get("reviewed_document")
    if result and result["key"] == current_key:
        if result["findings"]:
            st.success(f"Found {result['findings']} suggestions.")
        else:
            st.success("No suggestions found.")
        for warning in result["warnings"]:
            if "uncertain language" not in warning.casefold():
                st.caption(warning)
        st.download_button(
            f"Download reviewed {Path(result['name']).suffix[1:].upper()}",
            data=result["bytes"],
            file_name=result["name"],
            mime=(
                "application/pdf"
                if Path(result["name"]).suffix.lower() == ".pdf"
                else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            type="primary",
        )
        if result["document"].kind == "docx" and result["findings"]:
            st.subheader("Review corrections in Word")
            try:
                if "tracked_bytes" not in result:
                    choices = [
                        {"id": finding.id, "correction": finding.suggestions[0]}
                        for finding in result["issues"]
                        if finding.selected and finding.suggestions
                    ]
                    result["tracked_bytes"] = export(
                        result["document"], result["issues"], choices, track_changes=True
                    )
                    st.session_state.reviewed_document = result
                st.download_button(
                    "Download Word with tracked changes",
                    data=result["tracked_bytes"],
                    file_name=f"{Path(uploaded.name).stem}_tracked.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    type="primary",
                    on_click="ignore",
                )
                st.caption(
                    "Open this copy in Word. On the Review tab, choose All Markup to see the edits, "
                    "then use Accept or Reject to review each correction. Save when finished."
                )
            except DocumentError as exc:
                st.error(str(exc))
        if result["document"].kind == "pdf":
            st.subheader("PDF correction preview")
            document = result["document"]
            issues = result["issues"]
            targets = pdf_correction_targets(document, issues)
            state_key = f"pdf-preview-{current_key[0][:16]}"
            state = st.session_state.get(state_key) or {"page": 0, "selected": []}
            page_number = max(0, min(int(state.get("page", 0)), document.pages - 1))
            supported = {
                finding.id: finding
                for finding in issues
                if finding.selected
                and finding.suggestions
                and targets.get(finding.id, {}).get("supported")
            }
            selected_ids = set(state.get("selected", [])) & set(supported)
            choices = {
                finding_id: supported[finding_id].suggestions[0]
                for finding_id in selected_ids
            }
            signature = tuple(sorted(choices.items()))
            if result.get("preview_signature") != signature:
                try:
                    result["preview_bytes"] = apply_pdf_changes(document, issues, choices)
                    result["preview_signature"] = signature
                    st.session_state.reviewed_document = result
                except DocumentError as exc:
                    st.error(str(exc))
                    st.caption("Undo the last change before downloading the corrected PDF.")
            preview_data = result.get("preview_bytes", result["original"])
            image, page_width, page_height = render_pdf_page(preview_data, page_number)
            page_findings = []
            unsupported_count = 0
            for finding in issues:
                if not finding.suggestions:
                    continue
                target = targets.get(finding.id, {})
                if not target.get("supported"):
                    unsupported_count += 1
                    continue
                if target["page"] != page_number:
                    continue
                enabled = finding.id in supported
                page_findings.append(
                    {
                        "id": finding.id,
                        "original": finding.original,
                        "correction": finding.suggestions[0],
                        "rect": list(target["rect"]),
                        "enabled": enabled,
                        "reason": "Overlaps another finding." if not enabled else "",
                    }
                )
            PDF_PREVIEW(
                image=image,
                page=page_number,
                pageCount=document.pages,
                pageWidth=page_width,
                pageHeight=page_height,
                findings=page_findings,
                default={"page": page_number, "selected": sorted(selected_ids)},
                key=state_key,
            )
            if unsupported_count:
                st.caption(
                    f"{unsupported_count} suggestion(s) cannot be applied safely in the PDF preview; "
                    "they remain available in the reviewed copy above."
                )
            if selected_ids and result.get("preview_signature") == signature:
                st.download_button(
                    "Download corrected PDF",
                    data=preview_data,
                    file_name=f"{Path(uploaded.name).stem}_corrected.pdf",
                    mime="application/pdf",
                    type="primary",
                    on_click="ignore",
                    key=f"download-corrected-{current_key[0][:16]}",
                )
                st.caption("Print the downloaded PDF from your PDF viewer.")
