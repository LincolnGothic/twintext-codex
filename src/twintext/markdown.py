"""Translate visible Markdown without rewriting code or structural source.

CommonMark block maps distinguish nested lists from actual code. Tables are
translated cell by cell; link destinations, code, HTML blocks and math are opaque.
"""

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt

PREFIX = re.compile(
    r"^(\s*(?:(?:>\s*)+)?"
    r"(?:#{1,6}\s+|(?:[-+*]|\d+[.)])\s+(?:\[[ xX]\]\s+)?|\[\^[^\]]+\]:\s*)?)(.*)$"
)
PROTECTED = re.compile(
    r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)|"
    r"[a-zA-Z][\w+.-]*://[^\s<>]+|<[^>\n]+>|"
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|"
    r"(?<!\w)(?:/|~/|\./|\.\./)[\w./@%+~:=-]+|"
    r"(?<!\w)[A-Za-z]:\\[\w.\\/@%+~:=-]+|"
    r"(?<![\w/])(?:[\w.@+-]+/)*[\w.@+-]+\.(?:py|js|ts|tsx|jsx|rs|go|java|c|cpp|h|hpp|cs|"
    r"md|txt|json|yaml|yml|toml|sh|html|css|png|jpg|jpeg|svg|pdf|docx|xlsx|sqlite3)(?::\d+)?(?![\w/])|"
    r"\$(?!\d+(?:[.,]\d+)*(?:\s|$))[^$\n]+\$(?!\d)|\\\([^\n]*?\\\)|"
    r"[$€£¥]\d[\d,.]*(?!\w)|"
    r':{1,2}codex-[\w-]+\{(?:"(?:\\.|[^"\\])*"|[^{}\n"])*\}|'
    r"\[\^[^\]\n]+\]|\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]|"
    r"\\[!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~]|&(?:\w+|#\d+|#x[\da-fA-F]+);|"
    r"\*\*|__|~~|(?<!\w)[*_]|[*_](?!\w)"
)
REFERENCE = re.compile(r"^ {0,3}\[([^\]^][^\]]*)\]:", re.MULTILINE)
SYNTAX_LINE = re.compile(r"^(?:[-*_]\s*){3,}$|^=+\s*$|^-+\s*$")


@dataclass
class Block:
    original: str
    translatable: bool
    kind: str = "prose"


def blocks(text: str):
    lines = text.splitlines(keepends=True)
    kinds = ["opaque"] * len(lines)
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    for token in tokens:
        if token.type in ("inline", "heading_open") and token.map:
            start, end = token.map
            kinds[start:end] = ["prose"] * (end - start)
    for token in tokens:
        if token.type in ("fence", "code_block", "html_block", "table_open") and token.map:
            start, end = token.map
            kind = "table" if token.type == "table_open" else "opaque"
            kinds[start:end] = [kind] * (end - start)
    math_end = None
    for index, line in enumerate(lines):
        raw = re.sub(r"^\s*(?:>\s*)*", "", line).strip()
        if math_end:
            kinds[index] = "opaque"
            if raw == math_end:
                math_end = None
            continue
        if kinds[index] == "opaque":
            if re.match(r"^\[\^[^\]]+\]:\s+", raw):
                kinds[index] = "prose"
            else:
                continue
        if raw in ("$$", "\\["):
            kinds[index] = "opaque"
            math_end = "$$" if raw == "$$" else "\\]"
        elif (raw.startswith("$$") and raw.endswith("$$")) or (
            raw.startswith("\\[") and raw.endswith("\\]")
        ):
            kinds[index] = "opaque"
        elif re.match(r":{1,2}codex-[\w-]+\{", raw):
            kinds[index] = "opaque"
        elif not raw:
            kinds[index] = "opaque"
    output = []
    for index, line in enumerate(lines):
        kind = kinds[index]
        if output and output[-1].kind == kind:
            output[-1].original += line
        else:
            output.append(Block(line, kind != "opaque", kind))
    return output


def normalize_id(text):
    return " ".join(text.split()).casefold()


def reference_ids(text):
    return {normalize_id(match[1]) for match in REFERENCE.finditer(text)}


def prose(text: str):
    # Detection sees the same visible text as translation, including table headers.
    visible = []
    references = reference_ids(text)
    for block in blocks(text):
        if block.translatable:
            translate_block(
                block.original, lambda value: visible.append(value) or value, block.kind, references
            )
    return " ".join(visible)


def translate_span(text: str, translate):
    if not any(character.isalpha() for character in text):
        return text
    start = text[: len(text) - len(text.lstrip())]
    end = text[len(text.rstrip()) :]
    return start + translate(text.strip()) + end


def closing(text, start, left, right):
    """Match nested brackets/parentheses, respecting Markdown escapes."""
    depth = 0
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if left == "[" and text[index] == "`":
            code = PROTECTED.match(text, index)
            if code:
                index = code.end()
                continue
        if left == "(" and text[index] in "\"'" and index > start and text[index - 1].isspace():
            quote = text[index]
            index += 1
            while index < len(text) and text[index] != quote:
                index += 2 if text[index] == "\\" else 1
            index += 1
            continue
        if left == "(" and text[index] == "<" and ">" in text[index:]:
            index = text.index(">", index) + 1
            continue
        if text[index] == left:
            depth += 1
        elif text[index] == right:
            depth -= 1
            if not depth:
                return index
        index += 1
    return None


def translate_inline(body, translate, references=(), depth=0):
    result = []
    index = start = 0
    while index < len(body):
        protected = PROTECTED.match(body, index)
        label_start = index + 1 if body.startswith("![", index) else index
        end = replacement = None
        if not protected and depth < 16 and body[label_start : label_start + 1] == "[":
            label_end = closing(body, label_start, "[", "]")
            if label_end is not None:
                label = body[label_start + 1 : label_end]
                after = label_end + 1
                if body[after : after + 1] == "(":
                    destination_end = closing(body, after, "(", ")")
                    if destination_end is not None:
                        end = destination_end + 1
                elif body[after : after + 1] == "[":
                    reference_end = closing(body, after, "[", "]")
                    if reference_end is not None:
                        end = reference_end + 1
                elif normalize_id(label) in references:
                    end = after
                if end:
                    translated = translate_inline(label, translate, references, depth + 1)
                    suffix = body[after:end]
                    if suffix in ("", "[]"):
                        suffix = "[" + label + "]"
                    replacement = body[index : label_start + 1] + translated + "]" + suffix
        if protected:
            end, replacement = protected.end(), protected[0]
        if end:
            result.append(translate_span(body[start:index], translate))
            result.append(replacement)
            index = start = end
        else:
            index += 1
    result.append(translate_span(body[start:], translate))
    return "".join(result)


def row_parts(raw):
    """Keep table delimiters, including escaped pipes and code-span pipes."""
    parts = []
    start = index = 0
    code = None
    while index < len(raw):
        if raw[index] == "\\":
            index += 2
            continue
        if raw[index] == "`":
            end = index + 1
            while end < len(raw) and raw[end] == "`":
                end += 1
            marker = raw[index:end]
            if code == marker:
                code = None
            elif code is None and re.search(r"(?<!`)" + re.escape(marker) + r"(?!`)", raw[end:]):
                code = marker
            index = end
            continue
        if raw[index] == "|" and not code:
            parts.extend((raw[start:index], "|"))
            start = index + 1
        index += 1
    parts.append(raw[start:])
    return parts


def translate_table(text, translate, references, translate_header=None):
    output = []

    def safe_cell(fragment):
        # Model-created pipes/newlines must not create extra columns or rows.
        value = cell_translator(fragment)
        return value.replace("|", r"\|").replace("\r", " ").replace("\n", " ")

    for row, line in enumerate(text.splitlines(keepends=True)):
        cell_translator = translate_header if row == 0 and translate_header else translate
        raw = line.rstrip("\r\n")
        newline = line[len(raw) :]
        prefix = re.match(r"^(\s*(?:>\s*)*)", raw)[0]
        parts = row_parts(raw[len(prefix) :])
        cells = [value.strip() for value in parts[::2] if value.strip()]
        if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            output.append(line)
        else:
            output.append(
                prefix
                + "".join(
                    translate_inline(value, safe_cell, references) if i % 2 == 0 else value
                    for i, value in enumerate(parts)
                )
                + newline
            )
    return "".join(output)


def translate_block(text: str, translate, kind="prose", references=None, translate_header=None):
    references = reference_ids(text) if references is None else references
    if kind == "table":
        return translate_table(text, translate, references, translate_header)
    output = []
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        newline = line[len(raw) :]
        match = PREFIX.match(raw)
        prefix, body = match[1], match[2]
        if SYNTAX_LINE.fullmatch(body.strip()):
            output.append(line)
            continue
        suffix = re.search(r"\s+#+\s*$", body) if re.match(r"\s*(?:>\s*)*#{1,6} ", raw) else None
        if suffix:
            body, ending = body[: suffix.start()], body[suffix.start() :]
        else:
            ending = ""
        output.append(prefix + translate_inline(body, translate, references) + ending + newline)
    return "".join(output)
