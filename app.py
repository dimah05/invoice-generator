"""
Générateur de facture - Étape 3 : version web avec Flask
------------------------------------------------------------
Au lieu de taper les infos dans le terminal, l'utilisateur remplit
un formulaire dans son navigateur et télécharge directement le PDF.

Pour lancer ce fichier chez toi :
    pip install flask reportlab
    python3 app.py
Puis ouvre ton navigateur sur : http://localhost:5000
"""

from flask import Flask, request, render_template_string, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from datetime import date, timedelta
import json
import os

app = Flask(__name__)

COULEUR_PRINCIPALE = colors.HexColor("#1F3B57")
COULEUR_GRISE = colors.HexColor("#666666")

FICHIER_COMPTEUR = "compteur.json"
FICHIER_HISTORIQUE = "factures.json"
DOSSIER_FACTURES = "factures_generees"

# On crée le dossier de sortie s'il n'existe pas encore
os.makedirs(DOSSIER_FACTURES, exist_ok=True)


# ---------------------------------------------------------------
# Le formulaire HTML. On le garde dans une simple chaîne de texte
# pour rester dans un seul fichier Python, facile à lancer.
# ---------------------------------------------------------------
FORMULAIRE_HTML = """
<!doctype html>
<html lang="fr">
<head>
    <meta charset="utf-8">
    <title>Générateur de facture</title>
    <style>
        body {
            font-family: Helvetica, Arial, sans-serif;
            background: #F2F4F7;
            display: flex;
            justify-content: center;
            padding-top: 60px;
        }
        .carte {
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            width: 380px;
        }
        h1 { font-size: 20px; color: #1F3B57; margin-bottom: 20px; }
        label { display: block; font-size: 13px; color: #666; margin-top: 14px; margin-bottom: 4px; }
        input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 14px;
            box-sizing: border-box;
        }
        button {
            margin-top: 24px;
            width: 100%;
            padding: 10px;
            background: #1F3B57;
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 15px;
            cursor: pointer;
        }
        button:hover { background: #16293e; }
    </style>
</head>
<body>
    <div class="carte">
        <h1>🧾 Générer une facture</h1>
        <form action="/generer" method="post">
            <label>Ton nom / entreprise</label>
            <input type="text" name="entreprise" required>

            <label>Nom du client</label>
            <input type="text" name="client" required>

            <label>Description de la prestation</label>
            <input type="text" name="description" required>

            <label>Montant (€)</label>
            <input type="text" name="montant" required>

            <button type="submit">Générer le PDF</button>
        </form>
    </div>
</body>
</html>
"""


def generer_numero_facture():
    """Numéro séquentiel F-ANNEE-0001, persisté dans compteur.json."""
    annee_actuelle = date.today().strftime("%Y")

    if os.path.exists(FICHIER_COMPTEUR):
        with open(FICHIER_COMPTEUR, "r", encoding="utf-8") as f:
            compteur = json.load(f)
    else:
        compteur = {"annee": annee_actuelle, "dernier_numero": 0}

    if compteur["annee"] != annee_actuelle:
        compteur = {"annee": annee_actuelle, "dernier_numero": 0}

    compteur["dernier_numero"] += 1
    with open(FICHIER_COMPTEUR, "w", encoding="utf-8") as f:
        json.dump(compteur, f, indent=2)

    return f"F-{annee_actuelle}-{str(compteur['dernier_numero']).zfill(4)}"


def enregistrer_dans_historique(numero, entreprise, client, description, montant, chemin_pdf):
    if os.path.exists(FICHIER_HISTORIQUE):
        with open(FICHIER_HISTORIQUE, "r", encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []

    historique.append({
        "numero": numero,
        "date_emission": date.today().strftime("%d/%m/%Y"),
        "entreprise": entreprise,
        "client": client,
        "description": description,
        "montant": montant,
        "fichier_pdf": chemin_pdf,
    })

    with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, indent=2, ensure_ascii=False)


def generer_pdf(entreprise, client, description, montant):
    numero = generer_numero_facture()
    chemin_pdf = os.path.join(DOSSIER_FACTURES, f"facture_{numero}.pdf")

    c = canvas.Canvas(chemin_pdf, pagesize=A4)
    largeur, hauteur = A4

    date_emission = date.today()
    date_echeance = date_emission + timedelta(days=30)

    # En-tête
    c.setFillColor(COULEUR_PRINCIPALE)
    c.rect(0, hauteur - 25 * mm, largeur, 25 * mm, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, hauteur - 17 * mm, "FACTURE")
    c.setFont("Helvetica", 11)
    c.drawRightString(largeur - 20 * mm, hauteur - 12 * mm, entreprise)
    c.drawRightString(largeur - 20 * mm, hauteur - 18 * mm, f"N° {numero}")

    # Bloc infos
    y = hauteur - 45 * mm
    c.setFillColor(COULEUR_GRISE)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "FACTURÉ À")
    c.drawString(120 * mm, y, "DATE D'ÉMISSION")
    c.drawString(120 * mm, y - 6 * mm, "DATE D'ÉCHÉANCE")
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(20 * mm, y - 7 * mm, client)
    c.drawString(160 * mm, y, date_emission.strftime("%d/%m/%Y"))
    c.drawString(160 * mm, y - 6 * mm, date_echeance.strftime("%d/%m/%Y"))

    # Tableau
    y_tableau = y - 25 * mm
    hauteur_ligne = 10 * mm
    c.setFillColor(COULEUR_PRINCIPALE)
    c.rect(20 * mm, y_tableau, largeur - 40 * mm, hauteur_ligne, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(23 * mm, y_tableau + 3.5 * mm, "DESCRIPTION")
    c.drawRightString(largeur - 23 * mm, y_tableau + 3.5 * mm, "MONTANT")

    y_ligne = y_tableau - hauteur_ligne
    c.setFillColor(colors.HexColor("#F5F5F5"))
    c.rect(20 * mm, y_ligne, largeur - 40 * mm, hauteur_ligne, fill=True, stroke=False)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(23 * mm, y_ligne + 3.5 * mm, description)
    c.drawRightString(largeur - 23 * mm, y_ligne + 3.5 * mm, f"{montant} EUR")

    # Total
    y_total = y_ligne - 12 * mm
    c.setStrokeColor(COULEUR_PRINCIPALE)
    c.setLineWidth(1)
    c.line(120 * mm, y_total + 6 * mm, largeur - 20 * mm, y_total + 6 * mm)
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(COULEUR_PRINCIPALE)
    c.drawString(120 * mm, y_total, "TOTAL À PAYER")
    c.drawRightString(largeur - 20 * mm, y_total, f"{montant} EUR")

    # Pied de page
    c.setFillColor(COULEUR_GRISE)
    c.setFont("Helvetica", 8)
    c.drawCentredString(largeur / 2, 15 * mm, f"Merci pour votre confiance — {entreprise}")

    c.save()
    enregistrer_dans_historique(numero, entreprise, client, description, montant, chemin_pdf)
    return chemin_pdf


# ---------------------------------------------------------------
# Routes Flask : ce sont les "pages" de notre mini site web
# ---------------------------------------------------------------

@app.route("/")
def accueil():
    """Affiche le formulaire quand on visite la page d'accueil."""
    return render_template_string(FORMULAIRE_HTML)


@app.route("/generer", methods=["POST"])
def generer():
    """Reçoit les données du formulaire et renvoie le PDF à télécharger."""
    entreprise = request.form["entreprise"]
    client = request.form["client"]
    description = request.form["description"]
    montant = request.form["montant"]

    chemin_pdf = generer_pdf(entreprise, client, description, montant)

    # send_file renvoie le fichier directement au navigateur,
    # qui proposera de le télécharger
    return send_file(chemin_pdf, as_attachment=True)


if __name__ == "__main__":
    # En local : port 5000 par défaut.
    # En ligne (Render...) : la plateforme impose son propre port via
    # la variable d'environnement PORT, donc on s'adapte automatiquement.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
