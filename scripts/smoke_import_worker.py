"""Exercise source or frozen import workers using synthetic documents only."""
import argparse
import asyncio
from pathlib import Path
from unittest.mock import patch

from backend.app.import_worker import extract_document
from tests.desktop.test_import_documents import pdf_bytes, workbook_bytes


async def check():
    documents = {"csv": b"Company,Value\nSynthetic,123\n", "xlsx": workbook_bytes(),
                 "pdf": pdf_bytes(), "html": b"<p>Synthetic content</p>"}
    for format, raw in documents.items():
        result = await extract_document(raw, format, permission_confirmed=True)
        assert result.format == format and result.blocks and not result.verified
    print("Four synthetic import formats passed the owned worker; no files, facts or provider requests were created.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packaged", action="store_true")
    args = parser.parse_args()
    if args.packaged:
        executable = Path(__file__).resolve().parents[1] / "dist/ltt-service.exe"
        if not executable.is_file():
            raise SystemExit("Build the Windows sidecar before packaged import verification")
        with patch("sys.frozen", True, create=True), patch("sys.executable", str(executable)):
            asyncio.run(check())
    else:
        asyncio.run(check())


if __name__ == "__main__":
    main()
