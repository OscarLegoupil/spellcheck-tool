from io import BytesIO
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest
from test_annotations import finding, make_word

from spellcheck_tool import pipeline
from spellcheck_tool.word import NS, package, parse


@pytest.mark.parametrize("has_findings", [False, True])
def test_word_review_offers_native_tracked_download(monkeypatch, has_findings):
    uploaded = BytesIO(make_word())
    uploaded.name = "sample.docx"
    monkeypatch.setattr(st, "file_uploader", lambda *args, **kwargs: uploaded)
    monkeypatch.setattr(st, "form_submit_button", lambda *args, **kwargs: True)

    def review(document, options, engines):
        segment = next(s for s in document.segments if "recieve" in s.text)
        return {"warnings": []}, [finding(segment, "recieve", "receive")] if has_findings else []

    monkeypatch.setattr(pipeline, "review", review)
    downloads = {}
    download_button = st.download_button

    def capture_download(label, **kwargs):
        downloads[label] = kwargs
        return download_button(label, **kwargs)

    monkeypatch.setattr(st, "download_button", capture_download)
    app = AppTest.from_file(
        Path(__file__).parents[1] / "src" / "spellcheck_tool" / "streamlit_app.py",
        default_timeout=15,
    ).run()
    assert not app.exception
    assert not app.error
    assert "Download reviewed DOCX" in downloads
    tracked = downloads.get("Download Word with tracked changes")
    if not has_findings:
        assert tracked is None
        return
    assert tracked["file_name"] == "sample_tracked.docx"
    assert tracked["on_click"] == "ignore"
    root = parse(package(tracked["data"])["word/document.xml"])
    assert root.xpath(".//w:ins//w:t/text()", namespaces=NS) == ["receive"]
    assert "".join(root.xpath(".//w:del//w:delText/text()", namespaces=NS)) == "recieve"
    comments = package(downloads["Download reviewed DOCX"]["data"])
    assert "word/comments.xml" in comments
    assert not parse(comments["word/document.xml"]).xpath(".//w:ins | .//w:del", namespaces=NS)
