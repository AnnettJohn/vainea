"""Ausgangstexte für die Rechtsseiten (Impressum, AGB, Widerruf, Datenschutz).

Diese Fassungen sind ENTWÜRFE. Alle unternehmensspezifischen Angaben stehen
als Platzhalter in eckigen Klammern, Stellen mit Klärungsbedarf sind mit
[RECHTLICH PRÜFEN: ...] markiert. Vor der Veröffentlichung müssen sie von
einer auf E-Commerce spezialisierten Kanzlei geprüft werden.

Die Texte landen über scripts/seed.py einmalig in der Datenbank und werden
danach im Admin gepflegt - der Seed überschreibt sie nicht mehr. Formatierung
ist das Markdown-Subset aus app/core/legal.py (## / ### / - / **fett** /
Absätze durch Leerzeilen).

`is_published` steht bewusst auf False: solange Platzhalter enthalten sind,
zeigt die öffentliche Seite einen Hinweis statt eines halbfertigen Rechtstexts.
Das Veröffentlichen mit verbliebenen Platzhaltern verhindert zusätzlich eine
Prüfung im Admin (siehe app/admin.py).
"""

PLATZHALTER_MUSTER = ("[RECHTLICH PRÜFEN", "[Firmenname", "[Betrag", "[X")

IMPRESSUM = """## Angaben gemäß § 5 Digitale-Dienste-Gesetz (DDG)

[RECHTLICH PRÜFEN: Bei Sitz oder Marktauftritt in Österreich zusätzlich § 5 ECG / Mediengesetz, bei Bezug zur Schweiz Art. 3 lit. s UWG beachten.]

[Firmenname], [Rechtsform]
[Straße, Hausnummer]
[PLZ, Ort]
[Land]

Vertreten durch: [Name der vertretungsberechtigten Person(en)]

## Kontakt

- Telefon: [Telefonnummer]
- E-Mail: [E-Mail-Adresse]

## Registereintrag

- Eintragung im [Handelsregister/Firmenbuch]
- Registergericht: [Registergericht]
- Registernummer: [Registernummer]

Umsatzsteuer-Identifikationsnummer gemäß § 27a UStG: [USt-IdNr.]

[RECHTLICH PRÜFEN: Falls eine berufsrechtliche Zulassung oder Aufsichtsbehörde einschlägig ist, hier ergänzen.]

## Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV

[Name, Anschrift wie oben]

## Online-Streitbeilegung

Plattform der EU-Kommission zur Online-Streitbeilegung: [ec.europa.eu/consumers/odr](https://ec.europa.eu/consumers/odr/)

[RECHTLICH PRÜFEN: Hinweis- und Teilnahmepflicht an Verbraucherschlichtung aktuell prüfen, inkl. Sonderregeln für die Schweiz, wo die EU-OS-Plattform nicht zuständig ist.]"""


AGB = """## § 1 Geltungsbereich und Vertragspartner

(1) Für alle Bestellungen über den Online-Shop unter [Domain, z. B. www.vainea.de] gelten die nachfolgenden Allgemeinen Geschäftsbedingungen in ihrer bei Bestellung gültigen Fassung.

(2) Vertragspartner ist [Firmenname, Rechtsform, Anschrift wie im Impressum].

(3) Verbraucher im Sinne dieser Bedingungen ist jede natürliche Person, die ein Rechtsgeschäft zu Zwecken abschließt, die überwiegend weder ihrer gewerblichen noch ihrer selbständigen beruflichen Tätigkeit zugerechnet werden können.

(4) Der Shop liefert derzeit ausschließlich an Kundinnen und Kunden mit Lieferadresse in Deutschland, Österreich und der Schweiz (siehe § 4).

## § 2 Vertragsschluss

(1) Die Darstellung der Produkte im Online-Shop stellt kein rechtlich bindendes Angebot dar, sondern eine unverbindliche Aufforderung an die Kundin oder den Kunden, ein Angebot abzugeben (invitatio ad offerendum).

(2) Durch Anklicken des Bestellbuttons („[Bezeichnung des Bestellbuttons, z. B. zahlungspflichtig bestellen]“) gibt die Kundin oder der Kunde ein verbindliches Angebot zum Abschluss eines Kaufvertrags über die im Warenkorb enthaltenen Waren ab.

(3) Der Vertrag kommt zustande, wenn [Firmenname] das Angebot durch eine gesonderte Bestellbestätigung per E-Mail annimmt oder die Ware ohne vorherige ausdrückliche Annahmeerklärung versendet. Die automatische Eingangsbestätigung unmittelbar nach der Bestellung stellt noch keine Vertragsannahme dar.

(4) Der Vertragstext wird nicht gesondert gespeichert und ist nach Abschluss der Bestellung für die Kundin oder den Kunden nicht mehr zugänglich. [RECHTLICH PRÜFEN: Falls eine Speicherung oder Zusendung des Vertragstexts vorgesehen ist, Formulierung entsprechend anpassen.]

## § 3 Preise, Versandkosten und Zahlung

(1) Die angegebenen Preise sind Endpreise und enthalten die gesetzliche Umsatzsteuer. [RECHTLICH PRÜFEN: Bei Lieferungen in die Schweiz können zusätzlich Einfuhrabgaben, Zoll und Schweizer Mehrwertsteuer anfallen, die von der Kundin bzw. dem Kunden zu tragen sind - Formulierung und Zuständigkeit (DDP/DAP) rechtlich klären.]

(2) Es gelten folgende Versandzonen und -kosten:

- **Zone 1, Deutschland:** [Betrag] €, versandkostenfrei ab [Betrag] €
- **Zone 2, Österreich:** [Betrag] €, versandkostenfrei ab [Betrag] €
- **Zone 3, Schweiz:** [Betrag] CHF, versandkostenfrei ab [Betrag] CHF

Der jeweils gültige Versandkostenbetrag wird der Kundin oder dem Kunden vor Abschluss der Bestellung im Warenkorb sowie im Checkout angezeigt.

(3) Die Zahlung erfolgt über den Zahlungsdienstleister Mollie B.V., Keizersgracht 313, 1016 EE Amsterdam, Niederlande. Folgende Zahlungsarten stehen zur Verfügung: [z. B. iDEAL, SEPA-Lastschrift, Bancontact, Kreditkarte - tatsächlich angebotene Methoden ergänzen].

(4) Bei Zahlung per SEPA-Lastschrift erteilt die Kundin bzw. der Kunde ein SEPA-Lastschriftmandat; die Abbuchung erfolgt nach Vertragsschluss. [RECHTLICH PRÜFEN: Mandatsreferenz- und Vorabankündigungspflichten nach SEPA-Verordnung.]

(5) Der Kaufpreis gilt erst mit Bestätigung der erfolgreichen Zahlung durch Mollie als beglichen; erst danach gilt die Bestellung als final angenommen (siehe § 2 Abs. 3).

## § 4 Lieferung und Bestandsreservierung

(1) Die Lieferung erfolgt an die von der Kundin oder dem Kunden im Bestellprozess angegebene Lieferadresse in Deutschland, Österreich oder der Schweiz.

(2) Die Lieferzeit beträgt, sofern nicht anders angegeben, [X] Werktage innerhalb Deutschlands und Österreichs sowie [X] Werktage in die Schweiz ab Zahlungseingang.

(3) Das Hinzufügen eines Artikels zum Warenkorb stellt keine verbindliche Reservierung dar. Artikel im Warenkorb werden für die Dauer des Checkout-Vorgangs von maximal [X] Minuten vorgehalten; danach werden sie wieder für andere Kundinnen und Kunden freigegeben. Eine endgültige Reservierung des Bestands erfolgt erst mit Abschluss der Bestellung gemäß § 2 Abs. 3.

(4) Ist ein bestellter Artikel trotz Bestellbestätigung nicht verfügbar, weil er zwischenzeitlich vergriffen ist, wird die Kundin oder der Kunde unverzüglich informiert; bereits geleistete Zahlungen werden in diesem Fall unverzüglich erstattet. [RECHTLICH PRÜFEN: Selbstbelieferungsvorbehalt rechtssicher formulieren.]

## § 5 Rabattcodes

(1) [Firmenname] kann zeitlich befristete Rabattcodes ausgeben, die zu einem Nachlass auf den Warenwert in Höhe eines festen Betrags oder eines Prozentsatzes berechtigen.

(2) Rabattcodes sind nur innerhalb des angegebenen Gültigkeitszeitraums und, sofern angegeben, nur ab einem Mindestbestellwert von [Betrag] € einlösbar.

(3) Pro Bestellung ist die Einlösung nur eines Rabattcodes möglich, sofern nichts anderes angegeben ist. Rabattcodes sind nicht mit anderen Rabattaktionen kombinierbar, sofern nichts anderes angegeben ist.

(4) Eine Barauszahlung des Rabattbetrags ist ausgeschlossen. Rabattcodes gelten nicht rückwirkend für bereits abgeschlossene Bestellungen.

(5) Der Rabatt wird auf den Warenwert vor Versandkosten angerechnet. Für die Berechnung einer etwaigen Versandkostenfreigrenze ist der Warenwert vor Anwendung des Rabattcodes maßgeblich.

(6) Bei vollständigem oder teilweisem Widerruf einer Bestellung, für die ein Rabattcode eingelöst wurde, wird der Rabatt anteilig auf die zurückgesendete Ware angerechnet. [RECHTLICH PRÜFEN: Erstattungslogik bei Teilwiderruf im Detail festlegen.]

## § 6 Eigentumsvorbehalt

Die gelieferte Ware bleibt bis zur vollständigen Bezahlung Eigentum von [Firmenname].

## § 7 Gewährleistung

(1) Es gelten die gesetzlichen Mängelrechte. [RECHTLICH PRÜFEN: Verjährungsfristen und ggf. abweichende Regelungen für Gebrauchtwaren, Garantien Dritter sowie länderspezifische Abweichungen in Österreich und der Schweiz - in der Schweiz gilt grundsätzlich das Obligationenrecht mit eigenen, kürzeren Fristen.]

(2) Informationen zu einer etwaigen Herstellergarantie finden sich, sofern vorhanden, in der jeweiligen Produktbeschreibung.

## § 8 Haftung

(1) [Firmenname] haftet unbeschränkt für Vorsatz und grobe Fahrlässigkeit sowie nach den Vorschriften des Produkthaftungsgesetzes sowie bei Verletzung von Leben, Körper oder Gesundheit.

(2) Für die leicht fahrlässige Verletzung wesentlicher Vertragspflichten (Kardinalpflichten) haftet [Firmenname] der Höhe nach beschränkt auf den bei Vertragsschluss vorhersehbaren, vertragstypischen Schaden. [RECHTLICH PRÜFEN: Haftungsbeschränkung an die jeweils anwendbare Rechtsordnung anpassen; Wirksamkeit gegenüber Verbraucherinnen und Verbrauchern in Österreich und der Schweiz separat prüfen.]

(3) Im Übrigen ist die Haftung ausgeschlossen.

## § 9 Schlussbestimmungen

(1) Es gilt das Recht der Bundesrepublik Deutschland unter Ausschluss des UN-Kaufrechts. [RECHTLICH PRÜFEN: Für Verbraucherinnen und Verbraucher mit gewöhnlichem Aufenthalt in Österreich oder der Schweiz bleibt zwingendes Verbraucherschutzrecht des jeweiligen Wohnsitzstaats unberührt (Art. 6 Rom I-VO); Formulierung entsprechend absichern.]

(2) Gerichtsstand für Streitigkeiten mit Kaufleuten ist [Gerichtsstand]. [RECHTLICH PRÜFEN: Gerichtsstandsklauseln gegenüber Verbraucherinnen und Verbrauchern sind regelmäßig unwirksam und müssen entsprechend eingeschränkt formuliert werden.]

(3) Sollten einzelne Bestimmungen dieser AGB unwirksam sein, bleibt die Wirksamkeit der übrigen Bestimmungen hiervon unberührt."""


WIDERRUF = """[RECHTLICH PRÜFEN: Das gesetzliche Widerrufsrecht nach EU-Verbraucherrechterichtlinie gilt für Kundinnen und Kunden mit Wohnsitz in Deutschland und Österreich. Für Kundinnen und Kunden mit Wohnsitz in der Schweiz besteht mangels entsprechender gesetzlicher Grundlage regelmäßig kein gesetzliches Widerrufsrecht beim Fernabsatzkauf; ob und in welchem Umfang ein freiwilliges Rückgaberecht gewährt wird, sollte anwaltlich geklärt und ggf. gesondert ausgewiesen werden.]

## Widerrufsrecht

Verbraucherinnen und Verbraucher haben das Recht, binnen vierzehn Tagen ohne Angabe von Gründen diesen Vertrag zu widerrufen.

Die Widerrufsfrist beträgt vierzehn Tage ab dem Tag, an dem die Kundin oder der Kunde oder ein von ihr bzw. ihm benannter Dritter, der nicht der Beförderer ist, die letzte Ware in Besitz genommen hat.

Um das Widerrufsrecht auszuüben, muss die Kundin oder der Kunde [Firmenname], [Anschrift], E-Mail: [E-Mail-Adresse], mittels einer eindeutigen Erklärung (z. B. per Post versandter Brief oder E-Mail) über den Entschluss, diesen Vertrag zu widerrufen, informieren. Zur Wahrung der Widerrufsfrist reicht es aus, die Mitteilung über die Ausübung des Widerrufsrechts vor Ablauf der Widerrufsfrist abzusenden.

## Folgen des Widerrufs

Im Falle eines wirksamen Widerrufs sind die beiderseits empfangenen Leistungen zurückzugewähren. [Firmenname] hat alle Zahlungen, die von der Kundin oder dem Kunden geleistet wurden, einschließlich der Lieferkosten (mit Ausnahme zusätzlicher Kosten, die sich daraus ergeben, dass eine andere Art der Lieferung als die günstigste angebotene Standardlieferung gewählt wurde), unverzüglich und spätestens binnen vierzehn Tagen ab dem Tag zurückzuzahlen, an dem die Mitteilung über den Widerruf eingegangen ist. Für diese Rückzahlung wird dasselbe Zahlungsmittel eingesetzt, das bei der ursprünglichen Zahlung über Mollie verwendet wurde, sofern nicht ausdrücklich etwas anderes vereinbart wurde.

[Firmenname] kann die Rückzahlung verweigern, bis die Waren zurückerhalten wurden oder bis die Kundin bzw. der Kunde den Nachweis erbracht hat, dass die Waren zurückgesandt wurden, je nachdem, welches der frühere Zeitpunkt ist.

Die Kundin oder der Kunde hat die Waren unverzüglich und in jedem Fall spätestens binnen vierzehn Tagen ab dem Tag, an dem sie den Widerruf mitteilt, an [Firmenname], [Retourenadresse] zurückzusenden. Die unmittelbaren Kosten der Rücksendung trägt [die Kundin/der Kunde - bitte festlegen].

## Muster-Widerrufsformular

(Wenn Sie den Vertrag widerrufen wollen, füllen Sie bitte dieses Formular aus und senden Sie es zurück.)

An [Firmenname], [Anschrift], [E-Mail-Adresse]:

Hiermit widerrufe(n) ich/wir den von mir/uns abgeschlossenen Vertrag über den Kauf der folgenden Waren:

- Bestellt am / erhalten am:
- Name der Verbraucherin/des Verbrauchers:
- Anschrift der Verbraucherin/des Verbrauchers:
- Datum:"""


DATENSCHUTZ = """## 1. Verantwortlicher

Verantwortlich für die Datenverarbeitung im Sinne der DSGVO ist [Firmenname, Anschrift, E-Mail-Adresse wie im Impressum].

## 2. Datenverarbeitung bei Bestellung

Im Rahmen des Bestellvorgangs erheben und verarbeiten wir die zur Vertragserfüllung notwendigen Daten (Name, Liefer- und Rechnungsadresse, E-Mail-Adresse, ggf. Telefonnummer, Bestell- und Zahlungsdaten). Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO (Vertragserfüllung).

## 3. Warenkorb und Bestandsreservierung

Zur Bereitstellung des Warenkorbs, auch für Bestellungen ohne Kundenkonto, setzen wir ein Cookie bzw. eine vergleichbare Kennung ein, die den Warenkorbinhalt und die vorübergehende Artikelreservierung (siehe AGB § 4) einem Browser zuordnet. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b bzw. lit. f DSGVO (Vertragsanbahnung, berechtigtes Interesse an einem funktionsfähigen Bestellprozess).

## 4. Zahlungsabwicklung über Mollie

Für die Zahlungsabwicklung nutzen wir den Zahlungsdienstleister Mollie B.V., Keizersgracht 313, 1016 EE Amsterdam, Niederlande. Je nach gewählter Zahlungsart übermittelt Mollie die zur Zahlungsabwicklung erforderlichen Daten (u. a. Name, Zahlungsbetrag, Kontoinformationen) an beteiligte Kreditinstitute und Zahlungsnetzwerke. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO.

[RECHTLICH PRÜFEN: Auftragsverarbeitungsvertrag mit Mollie abschließen bzw. dessen Standardvertrag prüfen; ggf. Drittlandtransfer außerhalb der EU und des EWR durch Mollie-Subprozessoren identifizieren und Übermittlungsgrundlage (z. B. Standardvertragsklauseln) ergänzen.]

## 5. Rabattcodes

Bei Einlösung eines Rabattcodes verarbeiten wir den verwendeten Code sowie die zugehörige Bestellung, um die Gültigkeit und Nutzungshäufigkeit zu prüfen. Rechtsgrundlage ist Art. 6 Abs. 1 lit. b DSGVO.

## 6. Empfänger und Weitergabe

Zur Vertragsabwicklung geben wir Daten an folgende Empfänger weiter: den Zahlungsdienstleister Mollie, mit dem Versand beauftragte Logistikunternehmen (für Lieferungen nach Deutschland, Österreich und in die Schweiz) sowie ggf. Steuerberatung und Hosting-Dienstleister. [Empfänger konkret benennen.]

## 7. Speicherdauer

Bestelldaten speichern wir für die Dauer der handels- und steuerrechtlichen Aufbewahrungsfristen (in der Regel [6/10] Jahre). Warenkorb- bzw. Reservierungsdaten ohne abgeschlossene Bestellung werden nach [X Tagen/Stunden] automatisch gelöscht.

## 8. Cookies und Tracking

[RECHTLICH PRÜFEN und ergänzen: Auflistung aller eingesetzten Cookies und Tools (Analytics, Instagram-Embed o. Ä.) mit Einwilligungsstatus über ein Cookie-Consent-Tool, getrennt nach technisch notwendigen und einwilligungspflichtigen Diensten.]

## 9. Rechte der betroffenen Personen

Kundinnen und Kunden haben das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung, Datenübertragbarkeit sowie Widerspruch gegen die Verarbeitung, jeweils unter den gesetzlichen Voraussetzungen der Art. 15 bis 21 DSGVO. Zudem besteht ein Beschwerderecht bei der zuständigen Datenschutzaufsichtsbehörde: [zuständige Aufsichtsbehörde].

[RECHTLICH PRÜFEN: Für Kundinnen und Kunden in der Schweiz gilt ergänzend das Schweizer Datenschutzgesetz (DSG); Anwendbarkeit und ggf. Benennung einer Vertretung in der Schweiz prüfen (Art. 14 DSG).]"""


LEGAL_PAGES = [
    {"slug": "impressum", "title": "Impressum", "body": IMPRESSUM, "sort_order": 1},
    {"slug": "datenschutz", "title": "Datenschutzerklärung", "body": DATENSCHUTZ, "sort_order": 2},
    {"slug": "agb", "title": "Allgemeine Geschäftsbedingungen", "body": AGB, "sort_order": 3},
    {"slug": "widerruf", "title": "Widerrufsbelehrung", "body": WIDERRUF, "sort_order": 4},
]
