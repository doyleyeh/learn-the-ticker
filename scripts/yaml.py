from __future__ import annotations

from typing import Any, TextIO


def safe_load(stream: str | TextIO) -> Any:
    text = stream.read() if hasattr(stream, "read") else str(stream)
    lines = [
        (len(raw) - len(raw.lstrip(" ")), raw.strip())
        for raw in text.splitlines()
        if raw.strip() and not raw.lstrip().startswith("#")
    ]
    if not lines:
        return None
    value, _ = _parse_block(lines, 0, lines[0][0])
    return value


def _parse_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[Any, int]:
    if index >= len(lines):
        return {}, index

    if lines[index][1].startswith("- "):
        items: list[Any] = []
        while index < len(lines):
            current_indent, content = lines[index]
            if current_indent != indent or not content.startswith("- "):
                break
            item_text = content[2:].strip()
            index += 1
            if not item_text:
                item, index = _parse_block(lines, index, indent + 2)
            elif ":" in item_text:
                key, raw_value = _split_key_value(item_text)
                item = {key: _parse_scalar(raw_value)}
                if index < len(lines) and lines[index][0] > indent:
                    nested, index = _parse_block(lines, index, indent + 2)
                    if isinstance(nested, dict):
                        item.update(nested)
            else:
                item = _parse_scalar(item_text)
            items.append(item)
        return items, index

    mapping: dict[str, Any] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent != indent or content.startswith("- "):
            break
        key, raw_value = _split_key_value(content)
        index += 1
        if raw_value == "":
            value, index = _parse_block(lines, index, indent + 2)
        else:
            value = _parse_scalar(raw_value)
        mapping[key] = value
    return mapping, index


def _split_key_value(content: str) -> tuple[str, str]:
    key, separator, raw_value = content.partition(":")
    if not separator:
        raise ValueError(f"Unsupported YAML line: {content}")
    return key.strip(), raw_value.strip()


def _parse_scalar(value: str) -> Any:
    if value == "":
        return None
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        return value
