# ─── PERSISTANCE DES SOUMISSIONS (pour gérer edit/delete) ────────────────────
#
# Mémorise, par ID de message Discord, ce qui a été inscrit dans le Google
# Sheet. Permet de répercuter les modifications (edit) et suppressions
# (delete) de messages sur le sheet, même après un redémarrage du bot.

import json
import os

STATE_FILE = os.getenv("STATE_FILE", "state.json")


def _default_state() -> dict:
    return {"recolte": {}, "cambus": {}}


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_state()
    data.setdefault("recolte", {})
    data.setdefault("cambus", {})
    return data


def save_state(state: dict) -> None:
    tmp_path = STATE_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, STATE_FILE)
