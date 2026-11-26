import os
import re
import stat
from pathlib import Path


PUNCTUATION = str.maketrans({
    **dict.fromkeys("‐‑‒–—―−", "-"),
    **dict.fromkeys("‘’‚‛", "'"),
    **dict.fromkeys("“”„‟", '"'),
    **dict.fromkeys("\u00a0\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u202f\u205f\u3000", " "),
})


def patch_sections(text):
    lines = text.replace("\r\n", "\n").strip().split("\n")
    wrapper = re.fullmatch(r"""(?:apply_patch[ \t]+)?<<[ \t]*(['"]?)([A-Za-z_]\w*)\1""", lines[0])
    if wrapper and lines[-1] == wrapper[2]:
        lines = lines[1:-1]
    if len(lines) < 2 or lines[0].strip() != "*** Begin Patch" or lines[-1].strip() != "*** End Patch":
        raise ValueError("patch markers")
    body = "\n".join([*lines[1:-1], ""]).lstrip("\n \t")
    if body.startswith("*** Environment ID: "):
        body = body.partition("\n")[2].lstrip("\n \t")
    prefix, *sections = re.split(r"^\*\*\* (Add|Update|Delete) File: (.+)\n", body, flags=re.MULTILINE)
    if prefix:
        raise ValueError("patch header")
    for operation, path, section in zip(sections[::3], sections[1::3], sections[2::3]):
        lines = section.removesuffix("\n").split("\n") if section else []
        lines = [line for line in lines if line != r"\ No newline at end of file"]
        destination = path = path.strip()
        if operation == "Update" and lines and lines[0].startswith("*** Move to: "):
            destination = lines.pop(0).removeprefix("*** Move to: ").strip()
        if not path or not destination:
            raise ValueError("empty patch path")
        yield operation, path, destination, lines


def update_chunks(lines):
    anchor = None
    pending = False
    changes = []
    eof = False
    for line in [*lines, "@@"]:
        marker = line.rstrip()
        if marker == "@@" or marker.startswith("@@ "):
            if changes:
                yield anchor, changes, eof
            elif pending:
                raise ValueError("empty patch hunk")
            anchor = marker[3:] if marker != "@@" else None
            pending = True
            changes, eof = [], False
        elif marker == "*** End of File" and changes and not eof:
            eof = True
        elif eof and not line.strip():
            continue
        elif not eof and (not line or line[0] in " +-"):
            changes.append(line or " ")
        else:
            raise ValueError("invalid patch hunk")


def seek(lines, pattern, start, eof=False):
    if not pattern:
        return start
    end = len(lines) - len(pattern)
    start = max(start, end) if eof else start
    for normalize in (lambda line: line, str.rstrip, str.strip, lambda line: line.strip().translate(PUNCTUATION)):
        expected = [normalize(line) for line in pattern]
        for index in range(start, end + 1):
            if all(normalize(lines[index + i]) == line for i, line in enumerate(expected)):
                return index
    return None


def update_content(content, chunks):
    parts = re.split(r"(\r\n|\r|\n)", content)
    source = list(zip(parts[::2], [*parts[1::2], ""]))
    if source[-1] == ("", ""):
        source.pop()
    texts = [line for line, _ in source]
    newline = parts[1] if len(parts) > 1 else "\n"
    result, append = [], []
    cursor = start = 0
    for anchor, changes, eof in chunks:
        if anchor is not None:
            match = seek(texts, [anchor], start)
            if match is None:
                raise ValueError("patch anchor not found")
            start = match + 1
        old = [line[1:] for line in changes if line[0] != "+"]
        new = []
        offset = 0
        for line in changes:
            if line[0] != "-":
                new.append((line[1:], offset if line[0] == " " else None))
            if line[0] != "+":
                offset += 1
        if not old:
            append.extend((line, newline) for line, _ in new)
            continue
        index = seek(texts, old, start, eof)
        if index is None and old[-1] == "":
            old = old[:-1]
            if new and new[-1][0] == "":
                new = new[:-1]
            index = seek(texts, old, start, eof)
        if index is None:
            raise ValueError("patch context not found")
        result.extend(source[cursor:index])
        for line, offset in new:
            if offset is None:
                result.append((line, newline))
            elif offset < len(old):
                result.append(source[index + offset])
        cursor = start = index + len(old)
    return "".join(line + (ending or newline) for line, ending in [*result, *source[cursor:], *append])


def read_content(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "r", encoding="utf-8", newline="") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            raise ValueError("not a regular file")
        return file.read()


def patch_writes(text, cwd, *, post):
    files = {}
    for operation, path, destination, lines in patch_sections(text):
        source = Path(os.path.abspath(cwd / path))
        target = Path(os.path.abspath(cwd / destination))
        if operation == "Delete":
            if lines:
                raise ValueError("invalid deletion")
            files[source] = None
            continue
        if operation == "Add":
            if any(not line.startswith("+") for line in lines):
                raise ValueError("invalid addition")
            content = "".join(line[1:] + "\n" for line in lines)
        else:
            chunks = list(update_chunks(lines))
            if not chunks:
                raise ValueError("empty patch update")
            content = None
            if not post:
                if source in files:
                    if files[source] is None:
                        raise ValueError("patch updates a removed file")
                    content = files[source]["content"]
                else:
                    content = read_content(source)
                content = update_content(content, chunks)
            if target != source:
                files[source] = None
        files[target] = {"file_path": destination, "content": content}
    writes = []
    for path, write in files.items():
        if write is not None:
            if post:
                write["content"] = read_content(path)
            writes.append(write)
    return writes
