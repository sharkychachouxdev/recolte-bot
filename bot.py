import discord
import re
import os
from datetime import datetime
from dotenv import load_dotenv
try:
    from zoneinfo import ZoneInfo
    _PARIS = ZoneInfo("Europe/Paris")
except ImportError:
    _PARIS = None

def _now():
    return datetime.now(_PARIS) if _PARIS else datetime.now()
from sheets import update_recolte, new_week, append_cambus
from users import USERS

load_dotenv()

# ─── CHANNELS RÉCOLTE CHAMPS ──────────────────────────────────────────────────
CHANNEL_TO_SHEET = {
    "champ-bonelli": "Bonelli",
    "champ-faustin": "Faustin",
    "champ-families": "Families",
}

# ─── CHANNELS CAMBUS / DIGISCANNE ─────────────────────────────────────────────
CHANNEL_CAMBUS     = int(os.getenv("CHANNEL_CAMBUS",     "0"))
CHANNEL_DIGISCANNE = int(os.getenv("CHANNEL_DIGISCANNE", "0"))

JOURS_FR = {
    "Monday":    "Lundi",
    "Tuesday":   "Mardi",
    "Wednesday": "Mercredi",
    "Thursday":  "Jeudi",
    "Friday":    "Vendredi",
    "Saturday":  "Samedi",
    "Sunday":    "Dimanche",
}

ADMIN_IDS = [
    540873627629912084,  # remplace par ton vrai ID
]

# ─── MAPPING OBJETS CAMBUS ────────────────────────────────────────────────────
ITEM_MAP = {
    # Hameçons
    "hamecon alu":            "Hameçon Aluminium",
    "hameçon alu":            "Hameçon Aluminium",
    "ham alu":                "Hameçon Aluminium",
    "hamecon aluminium":      "Hameçon Aluminium",
    "hemecon aluminium":      "Hameçon Aluminium",
    "Hamecon en aluminium ":  "Hameçon Aluminium",
    "Hemecon en aluminium ":  "Hameçon Aluminium",
    "Hamecon en alu ":        "Hameçon Aluminium",
    "hameçon aluminium":      "Hameçon Aluminium",
    "hameçon en aluminium":   "Hameçon Aluminium",
    "hemeçon en aluminium":   "Hameçon Aluminium",
    "hameçon en alu":         "Hameçon Aluminium",
    "en alu":                 "Hameçon Aluminium",
    "hamecon acier":          "Hameçon Acier",
    "hamecon en acier":       "Hameçon Acier",
    "en acier":               "Hameçon Acier",
    "hameçon acier":          "Hameçon Acier",
    "hameçon en acier":       "Hameçon Acier",
    "ham acier":              "Hameçon Acier",
    "hamecon cobalt":         "Hameçon Cobalt",
    "hameçon cobalt":         "Hameçon Cobalt",
    "hameçon en cobalt":      "Hameçon Cobalt",
    "hamecon en cobalt":      "Hameçon Cobalt",
    "ham cobalt":             "Hameçon Cobalt",
    "ham cobat":              "Hameçon Cobalt",
    "en cobat":               "Hameçon Cobalt",
    "en cobalt":              "Hameçon Cobalt",
    "hamecon titane":         "Hameçon Titane",
    "hamecon titan":          "Hameçon Titane",
    "hamecon en titane":      "Hameçon Titane",
    "hamecon en titan":       "Hameçon Titane",
    "hameçon titane":         "Hameçon Titane",
    "ham titan":              "Hameçon Titane",
    "en titane":              "Hameçon Titane",
    "en titan":               "Hameçon Titane",
    "ham titane":             "Hameçon Titane",
    # Tendeur
    "tendeur de cro":         "Tendeur de crochetage",
    "tendeurs de cro":        "Tendeur de crochetage",
    "tendeur cro":            "Tendeur de crochetage",
    "tendeur de crochetage":  "Tendeur de crochetage",
    "tendeurs de crochetage": "Tendeur de crochetage",
    "tendeur":                "Tendeur de crochetage",
    "tendeurs":               "Tendeur de crochetage",
    # Kit réparation
    "kit de répa":            "Kit réparation",
    "kit de repa":            "Kit réparation",
    "kit répa":               "Kit réparation",
    "kit repa":               "Kit réparation",
    "kit réparation":         "Kit réparation",
    "kit reparation":         "Kit réparation",
    # Pièces détachées
    "pièces détachées":       "Pièces détachées",
    "pieces detachees":       "Pièces détachées",
    "pièces détacher":        "Pièces détachées",
    "pieces detacher":        "Pièces détachées",
    "pièce détachée":         "Pièces détachées",
    "piece détachée":         "Pièces détachées",
    # Pile
    "pile":                   "Pile Lithium",
    "pille":                  "Pile Lithium",
    "pile au lithium":        "Pile Lithium",
    "pile lithium":           "Pile Lithium",
    "pile lith":              "Pile Lithium",
    # Clé
    "clé":                    "Clé",
    "cle":                    "Clé",
    # Téléphone
    "téléphone":              "Téléphone",
    "telephone":              "Téléphone",
    # Chargeur
    "chargeur pistolet":      "Chargeur de pistolet",
    "chargeur pour pistolet": "Chargeur de pistolet",
    "chargeur de pistolet":   "Chargeur de pistolet",
    # Cannabis / Drogues
    "cannabis":               "Cannabis",
    "canna":                  "Cannabis",
    "graine cannabis":        "Graine cannabis",
    "graine de cannabis":     "Graine cannabis",
    "graine de canna":        "Graine cannabis",
    "cocaine":                "Cocaïne",
    "cocaïne":                "Cocaïne",
    "methamphétamine":        "Méthamphétamine",
    "methamphetamine":        "Méthamphétamine",
    "Methampethamine":        "Méthamphétamine",
    "méth":                   "Méthamphétamine",
    "heroïne":                "Héroïne",
    "heroine":                "Héroïne",
    "champignon":             "Champignon",
    "champignon magique":     "Champignon magique",
    # Divers
    "kit crochetage":         "Kit crochetage",
    "kit de crochetage":      "Kit crochetage",
    "kit de cro":             "Kit crochetage",
    "canne à peche":          "Canne à pêche",
    "canne a peche":          "Canne à pêche",
    "canne à pêche":          "Canne à pêche",
    "bijoux":                 "Bijoux",
    "bijou":                  "Bijoux",
    "kit nettoyage":          "Kit nettoyage",
    "kit de nettoyage":       "Kit nettoyage",
    "corde solide":           "Corde solide",
    "corde":                  "Corde solide",
    "hache":                  "Hache en Pierre",
    "hache en pierre":        "Hache en Pierre",
    "sac en tissu":           "Sac en tissus",
    "sac en tissus":          "Sac en tissus",
    "sac tissu":              "Sac en tissus",
    "sac tissus":             "Sac en tissus",
    "carte pirate":           "Carte pirate",
  "Carte de sécurité fleeca": "Carte Fleeca",
    "fleeca":                 "Carte Fleeca",
    "lecteur carte pirate":   "Lecteur carte pirate",
}

# ─── MAPPING ID DISCORD → NOM MEMBRE (sheet cambus) ──────────────────────────
MEMBRES_CAMBUS = {
     "434591660501106688": "Noslig Greg",
    "953032395970457681": "Gilson Sidney",
    "540873627629912084": "Smith Selena",
    "261556426005020682": "Blossom Sasou",
    "679821636727472261": "Smith José",
    "1096218148082044928": "Vince",
    "384434828377980928": "Paris Allan",
    "689587226392526880": "Broke Holly",
    "1439764282693648427": "Warren",
    "773154983444611082": "Luna",
    "617093557936848902": "Aleks",
    "1050702624304926761": "Larziz",
    "493202964073283584": "Lena",
    "1233303645747941377": "Brian",
    "1340689064252280974": "Hans",
    "1059194948571902003": "Thomas",
    "1458166292631523403": "Emma",
    "764200156525756416": "Jack",
    "853978573203046440": "Warren.F",
    "469529721269387284": "Kayla",
    "472731621112545280": "Maxon",
    "1462015339964403810": "Saïd",
    "984864079686553680": "Elisa",
    "417408464432660490": "Adel",
    "812388498790678558": "Maxans",
    "282694092679413761": "Sandra",
    "1094986534727471157": "Pablo",
    "306176725082177538": "Rafaël",
    "483633970970492938": "Deku",
    "993974061757628577": "Robin",
    "691950364852879391": "Ricardo", 
    "338238684824469506": "Leo Castelie",
    "462415132664922112": "Leo.G",
    "527961302694363147": "Zark",
    "1233721179249053717": "Sienna",
    "339111289924354048": "Masaru",
    "1206270148177035315": "Sandro",
    "1086783628043878494": "Lenskay",
    "1333523540804239443": "Elvira",
    "375260624034463746": "Tara",
    "1300239681610580050": "Alex.P",
    "446095392736542731": "Brady",
    "1118221253740875826": "Vaine vaine",
    "413326333855399937": "Dariano",
    "694267202752217218": "Maverick",
    "553139043265675267": "Mani",
    "802944895865192448": "Nedim",
    "791421834544676934": "Francis",
    "366519411403653120": "Dimitri",
    "735191904664158219": "Marwan",
    "791421834544676934": "Francis",
    "712063357158555648": "Tina",
    "508554998813163520": "Lorenzo",
    "859462281716301845": "Jamal",
    "790367134026694657": "Juan",
}


# ─── PARSERS ──────────────────────────────────────────────────────────────────

def parse_recolte(content: str):
    """Parse un message de récolte champ (Bonelli/Faustin/Gitans)."""
    def get(pattern):
        m = re.search(pattern, content, re.IGNORECASE)
        return m.group(1).strip() if m else None

    recolte = get(r"r[eé]colte\s*:\s*(\d+)")
    arrivee = get(r"heure\s+d.arriv[eé]e\s*:\s*(.+)")
    depart  = get(r"heure\s+de\s+d[eé]part\s*:\s*(.+)")
    matu    = get(r"matu\s*:\s*(.+)")

    if not recolte:
        return None

    return {
        "recolte": int(recolte),
        "arrivee": arrivee or "—",
        "depart":  depart  or "—",
        "matu":    matu    or "—",
    }


def match_item(raw: str) -> str:
    """Trouve le nom officiel d'un objet depuis son écriture brute."""
    key = raw.lower().strip()
    if key in ITEM_MAP:
        return ITEM_MAP[key]
    for pattern, official in ITEM_MAP.items():
        if pattern in key or key in pattern:
            return official
    return raw.strip().capitalize()


def parse_cambus(content: str) -> list:
    """Parse un message cambus/digiscanne. Retourne une liste de {item, qty}."""
    items = []
    for line in content.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"op[eé]rat(eur|rice)\s*:", line, re.IGNORECASE):
            continue
        # Quantité devant : "4 hamecon alu" ou "x4 hamecon alu"
        m = re.match(r"^[xX×]?(\d+)\s+(.+)$", line)
        if m:
            qty, raw_item = int(m.group(1)), m.group(2)
        else:
            # Quantité derrière : "hamecon alu 4"
            m = re.match(r"^(.+?)\s+[xX×]?(\d+)$", line)
            if m:
                raw_item, qty = m.group(1), int(m.group(2))
            else:
                continue
        items.append({"item": match_item(raw_item), "qty": qty})
    return items


# ─── BOT ──────────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"✅  Bot connecté : {client.user}")
    print(f"   Channels champs   : {', '.join(CHANNEL_TO_SHEET.keys())}")
    print(f"   Channel cambus    : {CHANNEL_CAMBUS}")
    print(f"   Channel digiscanne: {CHANNEL_DIGISCANNE}")
    print(f"   Opérateurs champs : {len(USERS)}")
    print(f"   Membres cambus    : {len(MEMBRES_CAMBUS)}")


async def traiter_recolte(message: discord.Message):
    """Traite un message de récolte champ (Bonelli / Faustin / Gitans)."""
    channel_name = message.channel.name.lower()
    if channel_name not in CHANNEL_TO_SHEET:
        return

    data = parse_recolte(message.content)
    if data is None:
        return

    sheet_name = CHANNEL_TO_SHEET[channel_name]
    user_id    = str(message.author.id)
    nom_sheet  = USERS.get(user_id)

    if nom_sheet is None:
        await message.reply(
            f"⚠️ Ton pseudo Discord **`{message.author.name}`** n'est pas enregistré.\n"
            f"Demande à l'admin de t'ajouter dans `users.py`.",
            mention_author=True
        )
        return

    jour_fr = JOURS_FR.get(_now().strftime("%A"))

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
            await message.add_reaction("<:LAgence_Noslig_Logo_Blanc:1403880911749255280>")
        else:
            await message.reply(
                f"⚠️ **{nom_sheet}** introuvable dans l'onglet **{sheet_name}**.\n"
                f"Vérifie que le nom dans `users.py` correspond exactement à la colonne `Nom/Prénom` du sheet.",
                mention_author=True
            )
    except Exception as e:
        print(f"[ERREUR SHEETS] {e}")
        await message.reply("❌ Erreur Google Sheets. Vérifie les logs du serveur.", mention_author=True)


async def traiter_cambus(message: discord.Message):
    """Traite un message cambus ou digiscanne."""
    items = parse_cambus(message.content)
    if not items:
        return

    user_id     = str(message.author.id)
    member_name = MEMBRES_CAMBUS.get(user_id)

    if not member_name:
        print(f"[CAMBUS] ID inconnu : {message.author.id} ({message.author.display_name})")
        try:
            await message.add_reaction("❓")
        except Exception:
            pass
        return

    date_str = _now().strftime("%d/%m/%Y")

    try:
        success = append_cambus(date_str, member_name, items)
        await message.add_reaction("<:LAgence_Noslig_Logo_Blanc:1403880911749255280>" if success else "❌")
    except Exception as e:
        print(f"[ERREUR CAMBUS SHEETS] {e}")
        await message.add_reaction("❌")


async def traiter_message(message: discord.Message):
    if message.author.bot:
        return

    # Commande !newweek
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

    # Channels cambus / digiscanne
    if message.channel.id in (CHANNEL_CAMBUS, CHANNEL_DIGISCANNE):
        await traiter_cambus(message)
        return

    # Channels récolte champs
    await traiter_recolte(message)


@client.event
async def on_message(message: discord.Message):
    await traiter_message(message)


@client.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    recolte_avant = re.search(r"r[eé]colte\s*:\s*(\d+)", before.content, re.IGNORECASE)
    recolte_apres = re.search(r"r[eé]colte\s*:\s*(\d+)", after.content, re.IGNORECASE)
    if recolte_apres and not recolte_avant:
        await traiter_message(after)


# ─── Lancement ────────────────────────────────────────────────────────────────
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN manquant dans .env")

client.run(token)
