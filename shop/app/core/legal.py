"""Rendering der redaktionell gepflegten Rechtstexte.

Statt HTML aus dem Admin durchzureichen (und damit jedem Admin-Zugang
faktisch XSS auf allen Seiten zu erlauben) akzeptieren wir nur ein enges
Markdown-Subset und bauen das HTML selbst. Alles Eingegebene wird vorher
escaped, es kann also kein Markup "durchrutschen".

Unterstützt:
    ## Überschrift            -> <h2>
    ### Unterüberschrift      -> <h3>
    - Listenpunkt             -> <ul><li>
    Leerzeile trennt Absätze  -> <p>
    **fett**                  -> <strong>
    [Text](https://ziel)      -> <a> (nur http/https/mailto/tel)

Bewusst nicht unterstützt: rohes HTML, Bilder, Tabellen. Rechtstexte
brauchen das nicht, und jede weitere Syntax wäre weitere Angriffsfläche.
"""

import re
from html import escape

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_SAFE_SCHEMES = ("https://", "http://", "mailto:", "tel:", "/")


def _inline(text: str) -> str:
    """Fett und Links innerhalb eines bereits escapten Textes auflösen."""
    out = _BOLD.sub(r"<strong>\1</strong>", text)

    def link(match: re.Match) -> str:
        label, href = match.group(1), match.group(2)
        # &amp; entsteht durch das vorherige escape() und muss für die
        # Schema-Prüfung nicht rückgängig gemacht werden - relevant ist nur
        # der Anfang der URL.
        # `//evil.example` wäre protokollrelativ und damit extern, obwohl es
        # wie ein lokaler Pfad aussieht - deshalb gesondert ausschließen.
        if href.startswith("//") or not href.startswith(_SAFE_SCHEMES):
            return label
        rel = ' rel="noopener noreferrer"' if href.startswith(("http://", "https://")) else ""
        return f'<a href="{href}"{rel}>{label}</a>'

    return _LINK.sub(link, out)


def render_legal_body(body: str) -> str:
    """Markdown-Subset -> HTML. Der Rückgabewert ist sicher und darf im
    Template mit `| safe` ausgegeben werden."""
    html: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            html.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            html.append("<p>" + "<br>".join(paragraph) + "</p>")
            paragraph.clear()

    for raw_line in (body or "").splitlines():
        line = _inline(escape(raw_line.strip()))

        if not line:
            flush_paragraph()
            flush_list()
        elif line.startswith("### "):
            flush_paragraph()
            flush_list()
            html.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("## "):
            flush_paragraph()
            flush_list()
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:])
        else:
            flush_list()
            paragraph.append(line)

    flush_paragraph()
    flush_list()
    return "".join(html)


# Eckige Klammern, die KEIN Markdown-Link sind (dort folgt direkt "(").
_PLATZHALTER = re.compile(r"\[[^\]\n]{2,}\](?!\()")


def find_placeholders(body: str) -> list[str]:
    """Offene Platzhalter in einem Rechtstext finden.

    Die Entwürfe enthalten Angaben wie [Firmenname] und Hinweise der Form
    [RECHTLICH PRÜFEN: ...]. Ein Text mit solchen Stellen darf nicht
    veröffentlicht werden - im günstigsten Fall ist er peinlich, im
    ungünstigsten ein Abmahngrund, weil Pflichtangaben fehlen.

    Markdown-Links wie [Text](https://...) sind keine Platzhalter.
    """
    gefunden = _PLATZHALTER.findall(body or "")
    # Reihenfolge erhalten, Dubletten entfernen.
    return list(dict.fromkeys(gefunden))
