# Validation record

Initial validation: 2026-10-13.

- Linux/Python 3.12: **23 tests passed**, including real LanguageTool 6.6 and Voikko engine checks.
- Real Finnish and English examples exported successfully as PDF and DOCX.
- Chromium browser: English DOCX upload, review and annotated download; review removal; Finnish PDF upload, review and annotated download. No JavaScript page errors observed.
- Annotated PDF and DOCX samples rendered and inspected for highlight placement and readability.
- Preservation tests cover PDF page content streams, text and rendering; split Word runs, bold formatting, tables, original package parts and existing comments; ligatures, soft hyphens and emoji offsets; overlapping selections and invalid corrections.
- Ruff checks passed for source, tests and scripts.

Windows validation: 2026-10-14, Windows 11 Home x64 (build 26200).

- Source setup completed with the pinned private CPython 3.12.10, Temurin Java 17, LanguageTool 6.6 and native Voikko runtimes. Both engine diagnostics passed. The downloaded setup script needed Windows' Unblock action; execution policy and system software were not changed.
- Python 3.12.14 development environment: **23 tests passed**, including real engine checks and all four sample document exports. Ruff checks passed. The test client emitted one dependency deprecation warning for AnyIO's BlockingPortal alias.
- Chrome 155 with the private Python application server: all four sample documents uploaded, reviewed and downloaded successfully. English DOCX/PDF produced 8/7 annotations; Finnish DOCX/PDF produced 7/6 annotations. Exported comments matched the selected corrections, original text stayed intact, and original PDF content streams were preserved.
- Browser checks covered finding filters, selection changes, clearing selection, JSON report export, profile save/load, session persistence after reload and review removal. DOCX downloads with no corrections selected were byte-identical to their inputs. No JavaScript page errors or external browser requests were observed.
- Review screens and a rendered annotated English PDF were visually inspected.
- The portable ZIP passed its integrity check. After extraction into a separate directory containing a space, its private interpreter successfully ran both engine diagnostics from outside the application folder without setup downloads.

The GitHub Windows workflow repeats setup, tests and portable packaging on each push to `main`. Microsoft Word and Acrobat hover/comment behaviour were not tested on a Windows desktop; the standard annotation/comment structures are covered by automated tests.

Correction download validation: 2026-10-19, Windows.

- **34 tests passed**, including real Finnish/English engine checks and tracked DOCX exports. Ruff checks passed.
- Chromium with the private Streamlit runtime: English and Finnish Word documents downloaded with 8 and 6 proposed corrections respectively. Their commented downloads remained available. No browser JavaScript errors were observed.
- Microsoft Word 16.0 opened the actual tracked downloads through COM automation. Accepting all revisions produced the expected corrected text; rejecting all revisions restored the original text. A separate fixture covered a correction spanning bold and plain runs. These were document automation checks, not manual ribbon-click tests.
- Tests cover individual selected occurrences, adjacent edits, tabs and line breaks, ligatures and soft hyphens, existing comments and revisions, and preservation of every package part other than `word/document.xml`.
- PDF browser downloads reflected selecting two corrections and undoing one. Streamlit regression tests also cover selections across pages and prevent a failed correction from offering the original PDF as a corrected download or corrupting the last valid preview.

Coverage limits and viewer-dependent behaviour are documented in the README. This record does not claim that every document structure or every language error is supported.
