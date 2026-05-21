import discord
import re
import os
from datetime import datetime
from dotenv import load_dotenv
from sheets import update_recolte, new_week
from users import USERS

load_dotenv()

CHANNEL_TO_SHEET = {
    "champ-bonelli": "Bonelli",
    "champ-faustin": "Faustin",
    "champ-gitans":  "Gitans",
}

JOURS_FR = {
    "Monday":    "Lundi",
    "Tuesday":   "Mardi",
    "Wednesday": "Mercredi",
    "Thursday":  "Jeudi",
    "Friday":    "Vendredi",
    "Saturday":  "Samedi",
    "Sunday":    "Dimanche",
}

# Ton ID Discord — Paramètres → Avancé → Mode développeur ON → clic droit sur ton pseudo → Copier l'identifiant
ADMIN_IDS = [
    123456789012345678,  # remplace par ton vrai ID
]


def parse_message(content: str):
    def get(pattern):
        m = re.search(pattern, content, re.IGNORECASE)
        return m.group(1).strip() if m else None

    recolte = get(r"r[eé]colte\s*:\s*(\d+)")
    arrivee = get(r"heure\s+d.arriv[eé]e\s*:\s*(.+)")
    depart  = get(r"heure\s+de\s+d[eé]part\s*:\s*(.+)")
    matu    = get(r"matu\s*:\s*(.+)")
    # "Opérateur" présent dans le message mais ignoré volontairement

    if not recolte:
        return None

    return {
        "recolte": int(recolte),
        "arrivee": arrivee or "—",
        "depart":  depart  or "—",
        "matu":    matu    or "—",
    }


intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅  Bot connecté : {client.user}")
    print(f"   Channels actifs : {', '.join(CHANNEL_TO_SHEET.keys())}")
    print(f"   Opérateurs enregistrés : {len(USERS)}")


async def traiter_message(message: discord.Message):
    """Traite un message ou une modification de message."""
    if message.author.bot:
        return

    # ── Commande !newweek ─────────────────────────────────────────────────────
    if message.content.strip().lower() == "!newweek":
        if message.author.id not in ADMIN_IDS:
            await message.reply("❌ Tu n'as pas la permission d'utiliser cette commande.")
            return

        await message.reply("⏳ Création de la nouvelle semaine en cours...")
        result = new_week()

        if result["success"]:
            onglets = ", ".join(f"**{n}**" for n in result["new_names"])
            await message.reply(
                f"✅ Nouvelle semaine créée ! (semaine du {result['date']})\n"
                f"Onglets remis à zéro : {onglets}\n"
                f"Les anciennes feuilles sont masquées mais conservées pour tes comptes."
            )
        else:
            await message.reply(f"❌ Erreur : {result['reason']}")
        return

    # ── Messages de récolte ───────────────────────────────────────────────────
    channel_name = message.channel.name.lower()
    if channel_name not in CHANNEL_TO_SHEET:
        return

    # Si pas de récolte dans le message, on ignore silencieusement
    # (ex: message envoyé au début du champ sans récolte encore)
    data = parse_message(message.content)
    if data is None:
        return

    sheet_name = CHANNEL_TO_SHEET[channel_name]

    user_id = str(message.author.id)
    nom_sheet = USERS.get(user_id)

    if nom_sheet is None:
        await message.reply(
            f"⚠️ Ton pseudo Discord **`{message.author.name}`** n'est pas enregistré.\n"
            f"Demande à l'admin de t'ajouter dans `users.py`.",
            mention_author=True
        )
        return

    jour_fr = JOURS_FR.get(datetime.now().strftime("%A"))

    try:
        result = update_recolte(
            sheet_name=sheet_name,
            operateur=nom_sheet,
            jour=jour_fr,
            recolte=data["recolte"],
        )

        if result["success"]:
            await message.reply(
                f"✅ **{sheet_name}** | {jour_fr} | **{nom_sheet}** → +{data['recolte']} ajouté | Total du jour : **{result['total']}**",
                mention_author=True
            )
        else:
            await message.reply(
                f"⚠️ **{nom_sheet}** introuvable dans l'onglet **{sheet_name}**.\n"
                f"Vérifie que le nom dans `users.py` correspond exactement à la colonne `Nom/Prénom` du sheet.",
                mention_author=True
            )

    except Exception as e:
        print(f"[ERREUR SHEETS] {e}")
        await message.reply(
            "❌ Erreur Google Sheets. Vérifie les logs du serveur.",
            mention_author=True
        )


@client.event
async def on_message(message: discord.Message):
    await traiter_message(message)


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    # Déclenché quand quelqu'un modifie son message
    # On traite UNIQUEMENT si la récolte vient d'être ajoutée pour la première fois
    # Si la récolte était déjà là avant la modif (ex: ajout opérateur), on ignore
    recolte_avant = re.search(r"r[eé]coltes*:\s*(\d+)", before.content, re.IGNORECASE)
    recolte_apres = re.search(r"r[eé]coltes*:\s*(\d+)", after.content, re.IGNORECASE)

    if recolte_apres and not recolte_avant:
        await traiter_message(after)


# ─── Lancement ────────────────────────────────────────────────────────────────
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN manquant dans .env")

client.run(token)
