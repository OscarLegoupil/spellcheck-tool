from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pymupdf as fitz
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from test_annotations import finding

from spellcheck_tool import pdf
from spellcheck_tool.models import DocumentError
from spellcheck_tool.pipeline import load_document


@pytest.fixture
def preview_app(monkeypatch):
    with fitz.open() as source:
        for _ in range(2):
            source.new_page().insert_text((50, 80), "We recieve the report.", fontsize=13)
        original = source.tobytes()
    document = load_document("sample.pdf", original)
    issues = [finding(segment, "recieve", "receive") for segment in document.segments]
    uploaded = BytesIO(original)
    uploaded.name = document.name
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)

    downloads = {}
    download_button = st.download_button

    def capture_download(label, *, data, **kwargs):
        downloads[label] = data
        return download_button(label, data=data, **kwargs)

    monkeypatch.setattr(st, "download_button", capture_download)
    app = AppTest.from_file(
        Path(__file__).parents[1] / "src" / "spellcheck_tool" / "streamlit_app.py",
        default_timeout=15,
    )
    digest = sha256(original).hexdigest()
    app.session_state.reviewed_document = {
        "key": (digest, "mixed", "en-GB"),
        "bytes": original,
        "findings": len(issues),
        "warnings": [],
        "name": "sample_reviewed.pdf",
        "original": original,
        "document": document,
        "issues": issues,
    }

    def render(selected, page=0):
        downloads.clear()
        app.session_state[f"pdf-preview-{digest[:16]}"] = {
            "page": page,
            "selected": [issue.id for issue in selected],
        }
        app.run()
        assert not app.exception
        return downloads.get("Download corrected PDF")

    return app, issues, render


def assert_corrections(data, corrected_pages):
    with fitz.open(stream=data, filetype="pdf") as document:
        for page_number, page in enumerate(document):
            assert bool(page.search_for("receive")) == (page_number in corrected_pages)
            assert bool(page.search_for("recieve")) == (page_number not in corrected_pages)


def test_corrected_download_tracks_selections_across_pages_and_undo(preview_app):
    app, issues, render = preview_app
    assert render([]) is None
    for selected, page, expected in [
        ([issues[0]], 0, {0}),
        (issues, 1, {0, 1}),
        ([issues[1]], 0, {1}),
    ]:
        data = render(selected, page)
        assert data == app.session_state.reviewed_document["preview_bytes"]
        assert_corrections(data, expected)
    assert render([]) is None
    assert app.session_state.reviewed_document["preview_bytes"] == (
        app.session_state.reviewed_document["original"]
    )


@pytest.mark.parametrize("undo_failed_change", [False, True])
def test_failed_correction_never_downloads_original_as_corrected(
    preview_app, monkeypatch, undo_failed_change
):
    app, issues, render = preview_app
    apply_changes = pdf.apply_pdf_changes

    def fail_second_change(document, findings, choices):
        if issues[1].id in choices:
            raise DocumentError("Output verification failed: corrected PDF text is missing.")
        return apply_changes(document, findings, choices)

    monkeypatch.setattr(pdf, "apply_pdf_changes", fail_second_change)
    good_pdf = render([issues[0]])
    failed_download = render(issues)
    assert app.error
    if undo_failed_change:
        recovered_pdf = render([issues[0]])
        assert not app.error
        assert_corrections(recovered_pdf, {0})
        assert recovered_pdf == good_pdf
    else:
        assert failed_download is None
