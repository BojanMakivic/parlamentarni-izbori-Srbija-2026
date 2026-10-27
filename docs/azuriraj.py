"""Освежи docs из извоза: python docs/azuriraj.py. Не објављује и не комитује."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
FILES = ("index.html", "stations.csv", "results.csv", "manifest.json", "github-pages.zip")


def same_content(name, first, second):
    # Git may normalize CSV line endings; the exported rows remain identical.
    if name.endswith('.csv'):
        first = first.replace(b'\r\n', b'\n')
        second = second.replace(b'\r\n', b'\n')
    return first == second


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8')
    has_sources = (ROOT / 'izbori/report.py').is_file()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / ('dist/izbori-2026' if has_sources else 'docs'))
    parser.add_argument("--check", action="store_true", help="Само провери да docs одговара извозу.")
    args = parser.parse_args()
    source = args.source.resolve()
    destination = ROOT / "docs"
    if source == destination.resolve():
        if has_sources and not args.check:
            raise SystemExit("Извор и docs морају бити различите фасцикле.")
        args.check = True
    # In the full local workspace, rebuild presentation from canonical sources first.
    if not args.check and (ROOT / "izbori/report.py").is_file():
        sys.path.insert(0, str(ROOT))
        from izbori.report import refresh_report
        refresh_report(source)
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256((source / "index.html").read_bytes()).hexdigest() != manifest["html_sha256"]:
        raise SystemExit("HTML и manifest.json се не слажу. Поново направите извоз.")
    with zipfile.ZipFile(source / "github-pages.zip") as archive:
        if set(archive.namelist()) != set(FILES) - {"github-pages.zip"}:
            raise SystemExit("ZIP нема очекивани садржај.")
        if any(not same_content(name, archive.read(name), (source / name).read_bytes()) for name in archive.namelist()):
            raise SystemExit("ZIP и пратеће датотеке се не слажу.")
    if args.check:
        different = [name for name in FILES if not (destination / name).exists() or not same_content(name, (destination / name).read_bytes(), (source / name).read_bytes())]
        if different:
            raise SystemExit("docs није освежен: " + ", ".join(different))
        print("docs одговара извозу.")
        return
    destination.mkdir(exist_ok=True)
    for name in FILES:
        destinations = [destination]
        if source == (ROOT / "dist/izbori-2026").resolve():
            destinations.append(ROOT / "dist")
        for target in destinations:
            existing = target / name
            if existing.is_file() and same_content(name, existing.read_bytes(), (source / name).read_bytes()):
                continue
            temporary = target / (name + ".tmp")
            shutil.copyfile(source / name, temporary)
            temporary.replace(target / name)
    (destination / ".nojekyll").write_text("", encoding="utf-8")
    print("Освежен је docs. Сада можете да комитујете његов садржај. Подаци и бројчани резултати нису поново рачунати.")


if __name__ == "__main__":
    main()
