"""Rechtstexte: Renderer, Platzhalter-Erkennung und Veröffentlichungssperre.

Der Renderer bekommt seinen Inhalt aus dem Admin. Er darf deshalb unter
keinen Umständen HTML durchreichen - sonst hätte jeder Admin-Zugang faktisch
XSS auf allen öffentlichen Seiten.
"""

import pytest

from app.core.legal import find_placeholders, render_legal_body
from scripts.legal_texts import LEGAL_PAGES


class TestRenderer:
    def test_ueberschriften_und_absaetze(self):
        html = render_legal_body("## Titel\n\nEin Absatz.\n\n### Unterpunkt")
        assert html == "<h2>Titel</h2><p>Ein Absatz.</p><h3>Unterpunkt</h3>"

    def test_liste(self):
        assert render_legal_body("- eins\n- zwei") == "<ul><li>eins</li><li>zwei</li></ul>"

    def test_fett(self):
        assert "<strong>wichtig</strong>" in render_legal_body("Das ist **wichtig**.")

    def test_html_wird_escaped(self):
        """Der entscheidende Test: eingegebenes Markup darf nicht wirken."""
        html = render_legal_body('<script>alert("x")</script>')
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_html_in_ueberschrift_wird_escaped(self):
        html = render_legal_body("## <img src=x onerror=alert(1)>")
        assert "<img" not in html
        assert "&lt;img" in html

    @pytest.mark.parametrize(
        "ziel",
        ["https://example.org", "http://example.org", "mailto:a@b.de", "tel:+49123", "/shop"],
    )
    def test_erlaubte_linkziele(self, ziel):
        html = render_legal_body(f"siehe [hier]({ziel})")
        assert f'href="{ziel}"' in html

    @pytest.mark.parametrize(
        "ziel",
        ["javascript:alert(1)", "data:text/html;base64,x", "//fremde.example"],
    )
    def test_gefaehrliche_linkziele_werden_zu_text(self, ziel):
        """javascript:, data: und protokollrelative Ziele durften nie zu
        einem anklickbaren Link werden."""
        html = render_legal_body(f"siehe [hier]({ziel})")
        assert "<a " not in html
        assert "hier" in html

    def test_anfuehrungszeichen_brechen_attribut_nicht_auf(self):
        html = render_legal_body('[x](https://a.example/?q=")')
        assert 'href="https://a.example/?q=&quot;"' in html or "<a " not in html


class TestPlatzhalter:
    def test_findet_firmenangaben_und_pruefhinweise(self):
        gefunden = find_placeholders("Vertragspartner ist [Firmenname]. [RECHTLICH PRÜFEN: Sitz klären]")
        assert gefunden == ["[Firmenname]", "[RECHTLICH PRÜFEN: Sitz klären]"]

    def test_markdown_link_ist_kein_platzhalter(self):
        assert find_placeholders("siehe [unsere AGB](https://vainea.de/legal/agb)") == []

    def test_leerer_text(self):
        assert find_placeholders("") == []

    def test_dubletten_nur_einmal(self):
        assert find_placeholders("[Firmenname] und [Firmenname]") == ["[Firmenname]"]

    @pytest.mark.parametrize("seite", LEGAL_PAGES, ids=lambda s: s["slug"])
    def test_entwuerfe_enthalten_platzhalter(self, seite):
        """Absicherung gegen ein Versehen: Die mitgelieferten Fassungen sind
        Entwürfe. Enthielte einer keine Platzhalter mehr, wäre er entweder
        fertig geprüft (dann gehört er nicht mehr hierher) oder jemand hat
        versehentlich Pflichtangaben gelöscht."""
        assert find_placeholders(seite["body"]), seite["slug"]


class TestVeroeffentlichungssperre:
    """Die Sperre im Admin (app/admin.py) verhindert, dass ein Text mit
    offenen Platzhaltern veröffentlicht wird. Ein Impressum mit
    [Firmenname] wäre nicht bloß unfertig, sondern ein Verstoß gegen die
    Impressumspflicht."""

    async def test_veroeffentlichen_mit_platzhaltern_scheitert(self):
        from app.admin import LegalPageAdmin

        with pytest.raises(ValueError, match="Platzhalter"):
            await LegalPageAdmin.on_model_change(
                LegalPageAdmin, {"is_published": True, "body": "Wir sind [Firmenname]."}, None, False, None
            )

    async def test_speichern_ohne_veroeffentlichen_ist_erlaubt(self):
        from app.admin import LegalPageAdmin

        await LegalPageAdmin.on_model_change(
            LegalPageAdmin, {"is_published": False, "body": "Wir sind [Firmenname]."}, None, False, None
        )

    async def test_veroeffentlichen_ohne_platzhalter_ist_erlaubt(self):
        from app.admin import LegalPageAdmin

        await LegalPageAdmin.on_model_change(
            LegalPageAdmin, {"is_published": True, "body": "Wir sind die Muster GmbH."}, None, False, None
        )
