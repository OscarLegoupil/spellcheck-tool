from copy import deepcopy
from io import BytesIO
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from lxml import etree as ET

from .models import Document, DocumentError, Segment
from .text import normalize

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
COMMENT_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"


def w(name):
    return "{" + NS["w"] + "}" + name


def parse(data):
    return ET.fromstring(data, ET.XMLParser(resolve_entities=False, no_network=True))


def serialize(root):
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def package(data):
    try:
        with ZipFile(BytesIO(data)) as z:
            if len(z.infolist()) > 10000 or sum(i.file_size for i in z.infolist()) > 200_000_000:
                raise DocumentError("The Word package is too large to safely process.")
            if any(n.startswith("_xmlsignatures/") for n in z.namelist()):
                raise DocumentError("Supply an unsigned Word review copy.")
            return {n: z.read(n) for n in z.namelist()}
    except (BadZipFile, RuntimeError) as exc:
        raise DocumentError("This is not a readable .docx file.") from exc


def paragraph_text(paragraph):
    chars, refs = [], []
    for child in paragraph:
        if child.tag != w("r"):
            continue
        for node in child:
            if node.tag == w("t"):
                for offset, char in enumerate(node.text or ""):
                    chars.append(char)
                    refs.append((child, node, offset))
            elif node.tag in (w("tab"), w("br"), w("cr")):
                chars.append("\t" if node.tag == w("tab") else "\n")
                refs.append((child, node, 0))
    return "".join(chars), refs


def paragraphs(root):
    return root.xpath(".//w:body//w:p", namespaces=NS)


def unsafe(paragraph):
    tags = {
        w(t)
        for t in [
            "ins",
            "del",
            "moveFrom",
            "moveTo",
            "fldChar",
            "fldSimple",
            "instrText",
            "hyperlink",
            "sdt",
            "drawing",
            "pict",
            "commentRangeStart",
            "commentRangeEnd",
            "commentReference",
            "footnoteReference",
            "endnoteReference",
        ]
    }
    return any(n.tag in tags for n in paragraph.iter()) or any(
        parent.tag == w("txbxContent") for parent in paragraph.iterancestors()
    )


def read_word(name, data):
    files = package(data)
    if "word/document.xml" not in files:
        raise DocumentError("The file is not a Word document.")
    root = parse(files["word/document.xml"])
    segments, warnings = [], []
    for i, paragraph in enumerate(paragraphs(root)):
        if unsafe(paragraph):
            if paragraph.xpath(".//w:t", namespaces=NS):
                warnings.append(
                    f"Paragraph {i + 1}: fields, revisions, links, existing comments or embedded content; not checked."
                )
            continue
        text, refs = paragraph_text(paragraph)
        text, refs = normalize(text, refs)
        if text.strip():
            # Persist offsets, not lxml elements: the original is reparsed when exporting.
            segments.append(
                Segment(f"w{i}", text, f"Paragraph {i + 1}", refs=list(range(len(refs))))
            )
    for part_name in files:
        if part_name.startswith(("word/header", "word/footer")) or part_name in (
            "word/footnotes.xml",
            "word/endnotes.xml",
        ):
            if part_name.endswith(".xml") and parse(files[part_name]).xpath(
                ".//w:t", namespaces=NS
            ):
                warnings.append(f"{part_name.split('/')[-1]}: retained but not checked.")
    if not segments:
        raise DocumentError("No supported text paragraphs were found in this Word document.")
    return Document(name, data, "docx", segments, warnings)


def split_run(run, offset):
    """Split a plain run by visible characters, retaining its properties and child order."""
    length = sum(
        len(n.text or "") if n.tag == w("t") else 1
        for n in run
        if n.tag in (w("t"), w("tab"), w("br"), w("cr"))
    )
    if offset <= 0:
        return run
    if offset >= length:
        return run.getnext()
    right = ET.Element(w("r"), attrib=dict(run.attrib))
    props = run.find(w("rPr"))
    if props is not None:
        right.append(deepcopy(props))
    consumed = 0
    for node in list(run):
        if node.tag == w("rPr"):
            continue
        count = (
            len(node.text or "")
            if node.tag == w("t")
            else int(node.tag in (w("tab"), w("br"), w("cr")))
        )
        if consumed >= offset:
            run.remove(node)
            right.append(node)
        elif consumed + count > offset:
            cut = offset - consumed
            other = deepcopy(node)
            other.text = (node.text or "")[cut:]
            node.text = (node.text or "")[:cut]
            node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            other.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            right.append(other)
        consumed += count
    run.addnext(right)
    return right


def boundary(paragraph, offset):
    position = 0
    for run in list(paragraph):
        if run.tag != w("r"):
            continue
        length = len(paragraph_text_for_run(run))
        if position <= offset < position + length:
            return split_run(run, offset - position)
        position += length
    return None


def paragraph_text_for_run(run):
    return "".join(
        n.text or "" if n.tag == w("t") else "\t" if n.tag == w("tab") else "\n"
        for n in run
        if n.tag in (w("t"), w("tab"), w("br"), w("cr"))
    )


def annotate_word(document, selections):
    files = package(document.data)
    root = parse(files["word/document.xml"])
    before = root.xpath(".//w:t/text()", namespaces=NS)
    paras = paragraphs(root)
    comments = (
        parse(files["word/comments.xml"])
        if "word/comments.xml" in files
        else ET.Element(w("comments"), nsmap=NS)
    )
    used = [int(n.get(w("id"))) for n in comments if n.get(w("id"), "").isdigit()]
    next_id = max(used, default=-1) + 1
    for finding, correction in sorted(
        selections, key=lambda pair: (pair[0].segment_id, -pair[0].start)
    ):
        p = paras[int(finding.segment_id[1:])]
        raw, refs = paragraph_text(p)
        normalized, mapping = normalize(raw, list(range(len(refs))))
        if normalized[finding.start : finding.end] != finding.original:
            raise DocumentError("The Word finding no longer matches the source.")
        start, end = mapping[finding.start], mapping[finding.end - 1] + 1
        end_node = boundary(p, end)
        first = boundary(p, start)
        if first is None:
            raise DocumentError("Could not anchor a Word comment.")
        cid = str(next_id)
        next_id += 1
        begin = ET.Element(w("commentRangeStart"))
        begin.set(w("id"), cid)
        first.addprevious(begin)
        node = first
        while node is not None and node is not end_node:
            if node.tag == w("r"):
                props = node.find(w("rPr"))
                if props is None:
                    props = ET.Element(w("rPr"))
                    node.insert(0, props)
                # Soft shading keeps dark text legible; preserve pre-existing highlighting.
                if props.find(w("shd")) is None and props.find(w("highlight")) is None:
                    shade = ET.SubElement(props, w("shd"))
                    shade.set(w("val"), "clear")
                    shade.set(w("fill"), "FFF2CC")
            node = node.getnext()
        finish = ET.Element(w("commentRangeEnd"))
        finish.set(w("id"), cid)
        reference = ET.Element(w("r"))
        rp = ET.SubElement(reference, w("rPr"))
        style = ET.SubElement(rp, w("rStyle"))
        style.set(w("val"), "CommentReference")
        ref = ET.SubElement(reference, w("commentReference"))
        ref.set(w("id"), cid)
        if end_node is None:
            p.append(finish)
            p.append(reference)
        else:
            end_node.addprevious(finish)
            finish.addnext(reference)
        comment = ET.SubElement(comments, w("comment"))
        comment.set(w("id"), cid)
        comment.set(w("author"), "")
        cp = ET.SubElement(comment, w("p"))
        cr = ET.SubElement(cp, w("r"))
        ct = ET.SubElement(cr, w("t"))
        ct.text = correction
        ct.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    if "".join(root.xpath(".//w:t/text()", namespaces=NS)) != "".join(before):
        raise DocumentError("Output verification failed: Word text changed.")
    if not selections:
        return document.data
    files["word/document.xml"] = serialize(root)
    files["word/comments.xml"] = serialize(comments)
    relpath = "word/_rels/document.xml.rels"
    rels = (
        parse(files[relpath])
        if relpath in files
        else ET.Element("{" + REL + "}Relationships", nsmap={None: REL})
    )
    if not any(n.get("Type") == COMMENT_REL for n in rels):
        used_ids = {n.get("Id") for n in rels}
        number = 1
        while f"rIdSpellcheck{number}" in used_ids:
            number += 1
        ET.SubElement(
            rels,
            "{" + REL + "}Relationship",
            Id=f"rIdSpellcheck{number}",
            Type=COMMENT_REL,
            Target="comments.xml",
        )
    files[relpath] = serialize(rels)
    types = parse(files["[Content_Types].xml"])
    if not any(n.get("PartName") == "/word/comments.xml" for n in types):
        ET.SubElement(
            types,
            "{" + CT + "}Override",
            PartName="/word/comments.xml",
            ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
        )
    files["[Content_Types].xml"] = serialize(types)
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for name, content in files.items():
            z.writestr(name, content)
    checked = package(output.getvalue())
    if len(parse(checked["word/comments.xml"])) != len(comments):
        raise DocumentError("Output verification failed: missing Word comments.")
    return output.getvalue()
