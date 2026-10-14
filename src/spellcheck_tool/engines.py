import json
import os
import shutil
import socket
import subprocess
import threading
import time
from collections import Counter
from functools import lru_cache
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

from .models import EngineError, Finding
from .text import WORD, anchor_replacement, utf16_to_index


def runtime_dir():
    override = os.environ.get("SPELLCHECK_RUNTIME")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[2] / ".runtime"


class Finnish:
    def __init__(self):
        from libvoikko import Voikko

        folder = runtime_dir() / "voikko"
        native = os.environ.get("SPELLCHECK_VOIKKO_LIBRARY")
        if native:
            Voikko.setLibrarySearchPath(native)
        elif os.name == "nt":
            Voikko.setLibrarySearchPath(str(folder))
        try:
            self.voikko = Voikko("fi", path=str(folder))
            self.voikko.setAcceptTitlesInGc(True)
            self.voikko.setAcceptUnfinishedParagraphsInGc(True)
            self.voikko.setIgnoreDot(True)
        except Exception as exc:
            raise EngineError(
                "Finnish engine unavailable. Run Setup.cmd to install Voikko and its dictionary."
            ) from exc
        self.lock = threading.Lock()

    @lru_cache(maxsize=20000)
    def spell(self, word):
        with self.lock:
            return self.voikko.spell(word)

    @lru_cache(maxsize=5000)
    def suggest(self, word):
        with self.lock:
            return tuple(self.voikko.suggest(word))

    def check(self, segment, options):
        findings = []
        for match in WORD.finditer(segment.text):
            word = match.group()
            if len(word) < 2 or (options.ignore_uppercase and word.isupper()):
                continue
            if not self.spell(word):
                findings.append(
                    Finding(
                        segment.id,
                        match.start(),
                        match.end(),
                        word,
                        list(self.suggest(word)[:5]),
                        "FI_SPELLING",
                        "spelling",
                        "Voikko",
                        "Word not recognised by the Finnish dictionary.",
                    )
                )
        with self.lock:
            errors = self.voikko.grammarErrors(segment.text, "en")
        for error in errors:
            start, end, suggestions = anchor_replacement(
                segment.text,
                error.startPos,
                error.startPos + error.errorLen,
                list(error.suggestions),
            )
            findings.append(
                Finding(
                    segment.id,
                    start,
                    end,
                    segment.text[start:end],
                    suggestions,
                    f"FI_GRAMMAR_{error.errorCode}",
                    "grammar",
                    "Voikko",
                    error.shortDescription,
                )
            )
        return findings

    def close(self):
        with self.lock:
            self.voikko.terminate()


class English:
    def __init__(self):
        self.process = None
        self.port = None
        self.lock = threading.Lock()
        self.opener = build_opener(ProxyHandler({}))
        self.cache = {}

    def start(self):
        if self.process and self.process.poll() is None:
            return
        folder = runtime_dir()
        java = next((folder / "java").glob("**/bin/java.exe"), None)
        java = java or shutil.which("java")
        jars = sorted((folder / "languagetool").rglob("*.jar"))
        if not java or not jars:
            raise EngineError(
                "English engine unavailable. Run Setup.cmd to install the private Java runtime and LanguageTool."
            )
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        classpath = str(folder / "languagetool" / "*")
        args = [
            str(java),
            "-Xmx768m",
            "-cp",
            classpath,
            "org.languagetool.server.HTTPServer",
            "--port",
            str(self.port),
        ]
        logdir = folder / "logs"
        logdir.mkdir(parents=True, exist_ok=True)
        with (logdir / "english-engine.log").open("wb") as log:
            self.process = subprocess.Popen(
                args,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise EngineError(
                    "English engine could not start. See .runtime/logs/english-engine.log."
                )
            try:
                with self.opener.open(f"http://127.0.0.1:{self.port}/v2/languages", timeout=1):
                    return
            except (URLError, TimeoutError, OSError):
                time.sleep(0.15)
        self.close()
        raise EngineError("English engine startup timed out.")

    def check(self, segment, options):
        with self.lock:
            self.start()
            key = (segment.text, options.english, options.thorough)
            if key not in self.cache:
                body = urlencode(
                    {
                        "text": segment.text,
                        "language": options.english,
                        "level": "picky" if options.thorough else "default",
                    }
                ).encode()
                try:
                    request = Request(f"http://127.0.0.1:{self.port}/v2/check", data=body)
                    with self.opener.open(request, timeout=45) as response:
                        result = json.load(response)
                    if result.get("warnings", {}).get("incompleteResults"):
                        raise EngineError(
                            "English engine returned an incomplete check. Split the document into smaller files."
                        )
                    if len(self.cache) >= 500:
                        self.cache.clear()
                    self.cache[key] = result["matches"]
                except (URLError, TimeoutError, KeyError) as exc:
                    raise EngineError(
                        "English checking failed; no partial result will be presented as complete."
                    ) from exc
            matches = self.cache[key]
        findings = []
        for match in matches:
            start = utf16_to_index(segment.text, match["offset"])
            end = utf16_to_index(segment.text, match["offset"] + match["length"])
            suggestions = [x["value"] for x in match.get("replacements", [])[:5]]
            start, end, suggestions = anchor_replacement(segment.text, start, end, suggestions)
            category = "spelling" if match["rule"].get("issueType") == "misspelling" else "grammar"
            findings.append(
                Finding(
                    segment.id,
                    start,
                    end,
                    segment.text[start:end],
                    suggestions,
                    match["rule"]["id"],
                    category,
                    "LanguageTool",
                    match.get("message", ""),
                )
            )
        return findings

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None


FI_HINTS = set(
    "ja on ovat ei ole että sekä tai mutta tämä sen se ne myös joka mukaan kanssa varten kuin kun jos voi olla oli olivat nämä sitä siitä tässä tulee tuleeessa".split()
)
EN_HINTS = set(
    "the a an and is are was were of to for with this that these those shall must should be has have will in on from by not it its can as".split()
)


def detect_language(text, finnish=None):
    words = [m.group().casefold() for m in WORD.finditer(text)]
    counts = Counter(words)
    fi = sum(counts[w] for w in FI_HINTS)
    en = sum(counts[w] for w in EN_HINTS)
    fi += sum(any(c in w for c in "äö") for w in words) * 0.5
    if fi == en and finnish and words:
        fi += sum(finnish.spell(w) for w in words[:30] if len(w) > 3) * 0.25
    return ("fi" if fi > en else "en"), abs(fi - en) < 1


class Engines:
    def __init__(self):
        self.finnish = None
        self.english = English()

    def get_finnish(self):
        if self.finnish is None:
            self.finnish = Finnish()
        return self.finnish

    def check(self, segment, options):
        if segment.language == "fi":
            return self.get_finnish().check(segment, options)
        return self.english.check(segment, options)

    def close(self):
        self.english.close()
        if self.finnish:
            self.finnish.close()
            self.finnish = None

    def status(self):
        folder = runtime_dir()
        dictionary = bool(list((folder / "voikko").glob("5/*/mor.vfst")))
        return {
            "finnish": dictionary
            and (os.name != "nt" or (folder / "voikko/libvoikko-1.dll").exists()),
            "english": bool(list((folder / "languagetool").rglob("language-en-*.jar"))),
        }
