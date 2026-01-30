#!/usr/bin/env python3
"""Lightweight local UI server for bibtex cleaning (no external deps)."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from clean import clean_bibtex_text, DEFAULT_KEEP_FIELDS

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"


class UIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/api/clean":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))

            input_text = payload.get("input", "")
            keep_fields = payload.get("keep_fields") or DEFAULT_KEEP_FIELDS
            do_titlecase = bool(payload.get("titlecase", True))
            regen_keys = bool(payload.get("regen_keys", False))
            journal_abbrev = payload.get("journal_abbrev") or None

            output_text = clean_bibtex_text(
                input_text,
                keep_fields=keep_fields,
                do_titlecase=do_titlecase,
                regen_keys=regen_keys,
                journal_abbrev=journal_abbrev,
            )

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps({"output": output_text}).encode("utf-8")
            )
        except Exception as exc:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                json.dumps({"error": str(exc)}).encode("utf-8")
            )


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), UIHandler)
    print("BibTeX UI running on http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
