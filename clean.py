#!/usr/bin/env python3
"""BibTeX cleaning helpers used by the Django UI."""

from __future__ import annotations

import re
from typing import Iterable

import bibtexparser
from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase
from pylatexenc.latexencode import unicode_to_latex
from titlecase import titlecase


TYPE_SPECS = {
    "article": {
        "ENTRYTYPE": "article",
        "required_fields": {
            "author",
            "title",
            "journal",
            "year",
            "volume",
            "number",
            "pages",
        },
        "optional_fields":{
            "doi",
            "note"
        }
    },
    "pre-print": {
        "ENTRYTYPE": "article",
        "required_fields": {
            "author",
            "journal",
            "title",
            "doi",
            "year",
        },
        "optional_fields":{
            "note",
        },
    },
    "book": {
        "ENTRYTYPE": "book",
        "required_fields": {
            "author",
            "title",
            "publisher",
            "edition",
            "year",
        },
        "optional_fields":{
            "note",
        },
    },
    "chapter": {
        "ENTRYTYPE": "incollection",
        "required_fields": {
            "author",
            "title",
            "editor",
            "booktitle",
            "pages",
            "publisher",
            "year",
        },
        "optional_fields":{
            "volume",
            "note",
        },
    },
}

PROTECT_TITLE_TOKENS = [
    "PROTAC", "PROTACs",
    "BRD4", "BET", "CRBN",
    "Nrf2", "Keap1",
    "DNA", "RNA", "ATP",
    "X-ray", "SAR",
]

JOURNAL_ABBREV: dict[str, str] = {}

PAGE_DASH_RE = re.compile(r"\s*(?:–|—|-)\s*")
BRACED_GROUP_RE = re.compile(r"\{[^{}]*\}")
MATH_GROUP_RE = re.compile(r"\$(?:\\.|[^$])*\$")


def normalize_pages(pages: str) -> str:
    if not pages:
        return pages
    pages = pages.strip()
    if "--" in pages:
        return re.sub(r"\s*--\s*", "--", pages)
    parts = PAGE_DASH_RE.split(pages)
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}--{parts[1]}"
    return PAGE_DASH_RE.sub("--", pages)


def latexify(s: str) -> str:
    if not s:
        return s
    return unicode_to_latex(s, non_ascii_only=True)


def protect_tokens_in_title(raw_title: str, tokens: Iterable[str]) -> str:
    if not raw_title:
        return raw_title

    braced: list[str] = []

    def _stash(m):
        braced.append(m.group(0))
        return f"@@BRACED{len(braced) - 1}@@"

    tmp = BRACED_GROUP_RE.sub(_stash, raw_title)

    for tok in sorted(set(tokens), key=len, reverse=True):
        pattern = re.compile(rf"(?<!\w)({re.escape(tok)})(?!\w)")
        tmp = pattern.sub(r"{\1}", tmp)

    for i, grp in enumerate(braced):
        tmp = tmp.replace(f"@@BRACED{i}@@", grp)

    return tmp


def smart_titlecase(title: str) -> str:
    if not title:
        return title
    
    math: list[str] = []

    def _stash_math(m):
        math.append(m.group(0))
        return f"ZZMATH{len(math) - 1}ZZ"

    tmp = MATH_GROUP_RE.sub(_stash_math, title)
    tmp = protect_tokens_in_title(tmp, PROTECT_TITLE_TOKENS)
    tmp = titlecase(tmp)

    for i, grp in enumerate(math):
        tmp = tmp.replace(f"ZZMATH{i}ZZ", grp)

    return tmp


def abbreviate_journal(journal: str, journal_abbrev: dict[str, str] | None = None) -> str:
    if not journal:
        return journal

    overrides = journal_abbrev or JOURNAL_ABBREV
    if journal in overrides:
        return overrides[journal]

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
        return journal


def make_key(entry: dict) -> str:
    """
    firstauthorYYYY_ShortTitle
    Example: nowak2018_PlasticityInBinding
    """
    author = entry.get("author", "")
    year = entry.get("year", "")
    title = entry.get("title", "")

    first = author.split(" and ")[0].strip()
    if "," in first:
        last = first.split(",")[0].strip()
    else:
        last = first.split()[-1].strip() if first else "unknown"

    words = re.findall(r"[A-Za-z0-9]+", title)
    short = "".join(w.capitalize() for w in words[:4]) or "untitled"

    last = re.sub(r"[^A-Za-z0-9]+", "", last.lower()) or "unknown"
    year = re.sub(r"[^0-9]+", "", year) or "nd"

    return f"{last}{year}_{short}"


def normalize_entry(
    entry: dict,
    do_titlecase: bool,
    regen_keys: bool,
    journal_abbrev: dict[str, str] | None = None,
) -> dict:
    etype = entry.get("ENTRYTYPE", "").lower()

    if etype == "misc":
        doi = str(entry.get("doi", "")).lower()
        if "arxiv" in doi:
            etype = "pre-print"
            entry = dict(entry)
            entry["ENTRYTYPE"] = "article"
            entry["journal"] = "{{arXiv}}"
            entry["note"] = (entry.get("note", "") + " arxiv detected in DOI").strip()

    if etype == "article":
        spec = TYPE_SPECS["article"]
    elif etype == "book":
        spec = TYPE_SPECS["book"]
    elif etype == "incollection":
        spec = TYPE_SPECS["chapter"]
    elif etype == "pre-print":
        spec = TYPE_SPECS["pre-print"]
    else:
        entry["note"] = (entry.get("note", "") + " Could not detect document type").strip()
        return entry

    out = {
        "ENTRYTYPE": spec["ENTRYTYPE"],
        "ID": entry.get("ID", ""),
    }

    for k in spec["required_fields"].union(spec["optional_fields"]):
        if k in entry and str(entry[k]).strip():
            out[k] = str(entry[k]).strip()

    if "author" in out:
        out["author"] = latexify(out["author"])
    if "editor" in out:
        out["editor"] = latexify(out["editor"])
    if "title" in out:
        out["title"] = latexify(out["title"])
        if do_titlecase and etype != "book": # According to Jessica's example on the wiki the book title is not in title case
            out["title"] = smart_titlecase(out["title"])
    if "booktitle" in out:
        out["booktitle"] = latexify(out["booktitle"])
        if do_titlecase:
            out["booktitle"] = smart_titlecase(out["booktitle"])
    if "journal" in out:
        out["journal"] = latexify(abbreviate_journal(out["journal"], journal_abbrev=journal_abbrev))
    if "publisher" in out:
        out["publisher"] = latexify(out["publisher"])
    if "pages" in out:
        out["pages"] = normalize_pages(out["pages"])

    missing = [r for r in spec["required_fields"] if r not in out or not out[r].strip()]
    if missing:
        out["note"] = (out.get("note", "") + " " + f"[MISSING: {', '.join(missing)}]").strip()

    if regen_keys:
        out["ID"] = make_key(out)

    return out


def clean_bibtex_text(
    text: str,
    do_titlecase: bool = True,
    regen_keys: bool = False,
    journal_abbrev: dict[str, str] | None = None,
) -> str:
    db = bibtexparser.loads(text)
    new_db = BibDatabase()

    new_db.entries = [
        normalize_entry(
            e,
            do_titlecase=do_titlecase,
            regen_keys=regen_keys,
            journal_abbrev=journal_abbrev,
        )
        for e in db.entries
    ]

    writer = BibTexWriter()
    writer.indent = "\t"
    writer.order_entries_by = ("ID",)
    return writer.write(new_db)
