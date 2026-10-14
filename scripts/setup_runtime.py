"""Install pinned language resources; no account or external checking service."""

import argparse
import hashlib
import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "src/spellcheck_tool/resources"
RUNTIME = ROOT / ".runtime"


def download(asset, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if (
        destination.exists()
        and hashlib.sha256(destination.read_bytes()).hexdigest() == asset["sha256"]
    ):
        return destination
    temporary = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(3):
        try:
            with urlopen(asset["url"], timeout=90) as source, temporary.open("wb") as target:
                shutil.copyfileobj(source, target)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != asset["sha256"]:
                raise ValueError(
                    f"Checksum mismatch: {asset['name']}. The upstream file changed; update the reviewed lock file before retrying."
                )
            temporary.replace(destination)
            return destination
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)
        finally:
            temporary.unlink(missing_ok=True)


def extract(archive, destination):
    destination = destination.resolve()
    with ZipFile(archive) as z:
        for info in z.infolist():
            if not (destination / info.filename).resolve().is_relative_to(destination):
                raise ValueError("Unsafe archive member")
        z.extractall(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((RESOURCES / "downloads.lock.json").read_text())
    cache = RUNTIME / "downloads"
    dictionary = download(manifest["dictionary"], cache / manifest["dictionary"]["name"])
    extract(dictionary, RUNTIME / "voikko")
    print("Finnish dictionary ready.", flush=True)
    if args.windows:
        download(manifest["voikko"], RUNTIME / "voikko/libvoikko-1.dll")
        java = download(manifest["java"], cache / manifest["java"]["name"])
        extract(java, RUNTIME / "java")
        print("Private Java runtime and Finnish library ready.", flush=True)
    lock = json.loads((RESOURCES / "english-runtime.lock.json").read_text())

    def install(asset):
        download(asset, RUNTIME / "languagetool" / asset["name"])

    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(install, lock["artifacts"]))
    allowed = {asset["name"] for asset in lock["artifacts"]}
    for old in (RUNTIME / "languagetool").glob("*.jar"):
        if old.name not in allowed:
            old.unlink()
    print(
        f"LanguageTool {lock['version']} ready. Run python -m spellcheck_tool doctor to verify.",
        flush=True,
    )


if __name__ == "__main__":
    main()
