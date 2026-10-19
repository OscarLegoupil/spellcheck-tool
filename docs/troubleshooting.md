# Troubleshooting

| Symptom | Action |
| --- | --- |
| Start says to run Setup | Use the complete portable package, or run Setup.cmd from an extracted source checkout. |
| Downloaded setup script is not digitally signed | For a ZIP downloaded from this repository, right-click the ZIP, open Properties, select Unblock, apply, and extract again. For an existing extracted copy, open `scripts/setup-windows.ps1` Properties and select Unblock. Retry Setup.cmd. |
| PowerShell script blocked by company policy | Use the ready-built portable package or ask IT. Setup does not change execution policy. |
| Executable blocked by company policy | Ask IT to approve the application. Administrator-free does not override application controls. |
| Download/checksum failure | Retry after checking your network or proxy. A checksum mismatch means an upstream file changed; do not remove the checksum check. |
| Browser did not open | Open the local URL printed in the launcher window. Keep the window open while using the app. |
| English engine failed | Inspect `.runtime/logs/english-engine.log`, then run the diagnostic command below. Check available memory and private Java files. |
| Finnish engine failed | Verify `.runtime/voikko/libvoikko-1.dll` and `.runtime/voikko/5/mor-standard/mor.vfst`. Run Setup again if missing. |
| Nothing visible when hovering | Try clicking the highlight or opening the PDF in Acrobat Reader with comments enabled. Hover is viewer-dependent. |
| Word has few findings | Read coverage notices. Paragraphs with complex structures are skipped to protect the document. Try a plain review copy. |
| Too many false positives | Choose a fixed language, add names to Accepted words, change dialect, or use Standard depth. Save a profile for reuse. |
| Overlap error at download | Two selected findings cover the same passage. Deselect one. The default selection already avoids overlaps. |
| An issue has no correction | It remains review-only in the app/report. No empty or explanatory document comment is generated. |
| Long scan has no results | OCR the document first with your organisation's approved software, then submit the searchable PDF. |

Diagnostics from the extracted application's folder:

```bat
.runtime\python\python.exe -m spellcheck_tool doctor
```

Setup needs access to python.org, files.pythonhosted.org / pypi.org, repo.maven.apache.org, puimula.org and GitHub's release download hosts. The prebuilt portable package requires none of these during checking. Local HTTP traffic must be allowed on `127.0.0.1`; no inbound network access is required.

Keep the launcher window open. Stop with Ctrl+C before moving or deleting the application folder. Removing the folder removes the application; downloaded documents and reports elsewhere are not deleted.
