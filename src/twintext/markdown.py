"""Conservative Markdown translation: protected source never enters the model.

This is intentionally not a complete Markdown parser. Tables, reference-link
definitions, fenced and indented code, and display math remain verbatim.
"""

import re
from dataclasses import dataclass

FENCE = re.compile(r"^(?: {0,3}> ?)* {0,3}(`{3,}|~{3,})")
PREFIX = re.compile(r"^(\s*(?:(?:>\s*)+)?(?:#{1,6}\s+|[-+*]\s+|\d+[.)]\s+)?)(.*)$")
PROTECTED = re.compile(
    r"(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)|!?\[[^\]\n]*\]\([^\n]*?\)|"
    r"!?\[[^\]\n]*\]\[[^\]\n]*\]|"
    r"https?://[^\s<>]+|<[^>\n]+>|"
    r"(?<!\w)(?:/|~/|\./|\.\./)[\w./@%+~:=-]+|"
    r"\$[^$\n]+\$|\\\([^\n]*?\\\)|"
    r"\*\*|__|~~|(?<!\w)[*_]|[*_](?!\w)"
)


@dataclass
class Block:
    original: str
    translatable: bool


def blocks(text: str):
    output = []
    buffer = []
    fence = None
    math = False
    table = False

    def flush():
        if buffer:
            output.append(Block("".join(buffer), True))
            buffer.clear()

    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if fence:
            output[-1].original += line
            if (
                match
                and match[1][0] == fence[0]
                and len(match[1]) >= len(fence)
                and not line[match.end() :].strip()
            ):
                fence = None
            continue
        if match:
            flush()
            output.append(Block(line, False))
            fence = match[1]
            continue
        if line.strip() in ("$$", "\\[", "\\]"):
            flush()
            output.append(Block(line, False))
            math = not math
            continue
        # CommonMark permits tables without a leading pipe. Detect their separator.
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if "|" in line and re.fullmatch(r"\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)+\|?", next_line):
            table = True
        if not line.strip() or "|" not in line:
            table = False
        opaque = (
            table
            or math
            or line.startswith(("    ", "\t"))
            or bool(re.match(r"^\s*\[[^\]]+\]:|^\s*\|", line))
            or bool(re.match(r"^\s*(?:[-*_]\s*){3,}$", line))
        )
        if not line.strip() or opaque:
            flush()
            output.append(Block(line, False))
        else:
            buffer.append(line)
    flush()
    return output


def prose(text: str):
    return " ".join(
        PROTECTED.sub(" ", block.original) for block in blocks(text) if block.translatable
    )


def translate_span(text: str, translate):
    if not any(character.isalpha() for character in text):
        return text
    start = text[: len(text) - len(text.lstrip())]
    end = text[len(text.rstrip()) :]
    return start + translate(text.strip()) + end


def translate_block(text: str, translate):
    output = []
    for line in text.splitlines(keepends=True):
        newline = "\n" if line.endswith("\n") else ""
        raw = line[:-1] if newline else line
        match = PREFIX.match(raw)
        prefix, body = match[1], match[2]
        cursor = 0
        result = [prefix]
        for token in PROTECTED.finditer(body):
            result.append(translate_span(body[cursor : token.start()], translate))
            result.append(token[0])
            cursor = token.end()
        result.append(translate_span(body[cursor:], translate))
        output.append("".join(result) + newline)
    return "".join(output)
