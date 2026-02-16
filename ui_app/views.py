"""Views for the BibTeX cleaner UI."""

import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from clean import clean_bibtex_text


def index(request):
    return render(request, "index.html")


@csrf_exempt
def clean_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        input_text = payload.get("input", "")
        do_titlecase = bool(payload.get("titlecase", True))
        protect_titlecase = bool(payload.get("protectTitlecase", False))
        regen_keys = bool(payload.get("regen_keys", False))
        journal_abbrev = payload.get("journal_abbrev") or None

        output_text = clean_bibtex_text(
            input_text,
            do_titlecase=do_titlecase,
            protect_titlecase=protect_titlecase,
            regen_keys=regen_keys,
            journal_abbrev=journal_abbrev,
        )

        return JsonResponse({"output": output_text})
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=400)
