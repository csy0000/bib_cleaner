#!/usr/bin/env python3
"""
bib_clean.py — normalize BibTeX @article entries to a clean journal format.

Features:
- Drop unwanted fields; keep a minimal set
- Convert unicode to LaTeX (accents, special letters) for BibTeX safety
- Normalize pages: 505–516 or 505-516 -> 505--516
- Optional: titlecase titles while protecting tokens in {...}
- Optional: regenerate keys (citation identifiers)

Usage:
  python bib_clean.py in.bib out.bib
  python bib_clean.py in.bib out.bib --regen-keys
  python bib_clean.py in.bib out.bib --keep url doi
"""

from __future__ import annotations

import argparse
import re
from typing import Iterable

import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from pylatexenc.latexencode import unicode_to_latex
from titlecase import titlecase

from iso4 import abbreviate as iso4_abbreviate


# ----------------------------
# Configurable policy
# ----------------------------

DEFAULT_KEEP_FIELDS = [
    "author",
    "title",
    "journal",
    "year",
    "volume",
    "number",
    "pages",
    "doi",
]

# Words/tokens you want to preserve in titles exactly as written.
# Anything already inside {...} will be preserved as well.
PROTECT_TITLE_TOKENS = [
    "PROTAC", "PROTACs",
    "BRD4", "BET", "CRBN",
    "Nrf2", "Keap1",
    "DNA", "RNA", "ATP",
    "X-ray", "X-ray", "SAR",
]

# Optional journal abbreviation map. This overrides iso4 abbreviations.
JOURNAL_ABBREV = {
}


# ----------------------------
# Helpers
# ----------------------------

PAGE_DASH_RE = re.compile(r"\s*(?:–|—|-)\s*")  # en dash, em dash, hyphen
BRACED_GROUP_RE = re.compile(r"\{[^{}]*\}")    # simple brace groups (no nesting)


def normalize_pages(pages: str) -> str:
    """
    Turn page ranges into BibTeX-friendly double dash.
    Examples:
      '505–516' -> '505--516'
      '505-516' -> '505--516'
      '10800--10805' -> '10800--10805'
    """
    if not pages:
        return pages
    # If already contains '--', keep as is but normalize spaces
    pages = pages.strip()
    if "--" in pages:
        return re.sub(r"\s*--\s*", "--", pages)
    parts = PAGE_DASH_RE.split(pages)
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}--{parts[1]}"
    # fallback: just replace any single dash-like with --
    return PAGE_DASH_RE.sub("--", pages)


def latexify(s: str) -> str:
    """
    Convert unicode to LaTeX commands for BibTeX compatibility.
    Keeps common ASCII untouched.
    """
    if not s:
        return s
    return unicode_to_latex(s, non_ascii_only=True)


def protect_tokens_in_title(raw_title: str, tokens: Iterable[str]) -> str:
    """
    Ensure important tokens remain capitalized by wrapping them in {...},
    but do not double-wrap tokens already protected.
    """
    if not raw_title:
        return raw_title

    protected_title = raw_title

    # Temporarily remove existing { ... } groups so we don't modify inside them.
    braced = []
    def _stash(m):
        braced.append(m.group(0))
        return f"@@BRACED{len(braced)-1}@@"
    tmp = BRACED_GROUP_RE.sub(_stash, protected_title)

    for tok in sorted(set(tokens), key=len, reverse=True):
        # match token as a "word-ish" unit; allow punctuation neighbors
        pattern = re.compile(rf"(?<!\w)({re.escape(tok)})(?!\w)")
        tmp = pattern.sub(r"{\1}", tmp)

    # Restore braced groups
    for i, grp in enumerate(braced):
        tmp = tmp.replace(f"@@BRACED{i}@@", grp)

    return tmp


def smart_titlecase(title: str) -> str:
    """
    Title-case while preserving already-braced segments and protected tokens.
    Strategy:
      1) protect tokens with braces
      2) run titlecase() which respects braces reasonably well
    """
    if not title:
        return title
    t = protect_tokens_in_title(title, PROTECT_TITLE_TOKENS)
    # titlecase() can still lowercase inside braces if you're unlucky with punctuation,
    # but in practice it's decent; braces give you protection.
    return titlecase(t)


def abbreviate_journal(journal: str, journal_abbrev: dict[str, str] | None = None) -> str:
    if not journal:
        return journal

    overrides = journal_abbrev or JOURNAL_ABBREV

    # Manual overrides first
    if journal in overrides:
        return overrides[journal]

    # ISO4 fallback, with WordNet auto-install
    try:
        from iso4 import abbreviate as iso4_abbreviate
        return iso4_abbreviate(journal)
    except LookupError:
        import nltk
        nltk.download("wordnet", quiet=True)
        nltk.download("omw-1.4", quiet=True)
        from iso4 import abbreviate as iso4_abbreviate
        return iso4_abbreviate(journal)
    except Exception:
        # safest fallback: don't break bibliography build
        return journal

def make_key(entry: dict) -> str:
    """
    A simple key scheme: firstauthorYYYY_shorttitle
    Example: nowak2018_plasticityBindingSelectivity
    """
    author = entry.get("author", "")
    year = entry.get("year", "")
    title = entry.get("title", "")

    # first author's last name (BibTeX 'Last, First' or 'First Last')
    first = author.split(" and ")[0].strip()
    if "," in first:
        last = first.split(",")[0].strip()
    else:
        last = first.split()[-1].strip() if first else "unknown"

    # slugify title: take first ~4 words, alnum only
    words = re.findall(r"[A-Za-z0-9]+", title)
    short = "".join(w.capitalize() for w in words[:4]) or "untitled"

    last = re.sub(r"[^A-Za-z0-9]+", "", last.lower()) or "unknown"
    year = re.sub(r"[^0-9]+", "", year) or "nd"

    return f"{last}{year}_{short}"


# ----------------------------
# Main transform
# ----------------------------

def normalize_entry(
    e: dict,
    keep_fields: set[str],
    do_titlecase: bool,
    regen_keys: bool,
    journal_abbrev: dict[str, str] | None = None,
) -> dict:
    if e.get("ENTRYTYPE", "").lower() != "article":
        return e  # leave other types alone (you can extend later)

    out = {
        "ENTRYTYPE": "article",
        "ID": e.get("ID", ""),
    }

    # Keep desired fields if present
    for k in keep_fields:
        if k in e and e[k].strip():
            out[k] = e[k].strip()

    # Normalize content
    if "author" in out:
        out["author"] = latexify(out["author"])
    if "title" in out:
        out["title"] = latexify(out["title"])
        if do_titlecase:
            out["title"] = smart_titlecase(out["title"])

        # If you want to ensure specific letters stay capitalized, braces help.
        # Example: wrap first letter after colon if needed — optional:
        # out["title"] = re.sub(r":\s*([A-Za-z])", r": {\1}", out["title"])

    if "journal" in out:
        out["journal"] = latexify(abbreviate_journal(out["journal"], journal_abbrev=journal_abbrev))

    if "pages" in out:
        out["pages"] = normalize_pages(out["pages"])

    # Enforce required fields check (like your screenshot)
    required = ["author", "title", "journal", "year", "volume", "pages"]
    missing = [r for r in required if r not in out or not out[r].strip()]
    if missing:
        # Keep the entry but annotate (BibTeX ignores unknown fields; you can also print warnings)
        out["note"] = (out.get("note", "") + " " + f"[MISSING: {', '.join(missing)}]").strip()

    # Regenerate key if requested
    if regen_keys:
        out["ID"] = make_key(out)

    return out


def clean_bibtex_text(
    text: str,
    keep_fields: Iterable[str] = DEFAULT_KEEP_FIELDS,
    do_titlecase: bool = True,
    regen_keys: bool = False,
    journal_abbrev: dict[str, str] | None = None,
) -> str:
    db = bibtexparser.loads(text)
    new_db = BibDatabase()
    new_entries = []
    keep_fields_set = set(keep_fields)

    for e in db.entries:
        new_entries.append(
            normalize_entry(
                e,
                keep_fields=keep_fields_set,
                do_titlecase=do_titlecase,
                regen_keys=regen_keys,
                journal_abbrev=journal_abbrev,
            )
        )

    new_db.entries = new_entries

    writer = BibTexWriter()
    writer.indent = "\t"
    writer.order_entries_by = ("ID",)

    return writer.write(new_db)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile")
    ap.add_argument("outfile")
    ap.add_argument("--keep", nargs="*", default=DEFAULT_KEEP_FIELDS,
                    help="Fields to keep (default: a minimal journal-article set).")
    ap.add_argument("--no-titlecase", action="store_true", help="Disable title casing.")
    ap.add_argument("--regen-keys", action="store_true", help="Regenerate citation keys.")
    args = ap.parse_args()

    with open(args.infile, "r", encoding="utf-8") as f:
        input_text = f.read()

    with open(args.outfile, "w", encoding="utf-8") as f:
        f.write(
            clean_bibtex_text(
                input_text,
                keep_fields=args.keep,
                do_titlecase=(not args.no_titlecase),
                regen_keys=args.regen_keys,
            )
        )


if __name__ == "__main__":
    main()
