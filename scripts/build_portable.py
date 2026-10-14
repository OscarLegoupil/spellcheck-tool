"""Package a verified private Windows runtime and the complete application source."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / "dist/Spellcheck-Tool-Windows.zip"
output.parent.mkdir(exist_ok=True)
required = [".runtime/python/python.exe", ".runtime/voikko/libvoikko-1.dll"]
for item in required:
    if not (ROOT / item).is_file():
        raise SystemExit("Run Windows setup before building: missing " + item)
include = [
    "src",
    "scripts",
    "tests",
    "examples",
    "docs",
    ".runtime/python",
    ".runtime/java",
    ".runtime/voikko",
    ".runtime/languagetool",
]
files = [
    ROOT / x
    for x in (
        "Start.cmd",
        "Setup.cmd",
        "README.md",
        "LICENSE",
        "THIRD_PARTY.md",
        "pyproject.toml",
        "requirements-windows.lock",
    )
]
for folder in include:
    files.extend(
        p
        for p in (ROOT / folder).rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and not any(part.endswith(".egg-info") for part in p.parts)
    )
with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as archive:
    for path in sorted(set(files)):
        archive.write(path, "Spellcheck-Tool/" + path.relative_to(ROOT).as_posix())
print(output)
