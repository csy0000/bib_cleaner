# BibTeX Cleaner (Django)

Minimal Django app for the BibTeX cleaner UI.

## Requirements

- Python 3.11

Install dependencies (conda or pip). Example with conda:

```bash
conda env create -f environment.yml
conda activate bibtex-clean
```

## Run

```bash
python manage.py migrate && python manage.py runserver 0.0.0.0:8888
```

Open:

```
http://<your-ip>:8888
```

## Project layout

- `manage.py`
- `bibtex_ui/`
- `ui_app/`
- `ui/`
- `environment.yml`
