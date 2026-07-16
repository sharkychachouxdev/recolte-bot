# ─── PERSISTANCE DES SOUMISSIONS (pour gérer edit/delete) ────────────────────
#
# Mémorise, par ID de message Discord, ce qui a été inscrit dans le Google
# Sheet. Permet de répercuter les modifications (edit) et suppressions
# (delete) de messages sur le sheet, même après un redémarrage du bot.
#
# Stocké dans un onglet caché du Google Sheet lui-même (voir sheets.py) plutôt
# que dans un fichier local : sur un hébergeur à disque non-persistant
# (Railway/Render gratuits), un fichier local disparaît à chaque redémarrage,
# ce qui faisait perdre le suivi et provoquait un double-comptage de la
# récolte à la moindre édition après un redémarrage.

import json
from datetime import datetime, timezone, timedelta

from sheets import load_bot_state_rows, save_bot_state_rows

STATE_MAX_AGE_DAYS = 8  # au-delà, une entrée n'est plus utile (semaine déjà reset / saisie trop ancienne)
DISCORD_EPOCH_MS = 1420070400000


def _default_state() -> dict:
    return {"recolte": {}, "cambus": {}}


def _snowflake_to_datetime(snowflake_id: str):
    try:
        ms = (int(snowflake_id) >> 22) + DISCORD_EPOCH_MS
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (ValueError, OverflowError):
        return None


def _prune(store: dict) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=STATE_MAX_AGE_DAYS)
    pruned = {}
    for msg_id, record in store.items():
        ts = _snowflake_to_datetime(msg_id)
        if ts is None or ts >= cutoff:
            pruned[msg_id] = record
    return pruned


def load_state() -> dict:
    state = _default_state()
    try:
        rows = load_bot_state_rows()
    except Exception as e:
        print(f"[STATE] Erreur de chargement depuis le sheet : {e}")
        return state

    for row in rows:
        if len(row) < 3:
            continue
        kind, msg_id, raw_json = row[0], row[1], row[2]
        if kind not in state or not msg_id:
            continue
        try:
            state[kind][msg_id] = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

    return state


def save_state(state: dict) -> None:
    state["recolte"] = _prune(state["recolte"])
    state["cambus"] = _prune(state["cambus"])

    rows = []
    for kind in ("recolte", "cambus"):
        for msg_id, record in state[kind].items():
            rows.append([kind, msg_id, json.dumps(record, ensure_ascii=False)])

    try:
        save_bot_state_rows(rows)
    except Exception as e:
        print(f"[STATE] Erreur de sauvegarde vers le sheet : {e}")
