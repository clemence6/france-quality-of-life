"""Build the English static pages from French sources and the reviewed catalogue.

python scripts/build_english.py
The shared CSS, public data and vendor assets are never duplicated.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]


def catalogue():
    entries = {}
    for number, line in enumerate((ROOT / "translations/en.tsv").read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        source, target = line.split("|||", 1)
        if source in entries and entries[source] != target:
            raise ValueError(f"Conflicting translation on line {number}: {source}")
        entries[source] = target
    return entries


def build():
    entries = catalogue()
    # One substitution pass prevents translations from being translated again.
    matcher = re.compile("|".join(re.escape(s) for s in sorted(entries, key=len, reverse=True)))
    destination = ROOT / "web/en"
    destination.mkdir(exist_ok=True)
    risk_translations = json.loads((ROOT / "translations/risks.en.json").read_text(encoding="utf-8"))
    for name in ("index.html", "app.js", "dashboard.js"):
        text = (ROOT / "web" / name).read_text(encoding="utf-8")
        text = matcher.sub(lambda match: entries[match.group()], text)
        if name == "index.html":
            text = text.replace('<html lang="fr">', '<html lang="en">')
            text = text.replace('<head>', '<head>\n<base href="../">')
            text = text.replace('src="app.js?', 'src="en/app.js?').replace('src="dashboard.js?', 'src="en/dashboard.js?')
        if name == "app.js":
            text = text.replace('"fr-FR"', '"en-GB"').replace('"date inconnue"', '"unknown date"')
            text = text.replace('function riskLabel(value) { return value; }',
                                'const ENGLISH_RISKS = ' + json.dumps(risk_translations, ensure_ascii=False) + ';\n'
                                'function riskLabel(value) { return ENGLISH_RISKS[value] || `Official French label: ${value}`; }')
        (destination / name).write_text(text, encoding="utf-8")
    print("English version generated: web/en/ (3 files)")


if __name__ == "__main__":
    build()
