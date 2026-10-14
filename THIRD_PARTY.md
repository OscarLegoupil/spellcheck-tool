# Third-party components

The MIT license in `LICENSE` covers this repository's original code. Dependencies retain their own copyrights and licenses. In particular, the runtime includes copyleft components; do not describe the complete bundle as MIT-only.

| Component | Version | License / source |
| --- | --- | --- |
| PyMuPDF / MuPDF | PyMuPDF 1.26.7 | AGPL-3.0 or a separate commercial license; [project and source](https://github.com/pymupdf/PyMuPDF/tree/1.26.7), [MuPDF](https://mupdf.com/) |
| LanguageTool | 6.6 | LGPL-2.1-or-later; [source](https://github.com/languagetool-org/languagetool/tree/v6.6), [Maven source artifacts](https://repo.maven.apache.org/maven2/org/languagetool/) |
| libvoikko native | Windows 4.3+win1 | GPL-2.0-or-later; [source and build files](https://www.puimula.org/htp/testing/voikko-sdk/win-crossbuild/), [upstream](https://github.com/voikko/corevoikko) |
| libvoikko Python wrapper | 4.3 | GPL-2.0-or-later; [PyPI source](https://pypi.org/project/libvoikko/4.3/) |
| Finnish morphology dictionary | format 5, snapshot 2024-06-18 | GPL-2.0-or-later; copyright Hannu Väisänen, Harri Pitkänen, Teemu Likonen and others; [source](https://github.com/voikko/corevoikko/tree/master/voikko-fi); installed index.txt contains original notice |
| CPython | 3.12.10 | PSF license; [source](https://www.python.org/downloads/release/python-31210/) |
| Temurin OpenJDK JRE | 17.0.16+8 | GPL-2.0 with Classpath Exception and accompanying notices; [release and source](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.16%2B8) |
| lxml | 6.0.2 | BSD and native-library notices; [source](https://pypi.org/project/lxml/6.0.2/) |
| FastAPI, Uvicorn, python-multipart | pinned in requirements | MIT / BSD / Apache-2.0 respectively; package metadata contains licenses and project source URLs |

Python wheels retain their distribution metadata and license files. Java JARs retain their META-INF notices, and the JRE retains its legal directory. Transitive dependencies are enumerated in the lock files and have separate terms. Upstream commercial services and premium features are not included.

Source locations and exact binary hashes are recorded so the runtime can be audited and reproduced. When redistributing a runtime bundle, preserve the notices and satisfy the corresponding-source requirements of its copyleft dependencies as well as those for the combined application. This repository publishes the application's complete source and build scripts.
