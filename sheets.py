import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Colonnes du sheet (A=1, B=2, C=3 ...)
# A = statut paiement (non payé / payé)
# B = colonne paiement (dropdown)
# C = Dimanche   Récolte
# D = Lundi      Récolte
# E = Mardi      Récolte
# F = Mercredi   Récolte
# G = Jeudi      Récolte
# H = Vendredi   Récolte
# I = Samedi     Récolte
# J = Total Hebdo
# K = Salaire
# L = Nom/Prénom
JOUR_TO_COL = {
    "Dimanche": 3,   # colonne C
    "Lundi":    4,   # colonne D
    "Mardi":    5,   # colonne E
    "Mercredi": 6,   # colonne F
    "Jeudi":    7,   # colonne G
    "Vendredi": 8,   # colonne H
    "Samedi":   9,   # colonne I
}

# Colonne Nom/Prénom
COL_NOM = 12  # colonne L

# Ligne à partir de laquelle commencent les opérateurs (après les 2 lignes de headers)
ROW_START = 4


def get_worksheet(sheet_name: str):
    """Ouvre l'onglet Google Sheet."""
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        scopes=SCOPES,
    )
    gc = gspread.authorize(creds)
    spreadsheet = gc.open_by_key(os.getenv("SPREADSHEET_ID"))
    return spreadsheet.worksheet(sheet_name)


def update_recolte(sheet_name: str, operateur: str, jour: str, recolte: int) -> dict:
    """
    Cherche la ligne de l'opérateur dans l'onglet sheet_name
    et écrit la récolte dans la colonne du jour.

    Retourne {"success": True} ou {"success": False, "reason": "..."}
    """
    if jour not in JOUR_TO_COL:
        return {"success": False, "reason": f"Jour inconnu : {jour}"}

    ws = get_worksheet(sheet_name)

    # Récupère toutes les valeurs de la colonne Nom/Prénom
    noms = ws.col_values(COL_NOM)

    # Cherche la ligne de l'opérateur (insensible à la casse, espaces ignorés)
    operateur_clean = operateur.strip().lower()
    row_index = None

    for i, nom in enumerate(noms):
        if nom.strip().lower() == operateur_clean:
            row_index = i + 1  # gspread est 1-indexé
            break

    if row_index is None:
        return {"success": False, "reason": f"Opérateur '{operateur}' non trouvé"}

    if row_index < ROW_START:
        return {"success": False, "reason": f"Ligne {row_index} est dans les headers"}

    # Écrit la récolte dans la bonne cellule
    col_index = JOUR_TO_COL[jour]
    ws.update_cell(row_index, col_index, recolte)

    print(f"[OK] {sheet_name} | {operateur} | {jour} → {recolte} (ligne {row_index}, col {col_index})")
    return {"success": True}
