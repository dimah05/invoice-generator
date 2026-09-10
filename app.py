"""
Générateur de facture - Étape 4 : logo, devise, mise en page pro
---------------------------------------------------------------
Nouveautés :
- Upload du logo du client (affiché sur la facture)
- Menu déroulant pour choisir la devise ($, €, £)
- Mise en page inspirée d'un vrai modèle de facture pro
  (n° facture, date, ID client, modalités, bill to / ship to,
  tableau multi-lignes, sous-total, taxe, total)

Pour lancer chez toi :
    pip install flask reportlab
    python3 app.py
Puis : http://localhost:5000
"""

from flask import Flask, request, render_template_string, send_file
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from datetime import date, timedelta
import json
import os
import io

app = Flask(__name__)

COULEUR_PRINCIPALE = colors.HexColor("#0070C0")
COULEUR_GRISE = colors.HexColor("#666666")
COULEUR_CLAIRE = colors.HexColor("#D9E2F1")

FICHIER_COMPTEUR = "compteur.json"
FICHIER_HISTORIQUE = "factures.json"
DOSSIER_FACTURES = "factures_generees"

os.makedirs(DOSSIER_FACTURES, exist_ok=True)

# Symboles affichés selon la devise choisie dans le formulaire
SYMBOLES_DEVISE = {"USD": "$", "EUR": "€", "GBP": "£"}


# ---------------------------------------------------------------
# Formulaire HTML avec upload de logo, devise, et lignes dynamiques
# ---------------------------------------------------------------
FORMULAIRE_HTML = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Invoice Generator</title>
    <style>
        body { font-family: Helvetica, Arial, sans-serif; background: #F2F4F7; padding: 40px; }
        .carte {
            background: white; padding: 32px; border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
            max-width: 700px; margin: 0 auto;
        }
        h1 { font-size: 20px; color: #1F3B57; margin-bottom: 24px; }
        h2 { font-size: 14px; color: #1F3B57; margin-top: 28px; margin-bottom: 10px; border-bottom: 2px solid #eee; padding-bottom: 6px; }
        label { display: block; font-size: 12px; color: #666; margin-top: 10px; margin-bottom: 3px; }
        input, select, textarea {
            width: 100%; padding: 7px; border: 1px solid #ccc; border-radius: 5px;
            font-size: 13px; box-sizing: border-box; font-family: inherit;
        }
        .ligne2 { display: flex; gap: 16px; }
        .ligne2 > div { flex: 1; }
        table.items { width: 100%; border-collapse: collapse; margin-top: 8px; }
        table.items th { font-size: 11px; color: #666; text-align: left; padding: 4px; }
        table.items td { padding: 4px; }
        table.items td.col-qty, table.items td.col-price { width: 90px; }
        table.items td.col-remove { width: 30px; }
        .btn-secondaire {
            margin-top: 10px; background: white; color: #1F3B57;
            border: 1px solid #1F3B57; padding: 6px 12px; border-radius: 5px;
            cursor: pointer; font-size: 13px;
        }
        button.remove-row { background: none; border: none; color: #c0392b; cursor: pointer; font-size: 16px; }
        button[type="submit"] {
            margin-top: 28px; width: 100%; padding: 11px; background: #1F3B57;
            color: white; border: none; border-radius: 5px; font-size: 15px; cursor: pointer;
        }
        button[type="submit"]:hover { background: #16293e; }
    </style>
</head>
<body>
    <div class="carte">
        <h1>🧾 Generate an invoice</h1>
        <form action="/generer" method="post" enctype="multipart/form-data">

            <h2>Branding</h2>
            <label>Your logo (optional)</label>
            <input type="file" name="logo" accept="image/*">

            <label>Currency</label>
            <select name="devise">
                <option value="USD">USD ($)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
            </select>

            <h2>Your company</h2>
            <label>Company name</label>
            <input type="text" name="entreprise" required>
            <label>Address</label>
            <textarea name="entreprise_adresse" rows="2"></textarea>
            <div class="ligne2">
                <div>
                    <label>Phone</label>
                    <input type="text" name="entreprise_telephone">
                </div>
                <div>
                    <label>Email</label>
                    <input type="text" name="entreprise_email">
                </div>
            </div>
            <label>Website (optional)</label>
            <input type="text" name="entreprise_site" placeholder="www.yoursite.com">

            <h2>Invoice details</h2>
            <div class="ligne2">
                <div>
                    <label>Client ID (optional)</label>
                    <input type="text" name="client_id">
                </div>
                <div>
                    <label>Terms (e.g. Net 30)</label>
                    <input type="text" name="modalites" value="Net 30">
                </div>
            </div>

            <h2>Bill to</h2>
            <label>ATTN (name/department, optional)</label>
            <input type="text" name="client_attn">
            <label>Client name</label>
            <input type="text" name="client_nom" required>
            <label>Client address</label>
            <textarea name="client_adresse" rows="2"></textarea>
            <label>Client phone (optional)</label>
            <input type="text" name="client_telephone">

            <h2>Ship to (optional)</h2>
            <label>ATTN (name/department, optional)</label>
            <input type="text" name="expedie_attn">
            <label>Name</label>
            <input type="text" name="expedie_nom">
            <label>Address</label>
            <textarea name="expedie_adresse" rows="2"></textarea>
            <label>Phone (optional)</label>
            <input type="text" name="expedie_telephone">

            <h2>Items</h2>
            <table class="items" id="tableau-items">
                <thead>
                    <tr>
                        <th>Description</th>
                        <th class="col-qty">Qty</th>
                        <th class="col-price">Unit price</th>
                        <th class="col-remove"></th>
                    </tr>
                </thead>
                <tbody id="corps-tableau">
                    <tr>
                        <td><input type="text" name="description" required></td>
                        <td class="col-qty"><input type="text" name="qty" value="1"></td>
                        <td class="col-price"><input type="text" name="unit_price" required></td>
                        <td class="col-remove"><button type="button" class="remove-row" onclick="supprimerLigne(this)">✕</button></td>
                    </tr>
                </tbody>
            </table>
            <button type="button" class="btn-secondaire" onclick="ajouterLigne()">+ Add line</button>

            <label style="margin-top:20px;">Tax rate (%)</label>
            <input type="text" name="taux_taxe" value="0">

            <button type="submit">Generate PDF</button>
        </form>
    </div>

    <script>
        // Ajoute une nouvelle ligne d'article en clonant la première ligne du tableau
        function ajouterLigne() {
            const corps = document.getElementById('corps-tableau');
            const nouvelle = corps.rows[0].cloneNode(true);
            // On vide les champs de la copie pour ne pas dupliquer les valeurs
            nouvelle.querySelectorAll('input').forEach(champ => {
                champ.value = champ.name === 'qty' ? '1' : '';
            });
            corps.appendChild(nouvelle);
        }

        // Supprime une ligne (sauf s'il n'en reste qu'une seule)
        function supprimerLigne(bouton) {
            const corps = document.getElementById('corps-tableau');
            if (corps.rows.length > 1) {
                bouton.closest('tr').remove();
            }
        }
    </script>
</body>
</html>
"""


def generer_numero_facture():
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


def enregistrer_dans_historique(numero, entreprise, client, montant_total, chemin_pdf):
    if os.path.exists(FICHIER_HISTORIQUE):
        with open(FICHIER_HISTORIQUE, "r", encoding="utf-8") as f:
            historique = json.load(f)
    else:
        historique = []
    historique.append({
        "numero": numero,
        "date_emission": date.today().strftime("%m/%d/%Y"),
        "entreprise": entreprise,
        "client": client,
        "total": montant_total,
        "fichier_pdf": chemin_pdf,
    })
    with open(FICHIER_HISTORIQUE, "w", encoding="utf-8") as f:
        json.dump(historique, f, indent=2, ensure_ascii=False)


def dessiner_bloc_texte(c, x, y, lignes, taille=10, interligne=5, couleur=colors.black, gras=False):
    """Dessine plusieurs lignes de texte les unes sous les autres."""
    c.setFillColor(couleur)
    c.setFont("Helvetica-Bold" if gras else "Helvetica", taille)
    for i, ligne in enumerate(lignes):
        if ligne:
            c.drawString(x, y - i * interligne * mm, ligne)


def dessiner_logo(c, fichier_logo, x, y_bas, largeur_max, hauteur_max):
    """Dessine le logo uploadé dans une zone donnée, en conservant ses proportions."""
    if not fichier_logo or fichier_logo.filename == "":
        return
    try:
        donnees = fichier_logo.read()
        image = ImageReader(io.BytesIO(donnees))
        largeur_img, hauteur_img = image.getSize()
        echelle = min(largeur_max / largeur_img, hauteur_max / hauteur_img)
        w, h = largeur_img * echelle, hauteur_img * echelle
        c.drawImage(image, x, y_bas + (hauteur_max - h) / 2, width=w, height=h,
                    mask="auto", preserveAspectRatio=True)
    except Exception:
        # Si le fichier n'est pas une image valide, on ignore simplement le logo
        pass


def generer_pdf(donnees_formulaire, fichier_logo, items):
    devise = donnees_formulaire.get("devise", "USD")
    symbole = SYMBOLES_DEVISE.get(devise, "$")

    numero = generer_numero_facture()
    chemin_pdf = os.path.join(DOSSIER_FACTURES, f"facture_{numero}.pdf")

    c = canvas.Canvas(chemin_pdf, pagesize=A4)
    largeur, hauteur = A4

    MARGE_CADRE = 8 * mm

    def dessiner_cadre():
        c.setStrokeColor(colors.HexColor("#999999"))
        c.setLineWidth(0.8)
        c.rect(MARGE_CADRE, MARGE_CADRE, largeur - 2 * MARGE_CADRE, hauteur - 2 * MARGE_CADRE,
               fill=False, stroke=True)

    dessiner_cadre()

    # ---------- LOGO + TITRE ----------
    # Le logo est limité en hauteur pour ne jamais toucher la ligne de séparation en dessous
    dessiner_logo(c, fichier_logo, x=15 * mm, y_bas=hauteur - 38 * mm,
                  largeur_max=50 * mm, hauteur_max=18 * mm)

    c.setFillColor(COULEUR_PRINCIPALE)
    c.setFont("Helvetica-Bold", 26)
    c.drawRightString(largeur - 15 * mm, hauteur - 28 * mm, "INVOICE")

    # Ligne de séparation horizontale sous l'en-tête (logo / titre)
    c.setStrokeColor(COULEUR_PRINCIPALE)
    c.setLineWidth(1.2)
    c.line(15 * mm, hauteur - 44 * mm, largeur - 15 * mm, hauteur - 44 * mm)

    # ---------- INFOS ENTREPRISE (colonne gauche) ----------
    lignes_entreprise = [donnees_formulaire.get("entreprise", "")]
    adresse = donnees_formulaire.get("entreprise_adresse", "")
    lignes_entreprise += adresse.splitlines()[:2]
    lignes_entreprise.append(donnees_formulaire.get("entreprise_telephone", ""))
    lignes_entreprise.append(donnees_formulaire.get("entreprise_email", ""))
    dessiner_bloc_texte(c, 15 * mm, hauteur - 52 * mm,
                         [lignes_entreprise[0]], taille=11, gras=True)
    dessiner_bloc_texte(c, 15 * mm, hauteur - 57 * mm,
                         lignes_entreprise[1:], taille=9.5, couleur=COULEUR_GRISE)

    # ---------- BOITES N° FACTURE / DATE / CLIENT ID / MODALITÉS ----------
    def boite_info(x, y_haut, largeur_boite, label, valeur):
        c.setFillColor(COULEUR_PRINCIPALE)
        c.rect(x, y_haut - 7 * mm, largeur_boite, 7 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(x + 3 * mm, y_haut - 5 * mm, label)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(x + 3 * mm, y_haut - 13 * mm, str(valeur))

    largeur_boite = 40 * mm
    x_col1 = largeur - 15 * mm - 2 * largeur_boite
    x_col2 = largeur - 15 * mm - largeur_boite

    boite_info(x_col1, hauteur - 50 * mm, largeur_boite, "INVOICE #", numero)
    boite_info(x_col2, hauteur - 50 * mm, largeur_boite, "DATE", date.today().strftime("%m/%d/%Y"))
    boite_info(x_col1, hauteur - 68 * mm, largeur_boite, "CLIENT ID",
               donnees_formulaire.get("client_id", "") or "—")
    boite_info(x_col2, hauteur - 68 * mm, largeur_boite, "TERMS",
               donnees_formulaire.get("modalites", "") or "—")

    # ---------- BILL TO / SHIP TO ----------
    y_bloc = hauteur - 95 * mm

    def entete_section(x, y, largeur_bloc, titre):
        c.setFillColor(COULEUR_PRINCIPALE)
        c.rect(x, y - 7 * mm, largeur_bloc, 7 * mm, fill=True, stroke=False)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(x + 3 * mm, y - 5 * mm, titre)

    largeur_demi = (largeur - 30 * mm - 10 * mm) / 2
    x_gauche = 15 * mm
    x_droite = 15 * mm + largeur_demi + 10 * mm

    entete_section(x_gauche, y_bloc, largeur_demi, "BILL TO")
    lignes_bill_to = []
    if donnees_formulaire.get("client_attn"):
        lignes_bill_to.append(f"ATTN: {donnees_formulaire['client_attn']}")
    lignes_bill_to.append(donnees_formulaire.get("client_nom", ""))
    lignes_bill_to += donnees_formulaire.get("client_adresse", "").splitlines()[:2]
    if donnees_formulaire.get("client_telephone"):
        lignes_bill_to.append(donnees_formulaire["client_telephone"])
    dessiner_bloc_texte(c, x_gauche, y_bloc - 12 * mm, lignes_bill_to, taille=10)

    if donnees_formulaire.get("expedie_nom") or donnees_formulaire.get("expedie_adresse"):
        entete_section(x_droite, y_bloc, largeur_demi, "SHIP TO")
        lignes_ship_to = []
        if donnees_formulaire.get("expedie_attn"):
            lignes_ship_to.append(f"ATTN: {donnees_formulaire['expedie_attn']}")
        lignes_ship_to.append(donnees_formulaire.get("expedie_nom", ""))
        lignes_ship_to += donnees_formulaire.get("expedie_adresse", "").splitlines()[:2]
        if donnees_formulaire.get("expedie_telephone"):
            lignes_ship_to.append(donnees_formulaire["expedie_telephone"])
        dessiner_bloc_texte(c, x_droite, y_bloc - 12 * mm, lignes_ship_to, taille=10)

    # ---------- TABLEAU DES ARTICLES (avec pagination) ----------
    # Limites des 4 colonnes : Description | Qty | Unit price | Amount
    B = [15 * mm, largeur - 90 * mm, largeur - 65 * mm, largeur - 35 * mm, largeur - 15 * mm]

    LIMITE_BAS = 40 * mm

    def dessiner_ligne_grille(y_haut, y_bas):
        """Dessine les bordures d'une ligne du tableau (4 cellules)."""
        c.setStrokeColor(colors.HexColor("#AAAAAA"))
        c.setLineWidth(0.4)
        for x in B:
            c.line(x, y_bas, x, y_haut)
        c.line(B[0], y_bas, B[-1], y_bas)
        c.line(B[0], y_haut, B[-1], y_haut)

    def dessiner_entete_tableau(y):
        c.setFillColor(COULEUR_PRINCIPALE)
        c.rect(B[0], y, B[-1] - B[0], 8 * mm, fill=True, stroke=False)
        dessiner_ligne_grille(y + 8 * mm, y)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(B[0] + 3 * mm, y + 2.7 * mm, "DESCRIPTION")
        c.drawCentredString((B[1] + B[2]) / 2, y + 2.7 * mm, "QTY")
        c.drawRightString(B[3] - 3 * mm, y + 2.7 * mm, "UNIT PRICE")
        c.drawRightString(B[4] - 3 * mm, y + 2.7 * mm, "AMOUNT")

    def nouvelle_page_articles():
        """Démarre une nouvelle page et redessine le cadre + l'en-tête du tableau."""
        c.showPage()
        dessiner_cadre()
        y = hauteur - 25 * mm
        c.setFillColor(COULEUR_GRISE)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(15 * mm, hauteur - 15 * mm, f"Invoice {numero} (continued)")
        dessiner_entete_tableau(y)
        return y - 8 * mm  # position juste sous l'en-tête, prête pour la 1ère ligne

    y_table = y_bloc - 46 * mm
    dessiner_entete_tableau(y_table)
    y_ligne = y_table

    sous_total = 0.0
    for i, item in enumerate(items):
        # Si la prochaine ligne ne tient plus au-dessus de la limite basse,
        # on passe à une nouvelle page avant de la dessiner.
        if y_ligne - 7 * mm < LIMITE_BAS:
            y_ligne = nouvelle_page_articles()

        y_haut_ligne = y_ligne
        y_ligne -= 7 * mm
        dessiner_ligne_grille(y_haut_ligne, y_ligne)

        try:
            qte = float(item["qty"] or 0)
            prix_unitaire = float(item["unit_price"] or 0)
        except ValueError:
            qte, prix_unitaire = 0, 0
        montant_ligne = qte * prix_unitaire
        sous_total += montant_ligne

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9.5)
        c.drawString(B[0] + 3 * mm, y_ligne + 2.3 * mm, item["description"])
        c.drawCentredString((B[1] + B[2]) / 2, y_ligne + 2.3 * mm, f"{qte:g}")
        c.drawRightString(B[3] - 3 * mm, y_ligne + 2.3 * mm, f"{symbole}{prix_unitaire:,.2f}")
        c.drawRightString(B[4] - 3 * mm, y_ligne + 2.3 * mm, f"{symbole}{montant_ligne:,.2f}")

    # ---------- TOTAUX ----------
    try:
        taux_taxe = float(donnees_formulaire.get("taux_taxe", 0) or 0)
    except ValueError:
        taux_taxe = 0
    montant_taxe = sous_total * taux_taxe / 100
    total = sous_total + montant_taxe

    # Le bloc des totaux fait environ 27mm de haut (3 lignes + marge).
    # S'il ne tient pas sous la dernière ligne d'article, nouvelle page.
    HAUTEUR_TOTAUX = 27 * mm
    if y_ligne - HAUTEUR_TOTAUX < LIMITE_BAS:
        c.showPage()
        dessiner_cadre()
        y_ligne = hauteur - 30 * mm

    y_totaux = y_ligne - 6 * mm
    largeur_totaux = 75 * mm
    x_totaux = largeur - 15 * mm - largeur_totaux

    def ligne_total(y, label, valeur, gras=False, symbole_separe=False):
        # Colonne label (bleu clair) + colonne valeur (bleu clair aussi), séparées par une ligne
        largeur_label = largeur_totaux * 0.55
        c.setFillColor(COULEUR_CLAIRE)
        c.rect(x_totaux, y - 7 * mm, largeur_totaux, 7 * mm, fill=True, stroke=False)
        c.setStrokeColor(colors.HexColor("#AAAAAA"))
        c.setLineWidth(0.5)
        c.rect(x_totaux, y - 7 * mm, largeur_totaux, 7 * mm, fill=False, stroke=True)
        c.line(x_totaux + largeur_label, y - 7 * mm, x_totaux + largeur_label, y)

        c.setFillColor(COULEUR_PRINCIPALE if gras else colors.black)
        c.setFont("Helvetica-Bold" if gras else "Helvetica", 10 if gras else 9.5)
        c.drawString(x_totaux + 3 * mm, y - 5 * mm, label)

        if symbole_separe:
            c.drawString(x_totaux + largeur_label + 3 * mm, y - 5 * mm, symbole)
            c.drawRightString(x_totaux + largeur_totaux - 3 * mm, y - 5 * mm, valeur)
        else:
            c.drawRightString(x_totaux + largeur_totaux - 3 * mm, y - 5 * mm, valeur)

    ligne_total(y_totaux, "SUBTOTAL", f"{sous_total:,.2f}")
    ligne_total(y_totaux - 7 * mm, f"TAX ({taux_taxe:g}%)", f"{montant_taxe:,.2f}")
    ligne_total(y_totaux - 16 * mm, "TOTAL", f"{total:,.2f}", gras=True, symbole_separe=True)

    # ---------- MERCI (aligné avec le bloc des totaux, comme sur le modèle) ----------
    c.setFillColor(COULEUR_PRINCIPALE)
    c.setFont("Helvetica-Bold", 18)
    centre_gauche = (15 * mm + (x_totaux - 10 * mm)) / 2
    c.drawCentredString(centre_gauche, y_totaux - 11 * mm, "THANK YOU")

    # ---------- FOOTER (toujours sur la dernière page) ----------
    c.setFillColor(COULEUR_GRISE)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(largeur / 2, 20 * mm, "For questions concerning this invoice, please contact")

    c.setFillColor(COULEUR_PRINCIPALE)
    c.setFont("Helvetica-Bold", 9)
    contact = ", ".join(filter(None, [
        donnees_formulaire.get("entreprise", ""),
        donnees_formulaire.get("entreprise_telephone", ""),
        donnees_formulaire.get("entreprise_email", ""),
    ]))
    c.drawCentredString(largeur / 2, 15 * mm, contact)

    site = donnees_formulaire.get("entreprise_site", "")
    if site:
        c.setFillColor(COULEUR_GRISE)
        c.setFont("Helvetica", 8)
        c.drawCentredString(largeur / 2, 10 * mm, site)

    c.save()
    enregistrer_dans_historique(numero, donnees_formulaire.get("entreprise", ""),
                                 donnees_formulaire.get("client_nom", ""), total, chemin_pdf)
    return chemin_pdf


@app.route("/")
def accueil():
    return render_template_string(FORMULAIRE_HTML)


@app.route("/generer", methods=["POST"])
def generer():
    donnees_formulaire = request.form.to_dict()
    fichier_logo = request.files.get("logo")

    descriptions = request.form.getlist("description")
    qtes = request.form.getlist("qty")
    prix = request.form.getlist("unit_price")
    items = [
        {"description": d, "qty": q, "unit_price": p}
        for d, q, p in zip(descriptions, qtes, prix) if d.strip()
    ]

    chemin_pdf = generer_pdf(donnees_formulaire, fichier_logo, items)
    return send_file(chemin_pdf, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
