"""Check local Markdown files and heading links without network access."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def without_fences(text: str) -> str:
    return re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*$", "", text)


def heading_ids(text: str) -> set[str]:
    counts, result = {}, set()
    for heading in re.findall(r"(?m)^#{1,6}\s+(.+?)\s*#*\s*$", without_fences(text)):
        heading = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", heading)
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(f"{slug}-{count}" if count else slug)
    return result


def check_file(path: Path, root: Path) -> list[str]:
    errors = []
    text = without_fences(path.read_text(encoding="utf-8"))
    for match in re.finditer(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", text):
        raw = match.group(1).strip()
        target = raw[1:raw.index(">")] if raw.startswith("<") and ">" in raw else raw.split(' "', 1)[0]
        url = urlsplit(target)
        if url.scheme or url.netloc:
            continue
        linked = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
        label = f"{path.relative_to(root)}: {target}"
        if not linked.is_relative_to(root.resolve()):
            errors.append(f"{label}: link escapes repository")
        elif not linked.exists():
            errors.append(f"{label}: missing target")
        elif url.fragment and linked.suffix.lower() == ".md" and unquote(url.fragment) not in heading_ids(linked.read_text(encoding="utf-8")):
            errors.append(f"{label}: missing heading")
    return errors


def main():
    names = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        cwd=ROOT,
    ).decode("utf-8").split("\0")
    paths = sorted({ROOT / name for name in names if name and (ROOT / name).is_file()})
    errors = [error for path in paths for error in check_file(path, ROOT)]
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Local Markdown links and anchors passed ({len(paths)} files).")


if __name__ == "__main__":
    main()
