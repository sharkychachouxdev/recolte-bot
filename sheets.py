import os
import re
import json
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

JOUR_TO_COL = {
    "Dimanche": 3,
    "Lundi":    4,
    "Mardi":    5,
    "Mercredi": 6,
    "Jeudi":    7,
    "Vendredi": 8,
    "Samedi":   9,
}

COL_NOM    = 12
ROW_START  = 4
SHEET_NAMES = ["Bonelli", "Faustin", "Gitans"]

# Structure sheet cambus : Date=A, Membre=B, puis Objet1/Qté1/Objet2/Qté2...
CAMBUS_SPREADSHEET_ID = os.getenv("CAMBUS_SPREADSHEET_ID", "")  # si sheet séparé
# Si c'est le même spreadsheet que la récolte, laisse vide et ça utilisera SPREADSHEET_ID
COL_CAMBUS_DATE        = 0   # colonne A
COL_CAMBUS_MEMBRE      = 1   # colonne B
COL_CAMBUS_OBJETS_START = 2 # colonne C
MAX_OBJETS             = 10


def get_spreadsheet(spreadsheet_id: str = None):
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(
            os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
            scopes=SCOPES,
        )
    gc = gspread.authorize(creds)
    sid = spreadsheet_id or os.getenv("SPREADSHEET_ID")
    return gc.open_by_key(sid)


def get_worksheet(sheet_name: str):
    return get_spreadsheet().worksheet(sheet_name)


# ─── RÉCOLTE CHAMPS ───────────────────────────────────────────────────────────

def update_recolte(sheet_name: str, operateur: str, jour: str, recolte: int) -> dict:
    if jour not in JOUR_TO_COL:
        return {"success": False, "reason": f"Jour inconnu : {jour}"}

    ws = get_worksheet(sheet_name)
    noms = ws.col_values(COL_NOM)

    operateur_clean = operateur.strip().lower()
    row_index = None

    for i, nom in enumerate(noms):
        if nom.strip().lower() == operateur_clean:
            row_index = i + 1
            break

    if row_index is None:
        return {"success": False, "reason": f"Opérateur '{operateur}' non trouvé"}

    if row_index < ROW_START:
        return {"success": False, "reason": f"Ligne {row_index} est dans les headers"}

    col_index = JOUR_TO_COL[jour]
    cell_value = ws.cell(row_index, col_index).value
    valeur_actuelle = int(cell_value) if cell_value and str(cell_value).strip().isdigit() else 0
    nouvelle_valeur = valeur_actuelle + recolte
    ws.update_cell(row_index, col_index, nouvelle_valeur)

    print(f"[OK] {sheet_name} | {operateur} | {jour} → {valeur_actuelle} + {recolte} = {nouvelle_valeur}")
    return {"success": True, "total": nouvelle_valeur}


# ─── CAMBUS / DIGISCANNE ──────────────────────────────────────────────────────

def append_cambus(date: str, member: str, items: list) -> bool:
    """
    Ajoute une ligne dans le sheet cambus.
    items = liste de {"item": str, "qty": int}
    """
    try:
        # Utilise CAMBUS_SPREADSHEET_ID si défini, sinon le spreadsheet principal
        sid = CAMBUS_SPREADSHEET_ID or os.getenv("SPREADSHEET_ID")
        spreadsheet = get_spreadsheet(sid)
        ws = spreadsheet.worksheet("Saisie") # première feuille

        next_row = len(ws.col_values(1)) + 1

        row = [""] * (COL_CAMBUS_OBJETS_START + MAX_OBJETS * 2)
        row[COL_CAMBUS_DATE]   = date
        row[COL_CAMBUS_MEMBRE] = member

        for i, entry in enumerate(items[:MAX_OBJETS]):
            row[COL_CAMBUS_OBJETS_START + i * 2]     = entry["item"]
            row[COL_CAMBUS_OBJETS_START + i * 2 + 1] = entry["qty"]

        ws.update(f"A{next_row}", [row])
        print(f"[CAMBUS OK] ligne {next_row} — {member} — {len(items)} objets")
        return True

    except Exception as e:
        print(f"[ERREUR CAMBUS] {e}")
        return False


# ─── NEW WEEK ─────────────────────────────────────────────────────────────────

# Dates de la semaine suivante par colonne (Dimanche = dimanche qui précède le lundi)
_JOUR_COL_OFFSET = {
    3: -1,  # Dimanche  (lundi - 1 jour)
    4:  0,  # Lundi
    5:  1,  # Mardi
    6:  2,  # Mercredi
    7:  3,  # Jeudi
    8:  4,  # Vendredi
    9:  5,  # Samedi
}


def new_week() -> dict:
    try:
        spreadsheet = get_spreadsheet()

        today          = datetime.now()
        lundi_actuel   = today - timedelta(days=today.weekday())
        lundi_prochain = lundi_actuel + timedelta(days=7)

        date_str_archive = lundi_actuel.strftime("%d/%m/%Y")
        date_str_new     = lundi_prochain.strftime("%d/%m/%Y")

        new_names = []

        for base_name in SHEET_NAMES:
            try:
                old_ws = spreadsheet.worksheet(base_name)
            except gspread.WorksheetNotFound:
                print(f"[WARN] Onglet '{base_name}' introuvable, on passe.")
                continue

            old_sheet_id = old_ws.id
            all_sheets   = spreadsheet.worksheets()
            old_index    = next(i for i, ws in enumerate(all_sheets) if ws.id == old_sheet_id)

            # 1) Dupliquer la feuille avec un nom temporaire (préserve tout le formatage)
            temp_name = f"__new_{base_name}__"
            response  = spreadsheet.batch_update({
                "requests": [{
                    "duplicateSheet": {
                        "sourceSheetId":    old_sheet_id,
                        "insertSheetIndex": old_index + 1,
                        "newSheetName":     temp_name,
                    }
                }]
            })
            new_sheet_id = response["replies"][0]["duplicateSheet"]["properties"]["sheetId"]

            # 2) Archiver et masquer l'ancienne feuille (titre + hidden en une requête)
            archive_title = f"{base_name} – {date_str_archive}"
            spreadsheet.batch_update({
                "requests": [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": old_sheet_id,
                            "title":   archive_title,
                            "hidden":  True,
                        },
                        "fields": "title,hidden",
                    }
                }]
            })

            # 3) Renommer le duplicata en nom officiel
            spreadsheet.batch_update({
                "requests": [{
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": new_sheet_id,
                            "title":   base_name,
                        },
                        "fields": "title",
                    }
                }]
            })

            # 4) Récupérer l'objet worksheet du duplicata
            new_ws = next(ws for ws in spreadsheet.worksheets() if ws.id == new_sheet_id)

            # 5) Lire les valeurs pour connaître la taille (avant tout effacement)
            all_values = new_ws.get_all_values()
            last_row   = max(len(all_values), ROW_START)

            # 6) Effacer toutes les valeurs C–I des lignes de données
            new_ws.batch_clear([f"C{ROW_START}:I{last_row}"])

            # 7) Restaurer les formules depuis l'archive (copyPaste PASTE_FORMULA)
            #    → les cellules avec formule reviennent, les valeurs manuelles restent vides
            spreadsheet.batch_update({
                "requests": [{
                    "copyPaste": {
                        "source": {
                            "sheetId":        old_sheet_id,
                            "startRowIndex":  ROW_START - 1,
                            "endRowIndex":    last_row,
                            "startColumnIndex": 2,   # col C (0-based)
                            "endColumnIndex":   9,   # col I inclusive → 9 exclusive
                        },
                        "destination": {
                            "sheetId":        new_sheet_id,
                            "startRowIndex":  ROW_START - 1,
                            "endRowIndex":    last_row,
                            "startColumnIndex": 2,
                            "endColumnIndex":   9,
                        },
                        "pasteType":        "PASTE_FORMULA",
                        "pasteOrientation": "NORMAL",
                    }
                }]
            })

            # 8) Mettre à jour les dates dans les lignes d'en-tête (1 à ROW_START-1)
            date_updates = []
            for row_idx in range(ROW_START - 1):          # lignes 0-based : 0, 1, 2
                if row_idx >= len(all_values):
                    break
                header_row = all_values[row_idx]
                for col_num, offset in _JOUR_COL_OFFSET.items():
                    idx       = col_num - 1               # index 0-based dans la ligne
                    cell_val  = header_row[idx] if idx < len(header_row) else ""
                    # Ne mettre à jour que les cellules qui contiennent déjà une date
                    if not re.search(r'\d{1,2}/\d{1,2}', str(cell_val)):
                        continue
                    new_date_obj = lundi_prochain + timedelta(days=offset)
                    # Préserver le format existant (avec ou sans année)
                    if re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', cell_val):
                        new_date = new_date_obj.strftime("%d/%m/%Y")
                    else:
                        new_date = new_date_obj.strftime("%d/%m")
                    col_letter = chr(ord('A') + col_num - 1)
                    date_updates.append({
                        "range":  f"{col_letter}{row_idx + 1}",
                        "values": [[new_date]],
                    })

            if date_updates:
                new_ws.batch_update(date_updates)

            new_names.append(base_name)
            print(f"[OK] '{base_name}' créé (sem. {date_str_new}), '{archive_title}' masqué")

        return {"success": True, "new_names": new_names, "date": date_str_new}

    except Exception as e:
        print(f"[ERREUR new_week] {e}")
        return {"success": False, "reason": str(e)}
