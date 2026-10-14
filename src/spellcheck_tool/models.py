import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Segment:
    id: str
    text: str
    location: str
    language: str | None = None
    refs: list[Any] = field(default_factory=list, repr=False)


@dataclass
class Finding:
    segment_id: str
    start: int
    end: int
    original: str
    suggestions: list[str]
    rule: str
    category: str
    engine: str
    message: str = ""
    id: str = ""
    selected: bool = True

    def __post_init__(self):
        if not self.id:
            key = f"{self.segment_id}:{self.start}:{self.end}:{self.rule}"
            self.id = hashlib.sha256(key.encode()).hexdigest()[:16]
        if not self.suggestions:
            self.selected = False

    def to_dict(self):
        return asdict(self)


@dataclass
class Options:
    language: str = "mixed"
    english: str = "en-GB"
    thorough: bool = True
    glossary: list[str] = field(default_factory=list)
    terminology: dict[str, str] = field(default_factory=dict)
    ignore_uppercase: bool = True
    ignore_codes: bool = True
    ignore_rules: list[str] = field(default_factory=list)


@dataclass
class Document:
    name: str
    data: bytes
    kind: str
    segments: list[Segment]
    warnings: list[str] = field(default_factory=list)
    pages: int = 0


class DocumentError(ValueError):
    pass


class EngineError(RuntimeError):
    pass
