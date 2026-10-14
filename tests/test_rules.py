from spellcheck_tool.engines import detect_language
from spellcheck_tool.models import Finding, Options, Segment
from spellcheck_tool.pipeline import chunks, combine
from spellcheck_tool.rules import check_rules
from spellcheck_tool.text import anchor_replacement, normalize, utf16_to_index


def test_utf16_offsets_after_non_bmp_character():
    text = "🚆 A speling mistake"
    assert utf16_to_index(text, 5) == 4
    assert text[utf16_to_index(text, 5) : utf16_to_index(text, 12)] == "speling"


def test_normalization_mapping():
    text = "ﬁne\u00a0mis\u00adspeling"
    result, refs = normalize(text, list(range(len(text))))
    assert result == "fine misspeling"
    assert refs[:2] == [0, 0]
    assert refs[result.index("s", 6)] == 6


def test_repeated_word_and_spacing():
    s = Segment("x", "The the item weighs 25kg. Two  spaces.", "test")
    fs = check_rules(s, Options())
    assert any(f.original == "The the" and f.suggestions == ["The"] for f in fs)
    assert any(f.original == "25kg" and f.suggestions == ["25 kg"] for f in fs)
    assert any("Two spaces." in f.suggestions for f in fs)


def test_insertion_has_visible_anchor():
    start, end, values = anchor_replacement("Hello world", 5, 5, [","])
    assert "Hello world"[start:end] == "Hello"
    assert values == ["Hello,"]


def test_deduplication_preserves_alternatives_and_avoids_overlap():
    s = Segment("x", "The the speling", "test")
    fs = [
        Finding("x", 0, 7, "The the", ["The"], "A", "grammar", "one"),
        Finding("x", 0, 7, "The the", ["the"], "B", "grammar", "two"),
        Finding("x", 4, 7, "the", ["a"], "C", "grammar", "one"),
    ]
    result = combine(fs, [s], Options())
    assert len(result) == 2
    assert result[0].suggestions == ["The", "the"]
    assert result[0].selected and not result[1].selected


def test_glossary_protects_spelling_not_grammar():
    s = Segment("x", "Valmet", "test")
    fs = [Finding("x", 0, 6, "Valmet", ["Velmet"], "A", "spelling", "test")]
    assert combine(fs, [s], Options(glossary=["VALMET"])) == []


def test_urls_and_codes_not_spellchecked():
    s = Segment("x", "https://exmaple.com XJ42", "test")
    f = Finding("x", 8, 15, "exmaple", ["example"], "A", "spelling", "test")
    assert combine([f], [s], Options()) == []


def test_chunks_reassemble_exactly():
    s = Segment("x", "This is a sentence. " * 1000, "test")
    parts = list(chunks(s, 100))
    assert "".join(p.text for _, p in parts) == s.text
    assert all(len(p.text) <= 100 for _, p in parts)


def test_language_routing():
    assert detect_language("Tämä on raportti ja se sisältää tiedot.")[0] == "fi"
    assert detect_language("This is the report and it contains the results.")[0] == "en"


def test_code_filter_keeps_unit_spacing_corrections():
    s = Segment("x", "The item weighs 25kg.", "test")
    fs = combine(check_rules(s, Options()), [s], Options())
    assert any(f.suggestions == ["25 kg"] for f in fs)
