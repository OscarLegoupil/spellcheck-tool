# Design and development

The pipeline has four stages: extract text and source positions, run local language/rule checks, combine/filter findings, and annotate a copy. Analysis normalization never changes the source wording.

`pdf.py` maps normalized characters to page/block/line bounding boxes. It creates standard PDF highlight annotations and checks extracted text after export. `word.py` reads the OOXML package directly, splits plain text runs at comment boundaries while copying run properties, and updates only the document/comment relationships and contents. Export validates wording preservation. The tests also check original PDF content streams, rendered appearance within anti-aliasing tolerance, and untouched Word package parts.

`engines.py` runs Voikko through its native wrapper and a private LanguageTool Java process. LanguageTool uses UTF-16 offsets; `text.py` translates these to Python character indices, including non-BMP characters. Ligatures and soft hyphens retain source mappings. Zero-width and deletion findings receive visible anchors containing the proposed final text.

`pipeline.py` checks long sections in bounded chunks, aggregates offsets, applies glossary/rule filters, merges duplicate ranges, and defaults to a non-overlapping selection. Chunk boundaries can reduce grammar context in unusually long paragraphs. Mixed-language routing operates per text block, not per word; fixed language gives more predictable results. Findings without a non-empty replacement stay in review data but are not exported.

`app.py` serves a local static browser UI and queues one review at a time. A random bearer token is passed through the URL fragment and retained in session storage. The server binds to loopback, validates Host, and does not enable CORS. The application is intended for one local desktop user, not deployment as a public website.

## Tests

```bash
python -m ruff check src tests scripts
python -m pytest -q
```

Real engine tests additionally require the prepared runtime and `SPELLCHECK_INTEGRATION=1`. The Windows workflow installs the private embedded Python, private JRE, native Voikko and locked LanguageTool dependencies, runs diagnostics and real engine/document tests, then produces the portable ZIP. No office installation is required to annotate DOCX.

## Runtime locks

- `requirements-windows.lock`: Python packages and hashes, compiled for Windows/Python 3.12.
- `src/spellcheck_tool/resources/downloads.lock.json`: embedded CPython, pip wheel, JRE, Voikko DLL and Finnish dictionary.
- `src/spellcheck_tool/resources/english-runtime.lock.json`: exact Maven artifacts and SHA-256 values.
- `scripts/languagetool-pom.xml`: Maven dependency inputs. Spanish, Catalan and Portuguese resources are needed by LanguageTool's shared language detection classes even though the application exposes only Finnish and English.

To update the Maven bundle, resolve runtime dependencies using the checked-in POM into a clean Maven repository-layout directory, then review every artifact/version/hash before regenerating the lock. Do not silently accept changed dictionary or binary downloads. Re-run both language engines and Windows tests for any runtime update.

## Packaging

Run `scripts/setup-windows.ps1`, then `python scripts/build_portable.py` on Windows. The package includes application source, tests, examples, dependency metadata and private runtimes. Download caches, documents uploaded by users, logs and development environments are excluded. Review third-party license/source requirements before redistributing modified packages.
