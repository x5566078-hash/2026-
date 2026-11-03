"""Refresh the offline dashboard UI without recalculating the embedded data."""

from pathlib import Path
from shutil import copy2


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output/interactive/flight_explorer.html"
TEMPLATE = ROOT / "src/explorer_template.html"
APPLICATION = ROOT / "src/explorer_app.js"


def between(text: str, start: str, end: str) -> str:
    return text.split(start, 1)[1].split(end, 1)[0]


def main() -> None:
    previous = OUTPUT.read_text()
    library = between(previous, "</style><script>", "</script></head>")
    data = between(previous, "<script>const DATA=", ";</script><script>")
    html = (TEMPLATE.read_text()
            .replace("/*PLOTLY_LIBRARY*/", library)
            .replace("/*DATA_PAYLOAD*/", data)
            .replace("/*APPLICATION*/", APPLICATION.read_text()))
    if html.count("<script>const DATA=") != 1 or len(data) < 1_000_000:
        raise ValueError("Dashboard payload was not preserved")
    OUTPUT.write_text(html)
    for destination in [ROOT / "site/dist/index.html", ROOT.parent / "flight_dashboard_site/dist/index.html"]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        copy2(OUTPUT, destination)
        print(destination, destination.stat().st_size)


if __name__ == "__main__":
    main()
