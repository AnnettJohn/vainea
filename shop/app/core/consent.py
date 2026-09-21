"""Cookie-Einwilligung (Opt-in für nicht-essenzielle Cookies).

Siehe Pflichtenheft, DSGVO/Datenschutz: "Cookie-Consent mit Opt-in für
nicht-essenzielle Cookies (Analytics, Instagram-Embed)".

Grundgedanken:

- **Essenzielle Cookies laufen ohne Einwilligung.** Warenkorb, Login-Sitzung
  und das Einwilligungs-Cookie selbst sind für den vom Nutzer angeforderten
  Dienst erforderlich (§ 25 Abs. 2 Nr. 2 TDDDG) und deshalb einwilligungsfrei.
- **Alles andere erst nach aktivem Klick.** Kein vorangekreuztes Kästchen,
  kein "Weitersurfen gilt als Zustimmung".
- **Ablehnen muss so leicht sein wie Zustimmen.** Deshalb zwei
  gleichwertige Schaltflächen auf derselben Ebene, nicht eine auffällige
  Zustimmung und ein versteckter Link.
- **Ohne JavaScript bedienbar.** Der Banner ist ein normales Formular; die
  Entscheidung wird serverseitig als Cookie gesetzt.

Es gibt aktuell noch keine nicht-essenziellen Dienste im Shop. Die Mechanik
steht trotzdem, damit ein später eingebundener Dienst sie nur noch abfragen
muss, statt dass jemand sie unter Zeitdruck nachrüstet.
"""

from fastapi import Request

COOKIE_NAME = "vainea_consent"

# Nur essenzielle Cookies - die Voreinstellung, solange nichts gewählt wurde.
ESSENTIAL = "essential"
# Zusätzlich nicht-essenzielle Dienste (Analytics, eingebettete Inhalte).
ALL = "all"

GUELTIGE_WERTE = (ESSENTIAL, ALL)

# Ein halbes Jahr. Danach wird erneut gefragt - eine einmal erteilte
# Einwilligung soll nicht unbegrenzt fortwirken.
MAX_AGE = 60 * 60 * 24 * 182


def current_consent(request: Request) -> str | None:
    """Getroffene Entscheidung oder None, wenn noch keine vorliegt."""
    wert = request.cookies.get(COOKIE_NAME)
    return wert if wert in GUELTIGE_WERTE else None


def allows_optional(request: Request) -> bool:
    """Dürfen nicht-essenzielle Dienste geladen werden?

    Im Zweifel nein: ohne Entscheidung ist die Antwort False, nicht True.
    """
    return current_consent(request) == ALL
