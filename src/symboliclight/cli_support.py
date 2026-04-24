from __future__ import annotations


def contains_line_comment_source(source: str) -> bool:
    in_string = False
    escaped = False
    for index, char in enumerate(source):
        if escaped:
            escaped = False
            continue
        if char == "\\" and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if not in_string and char == "/" and index + 1 < len(source) and source[index + 1] == "/":
            return True
    return False
