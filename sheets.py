import os
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

COL_NOM   = 12
ROW_START = 3
SHEET_NAMES = ["Bonelli", "Faustin", "Gitans"]


def get_spreadsheet():
    # Lit les credentials depuis la variable d'environnement GOOGLE_CREDENTIALS
    # (contenu JSON directement) ou depuis un fichier si dispo
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
    return gc.open_by_key(os.getenv("SPREADSHEET_ID"))


def get_worksheet(sheet_name: str):
    return get_spreadsheet().worksheet(sheet_name)


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

    # Lit la valeur actuelle et additionne
    cell_value = ws.cell(row_index, col_index).value
    valeur_actuelle = int(cell_value) if cell_value and str(cell_value).strip().isdigit() else 0
    nouvelle_valeur = valeur_actuelle + recolte
    ws.update_cell(row_index, col_index, nouvelle_valeur)

    print(f"[OK] {sheet_name} | {operateur} | {jour} → {valeur_actuelle} + {recolte} = {nouvelle_valeur} (ligne {row_index}, col {col_index})")
    return {"success": True, "total": nouvelle_valeur}
    return {"success": True}


def new_week() -> dict:
    try:
        spreadsheet = get_spreadsheet()

        today = datetime.now()
        lundi = today - timedelta(days=today.weekday())
        date_str = lundi.strftime("%d/%m/%Y")

        new_names = []

        for base_name in SHEET_NAMES:
            try:
                old_ws = spreadsheet.worksheet(base_name)
            except gspread.WorksheetNotFound:
                print(f"[WARN] Onglet '{base_name}' introuvable, on passe.")
                continue

            all_values = old_ws.get_all_values()

            archive_title = f"{base_name} – {date_str}"
            old_ws.update_title(archive_title)
            spreadsheet.batch_update({"requests": [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": old_ws.id,
                        "hidden": True,
                    },
                    "fields": "hidden"
                }
            }]})

            nb_rows = max(len(all_values) + 5, 50)
            new_ws = spreadsheet.add_worksheet(
                title=base_name,
                rows=str(nb_rows),
                cols="14"
            )

            if len(all_values) >= 2:
                new_ws.update("A1", all_values[0:2])

            updates = []
            for i, row in enumerate(all_values[2:], start=3):
                if len(row) >= COL_NOM:
                    nom = row[COL_NOM - 1]
                    if nom.strip():
                        updates.append({
                            "range": f"L{i}",
                            "values": [[nom]]
                        })

            if updates:
                new_ws.batch_update(updates)

            new_names.append(base_name)
            print(f"[OK] Nouvelle semaine : '{base_name}' créé, '{archive_title}' masqué")

        return {"success": True, "new_names": new_names, "date": date_str}

    except Exception as e:
        print(f"[ERREUR new_week] {e}")
        return {"success": False, "reason": str(e)}
