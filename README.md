# BibTeX Cleaner

A small command-line tool to normalize BibTeX `@article` entries into a
**journal-ready format**, suitable for chemistry, structural biology,
and computational science manuscripts.

The script is designed to clean Zotero-exported BibTeX files and enforce
consistent formatting rules commonly required by journals and supervisors.

---

## Features

- Converts Unicode characters to **BibTeX-safe LaTeX**
  (e.g. `Radosław → Rados{\l}aw`, `Käck → K{\"a}ck`)
- Normalizes page ranges to LaTeX standard `--`
- Optionally converts titles to **Title Case**
- Protects acronyms and chemistry tokens using `{}`  
  (e.g. `PROTAC`, `BRD4`, `Nrf2/Keap1`)
- Drops non-essential Zotero fields (`abstract`, `file`, `url`, etc.)
- Checks that required fields are present:
  - `author`
  - `title`
  - `journal`
  - `year`
  - `volume`
  - `pages`
- Optionally regenerates **short, descriptive citation keys**
- Leaves non-`@article` entries unchanged

---

## Repository Structure

```
.
├── clean.py        # Main normalization script
├── environment.yml     # Conda environment
├── requirements.txt    # pip environment (alternative)
├── README.md
```

---

## Installation

### Conda / Mamba (recommended)

```bash
conda env create -f environment.yml
conda activate bibtex-clean
```

or

```bash
mamba env create -f environment.yml
mamba activate bibtex-clean
```

### pip / virtualenv

```bash
python -m venv bibtex-env
source bibtex-env/bin/activate
pip install -r requirements.txt
```

---

## Usage

Basic usage:

```bash
python clean.py input.bib output.bib
```

Regenerate citation keys:

```bash
python clean.py input.bib output.bib --regen-keys
```

Disable automatic title casing:

```bash
python clean.py input.bib output.bib --no-titlecase
```

Keep additional fields (e.g. DOI and URL):

```bash
python clean.py input.bib output.bib --keep author title journal year volume pages doi url
```

---
## Local UI

Run the lightweight local UI (no extra dependencies required):

```bash
python ui_server.py
```

Then open `http://127.0.0.1:8000` in your browser. Paste your BibTeX,
adjust options, and the cleaned output updates automatically.

---
## Django App

If you want a shareable intranet app, run the Django server:

```bash
python manage.py runserver 0.0.0.0:8000
```

Then open `http://<your-lan-ip>:8000` in a browser on the same network.

---
## Static Site (JS)

For GitHub Pages or any static host, use the JS-only build in:

- `clean_my_bib/static_site/index.html`

Open the file directly in a browser, or host the `static_site` folder
on any static web server. Note: the static version keeps UTF-8 and does
not auto-abbreviate journal names unless you provide overrides.

---

## Citation Key Format

When `--regen-keys` is enabled, keys follow the pattern:

```
firstauthorYYYY_ShortTitle
```

Example:

```
nowak2018_PlasticityInBinding
```

You can customize the key generator in `make_key()` inside `clean.py`.

---

## Title Capitalization Rules

- Titles are converted to **Title Case**
- Protected tokens are wrapped in `{}` to prevent BibTeX from lowercasing:
  - Acronyms (`PROTAC`, `BRD4`, `DNA`)
  - Protein names (`Nrf2`, `Keap1`)
  - Technical terms (`X-ray`, `SAR`)
- Existing `{...}` in titles are always preserved

Protected tokens can be edited in:

```python
PROTECT_TITLE_TOKENS = [...]
```

---

## Journal Abbreviations

Journal name abbreviation is **not automatic**.

If desired, define abbreviations manually in `clean.py`:

```python
JOURNAL_ABBREV = {
    "Nature Chemical Biology": "Nat. Chem. Biol.",
    "Chemical Science": "Chem. Sci.",
}
```

This avoids incorrect or non-standard abbreviations and mirrors manual CAS usage.

---

## Limitations

- Does not infer journal abbreviations automatically
- Does not validate DOI correctness
- Assumes BibTeX (not BibLaTeX) conventions
- Does not reformat author name ordering beyond Unicode normalization

---

## Typical Workflow

```bash
# Export from Zotero
zotero → Export → BibTeX

# Clean bibliography
python clean.py library.bib library_clean.bib

# Use in LaTeX
\bibliography{library_clean}
```

---
