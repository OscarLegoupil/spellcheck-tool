import re
import unicodedata

WORD = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*", re.UNICODE)
PROTECTED = re.compile(
    r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b\w*\d\w*(?:[-_/.:]\w+)*\b"
)


def normalize(text, refs):
    """Normalize checker text while retaining every source character's location."""
    result, mapped = [], []
    for char, ref in zip(text, refs, strict=True):
        if char == "\u00ad":
            continue
        chars = unicodedata.normalize("NFKC", char) if char in "ﬀﬁﬂﬃﬄﬅﬆ" else char
        if char == "\u00a0":
            chars = " "
        result.extend(chars)
        mapped.extend([ref] * len(chars))
    return "".join(result), mapped


def utf16_to_index(text, offset):
    units = 0
    for i, char in enumerate(text):
        if units >= offset:
            return i
        units += 2 if ord(char) > 0xFFFF else 1
    return len(text)


def anchor_replacement(text, start, end, suggestions):
    """Give insertions/deletions visible anchors and correction-only comment text."""
    if start < 0 or end < start or end > len(text):
        raise ValueError("Invalid finding offsets")
    if start == end or any(not s or s.isspace() for s in suggestions):
        left, right = start, end
        while left > 0 and not text[left - 1].isspace():
            left -= 1
        while right < len(text) and not text[right].isspace():
            right += 1
        if left == start and right == end:
            while left > 0 and text[left - 1].isspace():
                left -= 1
            while left > 0 and not text[left - 1].isspace():
                left -= 1
            if left == start:
                while right < len(text) and text[right].isspace():
                    right += 1
                while right < len(text) and not text[right].isspace():
                    right += 1
        suggestions = [text[left:start] + s + text[end:right] for s in suggestions]
        start, end = left, right
    return start, end, list(dict.fromkeys(s for s in suggestions if s.strip()))
