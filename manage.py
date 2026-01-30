#!/usr/bin/env python3
"""Django entrypoint for the BibTeX cleaner UI."""

import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bibtex_ui.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed. Install it to run the web app."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
