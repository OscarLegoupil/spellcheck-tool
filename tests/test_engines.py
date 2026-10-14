import os
from pathlib import Path

import pytest

from spellcheck_tool.engines import Engines
from spellcheck_tool.models import Options, Segment
from spellcheck_tool.pipeline import export, load_document, review

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("SPELLCHECK_INTEGRATION") != "1",
        reason="Set SPELLCHECK_INTEGRATION=1 with runtimes installed",
    ),
]


def test_real_engines_and_example_exports(tmp_path):
    engines = Engines()
    try:
        fi = engines.get_finnish()
        assert fi.spell("kirjoitusvirhe")
        assert not fi.spell("huommenna")
        assert "huomenna" in fi.suggest("huommenna")
        fs = engines.check(
            Segment("x", "This is an test with a speling mistake.", "test", "en"), Options()
        )
        assert any("spelling" in f.suggestions for f in fs)
        for language, name in [("fi", "finnish"), ("en", "english")]:
            for suffix in ("pdf", "docx"):
                path = Path(__file__).parents[1] / "examples" / f"{name}.{suffix}"
                doc = load_document(path.name, path.read_bytes())
                result, findings = review(doc, Options(language=language), engines)
                selected = [
                    {"id": f.id, "correction": f.suggestions[0]} for f in findings if f.selected
                ]
                assert len(selected) >= 3, result
                output = export(doc, findings, selected)
                (tmp_path / f"{name}_reviewed.{suffix}").write_bytes(output)
    finally:
        engines.close()
