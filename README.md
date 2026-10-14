# Spellcheck Tool

Finnish and English proofreading for PDF and Word documents. Original wording stays intact; possible mistakes receive soft highlights and comments containing **only the proposed correction**.

Runs locally on Windows 10/11 x64. No administrator rights, subscription, account, API key or installed Python/Java required. Setup downloads free language resources once; document checking then works offline.

See the [validation record](docs/validation.md) for tested platforms and workflows.

## Start on Windows

**Portable package — recommended**

1. Open [Windows builds](https://github.com/OscarLegoupil/spellcheck-tool/actions/workflows/windows.yml), select the latest successful build, and download **Spellcheck-Tool-Windows** under Artifacts. GitHub requires you to be signed in to download build artifacts.
2. Extract the downloaded archive and the application ZIP inside it into a writable folder, such as Documents. Extract everything; do not run from inside the ZIP.
3. Double-click **Start.cmd**. Keep its window open while using the application. Your browser opens automatically.

The portable package already includes the engines and runtimes. It needs no setup download on the work computer. Corporate application controls can still block portable executables; ask IT to allow the application if that happens.

**From source**

Download this repository with **Code → Download ZIP**. Before extracting, right-click the downloaded ZIP, open **Properties**, select **Unblock** if shown, and click **Apply**. Extract it and run **Setup.cmd** once. Then run **Start.cmd**. Setup uses the current user's writable folder and does not change PowerShell policy, PATH, registry settings or system software. If company policy blocks unsigned PowerShell scripts, use the portable package or ask IT.

Allow roughly 1 GB of free disk space for setup and extraction. Initial startup of the English engine can take a little time. Downloads are pinned and SHA-256 checked; a changed upstream download fails explicitly.

## Review a document

1. Choose or drop one or more `.pdf` / `.docx` documents.
2. Select Finnish, English, or mixed language. For a single-language document, select that language explicitly. Choose British or American English.
3. Click **Check documents**. Review the selected findings or download immediately with the default non-overlapping selection.
4. Download the annotated copy. Choose alternatives or exclude findings whenever needed. The original file is never overwritten by the browser workflow.

A highlight on `recieve` has the comment `receive`. No explanation, rule name or “Suggested correction” prefix is placed in the document. Blank corrections are anchored to nearby text so deletion and insertion suggestions remain readable. The review screen contains the explanations and alternative suggestions.

PDF comments appear on hover or click **when supported by the PDF viewer**. Adobe Acrobat Reader is a suitable review client; some browser PDF viewers hide comments. Word comments use Word's normal comment interface, with pale shading on the affected text. Viewer controls, authorship labels or comment bubbles are controlled by the viewer.

## Included checks

| Area | Implementation |
| --- | --- |
| Finnish spelling and inflection | Voikko with the Finnish morphological dictionary; compound words and inflections are handled by the language engine |
| Finnish grammar | Voikko's available deterministic grammar checks |
| English spelling and grammar | Local LanguageTool 6.6, British or American English |
| Thorough review | LanguageTool's picky mode plus typography checks |
| Typography | Repeated words, extra spaces, punctuation spacing and selected number/unit spacing |
| House style | Accepted words, preferred terminology, ignored rules and reusable JSON profiles |
| Mixed documents | Deterministic routing by paragraph/text block, with notices for uncertain decisions |
| Review controls | Batch files, category filters, alternative corrections, exclusion, JSON report and overlap checks |

There are no cloud checks or paid LanguageTool features. These engines find many spelling and rule-based grammar errors; they do not verify facts, meaning or every possible language mistake. Finnish grammar coverage is narrower than English. Suggestions can be wrong; nothing is automatically replaced.

## Document support

- **PDF → annotated PDF:** text coordinates identify exact occurrences; words are not located with a global search. Existing annotations, page contents and page geometry are retained. Multi-line findings receive one comment across their highlight areas.
- **DOCX → annotated DOCX:** body paragraphs and tables, including words split across formatting runs. Run formatting and unrelated package parts are retained. Existing comments remain intact.
- **Coverage notices:** Word paragraphs containing revisions, fields, hyperlinks, existing comments, content controls or embedded objects are conservatively skipped. Headers, footers, footnotes and endnotes are retained but not checked. Notices are shown in the app and report. Text boxes and rotated PDF text are not checked.
- **Scanned PDFs:** require an existing searchable OCR layer. Image-only PDFs are rejected with a clear message; the application does not install or perform OCR.
- **Other formats:** save legacy `.doc` as `.docx` in Word first. PDF/Word conversion is not included; outputs keep the input format. To obtain PDF from reviewed Word, use Word's export/print options, checking how your viewer handles comments.
- Password-protected PDFs and signed review files are rejected. Maximum 30 MB per document, eight reviews per session and one million extracted characters per document.

See [troubleshooting](docs/troubleshooting.md), [design and development](docs/development.md), and the [sample documents](examples/).

## Privacy

Documents are processed on your computer. The browser talks only to a loopback service with a random session token, and the English engine runs on loopback too. No analytics, external fonts or checking requests are used. Uploaded reviews are held in memory; the web framework may spool uploads to the operating system's temporary directory during receipt and closes them after reading. Finished reviews expire after two hours on the next application request, or can be removed immediately. Closing the application ends the session. Downloads and exported reports are files you choose to retain; reports include document text.

## Development

```bash
python -m venv .venv
# Activate the virtual environment for your shell, then:
python -m pip install -e '.[dev]'
python scripts/setup_runtime.py
python -m spellcheck_tool doctor
python -m spellcheck_tool serve
```

On Linux/macOS, install compatible native **libvoikko** and **Java 17+** separately. On Windows, `Setup.cmd` installs private copies. `SPELLCHECK_VOIKKO_LIBRARY` can point to a native library directory; `SPELLCHECK_RUNTIME` can point to a prepared runtime directory.

```bash
python -m pytest -q                        # structural and application tests
# Set SPELLCHECK_INTEGRATION=1 to include real engine checks.
python -m spellcheck_tool check report.pdf --language fi
python -m spellcheck_tool check report.docx --language en --english en-GB
```

The command-line workflow selects the first available correction for each default selected finding and writes a separate reviewed file and JSON report. Use the browser to choose alternatives.

## License

The repository's own code is MIT licensed. Dependencies keep their own licenses, including **PyMuPDF's AGPL** and Voikko's GPL/LGPL components. The bundled application is not an MIT-only distribution. See [third-party components](THIRD_PARTY.md) for licenses and source locations.
