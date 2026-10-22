# Spellcheck Tool

Finnish and English proofreading for PDF and Word documents. Reviewed copies preserve the original wording with soft highlights and comments containing **only the proposed correction**. Word documents also offer native tracked changes for accepting or rejecting edits in Word.

Runs locally on Windows 10/11 x64. No administrator rights, subscription, account, API key or installed Python/Java required. Setup downloads free language resources once; document checking then works offline.

See the [validation record](docs/validation.md) for tested platforms and workflows.

## Start on Windows

**Portable package — recommended**

1. Open [Windows builds](https://github.com/OscarLegoupil/spellcheck-tool/actions/workflows/windows.yml), select the latest successful build, and download **Spellcheck-Tool-Windows** under Artifacts. GitHub requires you to be signed in to download build artifacts.
2. Extract the downloaded archive and the application ZIP inside it into a writable folder, such as Documents. Extract everything; do not run from inside the ZIP.
3. Double-click **Start.cmd**. A simple local Streamlit page opens in your browser. Keep the window open while using it.

The portable package already includes the engines and runtimes. It needs no setup download on the work computer. Corporate application controls can still block portable executables; ask IT to allow the application if that happens.

**From source**

Download this repository with **Code → Download ZIP**. Before extracting, right-click the downloaded ZIP, open **Properties**, select **Unblock** if shown, and click **Apply**. Extract it and run **Setup.cmd** once. Then run **Start.cmd** to open the local Streamlit page. Setup uses the current user's writable folder and does not change PowerShell policy, PATH, registry settings or system software. If company policy blocks unsigned PowerShell scripts, use the portable package or ask IT.

Allow roughly 1 GB of free disk space for setup and extraction. Initial startup of the English engine can take a little time. Downloads are pinned and SHA-256 checked; a changed upstream download fails explicitly.

## Review a document

1. Upload a searchable PDF or `.docx` and choose Finnish, English, or mixed language.
2. Click **Check document**. **Download reviewed PDF/DOCX** saves the annotated copy; the uploaded original is never overwritten.
3. For PDFs, use the page-by-page preview below the download button. Click a highlighted finding to toggle its correction in the preview, then download the corrected PDF when ready.
4. For Word documents, choose **Download Word with tracked changes** to get a separate `_tracked.docx` copy. Open it in Word, select **Review → All Markup**, and use **Accept** or **Reject** to review the proposed edits. Save when finished. The commented copy remains available above.

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
| Streamlit workflow | One searchable PDF or `.docx` at a time; download the annotated copy. PDFs also have a visual correction preview with one-click toggles and a separate corrected-PDF download. Word documents offer a separate download with native tracked changes. The command-line workflow retains profile-based checking and JSON reports. |

There are no cloud checks or paid LanguageTool features. These engines find many spelling and rule-based grammar errors; they do not verify facts, meaning or every possible language mistake. Finnish grammar coverage is narrower than English. Suggestions can be wrong; PDF text changes are made only when you click them in the preview.

## Document support

- **PDF → annotated PDF:** supported in Streamlit and the command line. Text coordinates identify exact occurrences; words are not located with a global search. Existing annotations, page contents and page geometry are retained.
- **PDF → corrected PDF:** single-line vector text can be toggled in the visual preview. The original glyphs are removed without painting over the page background, and replacement text uses the closest available font style. Corrections over artwork, multi-line text, and changes that do not fit safely remain available in the annotated copy only; exact font matching is not guaranteed for embedded/subset fonts.
- **DOCX → annotated DOCX:** supported in Streamlit and the command line. Body paragraphs and tables, including words split across formatting runs. Run formatting and unrelated package parts are retained. Existing comments remain intact; the commented copy preserves the source text.
- **DOCX → tracked DOCX:** available in Streamlit. Each default selected suggestion becomes a native Word deletion/insertion attributed to Spellcheck Tool. Accepting applies the replacement; rejecting restores the original text and its formatting. Replacement text inherits the first affected run's formatting. Existing comments, revisions and unrelated package parts are retained; paragraphs already containing comments or revisions are not edited.
- **Coverage notices:** Word paragraphs containing revisions, fields, hyperlinks, existing comments, content controls or embedded objects are conservatively skipped. Headers, footers, footnotes and endnotes are retained but not checked. Notices are shown in the app and report. Text boxes and rotated PDF text are not checked.
- **Scanned PDFs:** require an existing searchable OCR layer. Image-only PDFs are rejected with a clear message; the application does not install or perform OCR.
- **Other formats:** save legacy `.doc` as `.docx` in Word first. PDF/Word conversion is not included; outputs keep the input format. To obtain PDF from reviewed Word, use Word's export/print options, checking how your viewer handles comments.
- Password-protected PDFs and signed review files are rejected. Maximum 30 MB per document, eight reviews per session and one million extracted characters per document.

See [troubleshooting](docs/troubleshooting.md), [design and development](docs/development.md), and the [sample documents](examples/).

## Privacy

Documents are processed on your computer. The Windows launcher binds the Streamlit app to `127.0.0.1`; the English engine also runs locally. No analytics, external fonts or cloud checking requests are used. Uploaded PDFs and reviewed copies stay in the app's memory for the active session and are not saved to disk by the app. Closing the app ends the session. Downloads are files you choose to retain.

## Development

```bash
python -m venv .venv
# Activate the virtual environment for your shell, then:
python -m pip install -e '.[dev]'
python scripts/setup_runtime.py
python -m spellcheck_tool doctor
streamlit run src/spellcheck_tool/streamlit_app.py --server.address 127.0.0.1
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
