# Sample documents

`english.pdf` and `english.docx` include deliberate spelling, grammar and spacing mistakes. The Word example includes a misspelling split across differently formatted runs and a table.

`finnish.pdf` and `finnish.docx` include deliberate Finnish spelling, repetition and spacing mistakes. Use Finnish mode; the English footer on the PDF also demonstrates why a fixed language can flag foreign text.

`northstar-edge-operations-en.pdf` is a 10-page technical operations manual with tables, an architecture diagram, and exactly 40 deliberate English spelling mistakes. The typo count is verified against selectable PDF text by `scripts/build_english_technical_example.py`.

`northstar-edge-operations-en.docx` is the Word version of the English manual, with the same 40 deliberate spelling mistakes. `northstar-edge-operations-fi.docx` is a matching Finnish technical manual with exactly 40 deliberate Finnish spelling mistakes. Both counts are verified by `scripts/build_technical_docx_examples.py`.

Run these through the application and compare the original with the reviewed copy. Expected examples include `recieve → receive`, `speling → spelling`, `huommenna → huomenna`, and `25kg → 25 kg`. Engines can offer multiple candidates; select the appropriate correction in the review screen.
