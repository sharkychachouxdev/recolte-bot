import discord
import re
import os
from datetime import datetime, time as dtime
from discord.ext import tasks
from dotenv import load_dotenv
try:
    from zoneinfo import ZoneInfo
    _PARIS = ZoneInfo("Europe/Paris")
except ImportError:
    _PARIS = None

def _now():
    return datetime.now(_PARIS) if _PARIS else datetime.now()
from sheets import update_recolte, new_week, append_cambus, update_cambus_row, clear_cambus_row
from users import USERS
from state import load_state, save_state
from cambus_menu import SaisieCambusButtonView, SaisieRecordView, CartView

load_dotenv()

# ─── SUIVI DES SOUMISSIONS (pour répercuter edit/delete sur le sheet) ────────
STATE = load_state()

# ─── CHANNELS RÉCOLTE CHAMPS ──────────────────────────────────────────────────
CHANNEL_TO_SHEET = {
    "champ-bonelli": "Bonelli",
    "champ-faustin": "Faustin",
    "champ-vagos": "Vagos",
}

# ─── CHANNELS CAMBUS / DIGISCANNE ─────────────────────────────────────────────
CHANNEL_CAMBUS      = int(os.getenv("CHANNEL_CAMBUS",      "0"))
CHANNEL_DIGISCANNE  = int(os.getenv("CHANNEL_DIGISCANNE",  "0"))
CHANNEL_CAMBUS_MENU = int(os.getenv("CHANNEL_CAMBUS_MENU", "1330679538736173106"))
# Channel où sont notifiées les modifications/suppressions de saisies déjà
# validées (traçabilité admin). Laisser à 0 pour désactiver ces notifs.
CHANNEL_CAMBUS_LOG  = int(os.getenv("CHANNEL_CAMBUS_LOG",  "0"))

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
    "646623783633027072": "Jo",
    "733317226148659271": "Ethan",
    "1435531868106784850": "John",
    "1385831594069200987": "Tayron",
    "922112971793133568": "John.R",
    "931356130238681098": "Mike",
    "1407413370885509250": "Alan.H",
    "478531158338961435": "Jack.B",
    "682747688604663848": "John.M",
    "479310505539010565": "Nora",
    "378316829791223810": "Mia",
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

# Vues persistantes : initialisées à None, créées dans on_ready() une fois
# que la boucle asyncio tourne (discord.ui.View en a besoin pour appeler
# asyncio.get_running_loop()).
SAISIE_CAMBUS_VIEW = None
SAISIE_RECORD_VIEW = None


# ─── NOUVELLE SEMAINE AUTOMATIQUE (dimanche minuit, heure de Paris) ───────────

@tasks.loop(time=dtime(hour=0, minute=0, tzinfo=_PARIS) if _PARIS else dtime(hour=0, minute=0))
async def newweek_hebdomadaire():
    if _now().weekday() != 6:  # 0=lundi ... 6=dimanche
        return
    print("[NEWWEEK AUTO] Déclenchement automatique (dimanche minuit)")
    result = new_week(_now())
    if result["success"]:
        print(f"[NEWWEEK AUTO] OK — semaine du {result['date']} — onglets : {', '.join(result['new_names'])}")
    else:
        print(f"[NEWWEEK AUTO] ERREUR : {result['reason']}")


@newweek_hebdomadaire.before_loop
async def before_newweek_hebdomadaire():
    await client.wait_until_ready()


@client.event
async def on_ready():
    global SAISIE_CAMBUS_VIEW, SAISIE_RECORD_VIEW

    # Création + enregistrement des vues persistantes, seulement maintenant
    # que le bot est prêt et que la boucle asyncio tourne.
    if SAISIE_CAMBUS_VIEW is None:
        SAISIE_CAMBUS_VIEW = SaisieCambusButtonView(
            resolve_member=resolve_membre_cambus,
            on_valider=valider_saisie_cambus,
        )
        client.add_view(SAISIE_CAMBUS_VIEW)

    if SAISIE_RECORD_VIEW is None:
        SAISIE_RECORD_VIEW = SaisieRecordView(
            get_record=lambda message_id: STATE["cambus"].get(message_id),
            on_modifier=record_modifier_saisie,
            on_supprimer=record_supprimer_saisie,
        )
        client.add_view(SAISIE_RECORD_VIEW)

    if not newweek_hebdomadaire.is_running():
        newweek_hebdomadaire.start()

    print(f"✅  Bot connecté : {client.user}")
    print(f"   Channels champs   : {', '.join(CHANNEL_TO_SHEET.keys())}")
    print(f"   Channel cambus    : {CHANNEL_CAMBUS}")
    print(f"   Channel digiscanne: {CHANNEL_DIGISCANNE}")
    print(f"   Channel log cambus: {CHANNEL_CAMBUS_LOG or '(non configuré)'}")
    print(f"   Opérateurs champs : {len(USERS)}")
    print(f"   Membres cambus    : {len(MEMBRES_CAMBUS)}")
    print(f"   Suivi récolte     : {len(STATE['recolte'])} message(s) suivi(s)")
    print(f"   Suivi cambus      : {len(STATE['cambus'])} saisie(s) suivie(s)")


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
            STATE["recolte"][str(message.id)] = {
                "sheet_name": sheet_name,
                "operateur":  nom_sheet,
                "jour":       jour_fr,
                "recolte":    data["recolte"],
            }
            save_state(STATE)
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
        row = append_cambus(date_str, member_name, items)
        if row is not None:
            STATE["cambus"][str(message.id)] = {
                "row":    row,
                "member": member_name,
                "date":   date_str,
                "items":  items,
            }
            save_state(STATE)
            await log_cambus_modification("🧾 Nouvelle saisie (texte)", member_name, items, message.author)
        await message.add_reaction("<:LAgence_Noslig_Logo_Blanc:1403880911749255280>" if row is not None else "❌")
    except Exception as e:
        print(f"[ERREUR CAMBUS SHEETS] {e}")
        await message.add_reaction("❌")


# ─── MENU INTERACTIF CAMBUS (bouton → panier) ─────────────────────────────────

def resolve_membre_cambus(user_id: str):
    return MEMBRES_CAMBUS.get(user_id)


async def log_cambus_modification(action: str, member_name: str, items: list, user: discord.abc.User | None = None, operateur_text: str = ""):
    """Notifie un channel de log admin qu'une saisie déjà validée a été
    modifiée ou supprimée, pour garder une trace visible de ce qui est
    réellement répercuté sur le sheet. No-op si CHANNEL_CAMBUS_LOG n'est
    pas configuré."""
    if not CHANNEL_CAMBUS_LOG:
        print("[LOG CAMBUS] CHANNEL_CAMBUS_LOG non configuré (variable vide ou 0), log ignoré.")
        return
    channel = client.get_channel(CHANNEL_CAMBUS_LOG)
    if channel is None:
        print(f"[LOG CAMBUS] Channel introuvable pour l'ID {CHANNEL_CAMBUS_LOG} (mauvais ID, ou pas en cache).")
        return
    lignes = "\n".join(f"• **{e['qty']}x** {e['item']}" for e in items)
    note = f"\nOpérateur : **{operateur_text}**" if operateur_text else ""
    qui = f" par {user.mention}" if user is not None else ""
    try:
        await channel.send(f"{action}{qui} — **{member_name}**\n{lignes}{note}")
    except discord.HTTPException as e:
        print(f"[ERREUR LOG CAMBUS] {e}")


async def valider_saisie_cambus(interaction: discord.Interaction, member_name: str, items: list, operateur_text: str) -> bool:
    """Écrit la saisie du panier sur le sheet et poste une confirmation
    publique dans le channel, avec des boutons Modifier/Supprimer persistants
    (SaisieRecordView) pour pouvoir corriger une erreur ensuite."""
    date_str = _now().strftime("%d/%m/%Y")
    try:
        row = append_cambus(date_str, member_name, items)
        if row is None:
            return False

        lignes = "\n".join(f"• **{e['qty']}x** {e['item']}" for e in items)
        note = f"\nOpérateur : **{operateur_text}**" if operateur_text else ""
        try:
            sent = await interaction.channel.send(
                f"🧾 Nouvelle saisie cambus — **{member_name}**\n{lignes}{note}",
                view=SAISIE_RECORD_VIEW,
            )
            STATE["cambus"][str(sent.id)] = {
                "row":       row,
                "member":    member_name,
                "date":      date_str,
                "items":     items,
                "operateur": operateur_text,
            }
            save_state(STATE)

            await log_cambus_modification("🧾 Nouvelle saisie", member_name, items, interaction.user, operateur_text)
        except discord.HTTPException as e:
            print(f"[ERREUR CAMBUS UI - confirmation publique] {e}")

        return True
    except Exception as e:
        print(f"[ERREUR CAMBUS UI] {e}")
        return False


async def record_modifier_saisie(interaction: discord.Interaction, record: dict):
    """Rouvre un panier pré-rempli avec le contenu d'une saisie déjà validée,
    pour permettre de la corriger. La validation met à jour la ligne du
    sheet existante (au lieu d'en créer une nouvelle) et répercute le
    changement sur le message public d'origine."""
    original_message = interaction.message  # le message public Modifier/Supprimer

    async def on_valider_modif(inter2: discord.Interaction, member_name2: str, items2: list, operateur_text2: str) -> bool:
        try:
            ok = update_cambus_row(record["row"], record["date"], member_name2, items2)
            if not ok:
                return False

            record["items"] = items2
            record["member"] = member_name2
            record["operateur"] = operateur_text2
            save_state(STATE)

            lignes = "\n".join(f"• **{e['qty']}x** {e['item']}" for e in items2)
            note = f"\nOpérateur : **{operateur_text2}**" if operateur_text2 else ""
            try:
                await original_message.edit(
                    content=f"🧾 Saisie cambus (modifiée) — **{member_name2}**\n{lignes}{note}",
                    view=SAISIE_RECORD_VIEW,
                )
            except discord.HTTPException as e:
                print(f"[ERREUR MAJ MESSAGE ORIGINAL] {e}")

            await log_cambus_modification("✏️ Saisie modifiée", member_name2, items2, inter2.user, operateur_text2)
            return True
        except Exception as e:
            print(f"[ERREUR CAMBUS MODIF] {e}")
            return False

    cart_view = CartView(
        member_name=record["member"],
        on_valider=on_valider_modif,
        initial_items=record["items"],
        titre="✏️ Modifier ma saisie",
    )
    await interaction.response.send_message(
        embed=cart_view.build_embed(), view=cart_view, ephemeral=True
    )


async def record_supprimer_saisie(interaction: discord.Interaction, record: dict):
    """Vide la ligne du sheet correspondant à une saisie déjà validée et
    marque le message public comme supprimé."""
    try:
        ok = clear_cambus_row(record["row"])
        if not ok:
            await interaction.response.send_message(
                "❌ Erreur lors de la suppression sur le sheet, réessaie.", ephemeral=True
            )
            return

        STATE["cambus"].pop(str(interaction.message.id), None)
        save_state(STATE)

        await interaction.response.edit_message(
            content=f"🗑️ Saisie cambus supprimée — **{record['member']}**",
            view=None,
        )

        await log_cambus_modification(
            "🗑️ Saisie supprimée", record["member"], record["items"], interaction.user, record.get("operateur", "")
        )
    except Exception as e:
        print(f"[ERREUR CAMBUS SUPPRESSION] {e}")
        try:
            await interaction.response.send_message("❌ Erreur lors de la suppression.", ephemeral=True)
        except discord.InteractionResponded:
            pass


async def traiter_message(message: discord.Message):
    if message.author.bot:
        return

    # Commande !newweek
    if message.content.strip().lower() == "!newweek":
        if message.author.id not in ADMIN_IDS:
            await message.reply("❌ Tu n'as pas la permission d'utiliser cette commande.")
            return
        await message.reply("⏳ Création de la nouvelle semaine en cours...")
        result = new_week(_now())
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

    # Commande !setup_cambus : poste le bouton persistant de saisie cambus
    if message.content.strip().lower() == "!setup_cambus":
        if message.author.id not in ADMIN_IDS:
            await message.reply("❌ Tu n'as pas la permission d'utiliser cette commande.")
            return
        channel = client.get_channel(CHANNEL_CAMBUS_MENU)
        if channel is None:
            await message.reply(f"❌ Channel introuvable : {CHANNEL_CAMBUS_MENU}")
            return
        await channel.send(
            "🧾 **Saisie cambus**\nClique sur le bouton ci-dessous pour déclarer ta récolte "
            "(jusqu'à 10 objets différents par saisie, quantité illimitée par objet).",
            view=SAISIE_CAMBUS_VIEW,
        )
        await message.reply(f"✅ Bouton de saisie posté dans <#{CHANNEL_CAMBUS_MENU}>.")
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


# ─── GESTION DES MODIFICATIONS DE MESSAGE ─────────────────────────────────────

async def gerer_edition_recolte(message: discord.Message):
    """Répercute la modification d'un message de récolte champ sur le sheet.

    Seul le nombre après **Récolte :** compte pour le sheet (delta entre
    l'ancienne et la nouvelle valeur) ; le crédit reste toujours sur
    l'opérateur d'origine (celui qui a posté le message). Le champ
    **Opérateur :** est purement informatif et n'a aucun effet ici."""
    channel_name = message.channel.name.lower()
    if channel_name not in CHANNEL_TO_SHEET:
        return

    msg_id = str(message.id)
    record = STATE["recolte"].get(msg_id)
    data = parse_recolte(message.content)
    nouvelle_recolte = data["recolte"] if data else 0

    if record is None:
        # Pas encore suivi : si le message est maintenant valide, on le traite
        # comme une nouvelle soumission (peu importe le nombre d'éditions).
        if data is not None:
            await traiter_recolte(message)
        return

    delta = nouvelle_recolte - record["recolte"]
    if delta == 0:
        return

    try:
        result = update_recolte(
            sheet_name=record["sheet_name"],
            operateur=record["operateur"],
            jour=record["jour"],
            recolte=delta,
        )
        if result["success"]:
            if nouvelle_recolte <= 0:
                del STATE["recolte"][msg_id]
            else:
                record["recolte"] = nouvelle_recolte
            save_state(STATE)
            signe = "+" if delta > 0 else ""
            await message.reply(
                f"✏️ **{record['sheet_name']}** | {record['jour']} | **{record['operateur']}** → "
                f"{signe}{delta} (modification) | Total du jour : **{result['total']}**",
                mention_author=True
            )
    except Exception as e:
        print(f"[ERREUR SHEETS EDIT] {e}")


async def gerer_edition_cambus(message: discord.Message):
    """Répercute la modification d'un message cambus/digiscanne sur le sheet."""
    msg_id = str(message.id)
    record = STATE["cambus"].get(msg_id)
    items = parse_cambus(message.content)

    if record is None:
        # Pas encore suivi : si le message est maintenant valide, on le traite
        # comme une nouvelle soumission.
        if items:
            await traiter_cambus(message)
        return

    try:
        if items:
            if update_cambus_row(record["row"], record["date"], record["member"], items):
                record["items"] = items
                save_state(STATE)
                await message.add_reaction("✏️")
                await log_cambus_modification("✏️ Saisie modifiée (texte)", record["member"], items, message.author)
        else:
            # Plus aucun objet dans le message modifié → on vide la ligne
            if clear_cambus_row(record["row"]):
                ancien_items = record["items"]
                ancien_member = record["member"]
                del STATE["cambus"][msg_id]
                save_state(STATE)
                await message.add_reaction("🗑️")
                await log_cambus_modification("🗑️ Saisie supprimée (texte vidé)", ancien_member, ancien_items, message.author)
    except Exception as e:
        print(f"[ERREUR CAMBUS EDIT] {e}")


async def gerer_suppression_recolte(message_id: int):
    """Retire de la sheet la récolte champ liée à un message supprimé."""
    msg_id = str(message_id)
    record = STATE["recolte"].pop(msg_id, None)
    if record is None:
        return
    try:
        update_recolte(
            sheet_name=record["sheet_name"],
            operateur=record["operateur"],
            jour=record["jour"],
            recolte=-record["recolte"],
        )
        save_state(STATE)
        print(f"[RECOLTE DELETE] message {msg_id} → -{record['recolte']} retiré "
              f"({record['sheet_name']} / {record['operateur']} / {record['jour']})")
    except Exception as e:
        print(f"[ERREUR SHEETS DELETE] {e}")


async def gerer_suppression_cambus(message_id: int):
    """Vide la ligne cambus liée à un message supprimé."""
    msg_id = str(message_id)
    record = STATE["cambus"].pop(msg_id, None)
    if record is None:
        return
    try:
        clear_cambus_row(record["row"])
        save_state(STATE)
        print(f"[CAMBUS DELETE] message {msg_id} → ligne {record['row']} vidée")
        await log_cambus_modification("🗑️ Saisie supprimée (message effacé)", record["member"], record["items"])
    except Exception as e:
        print(f"[ERREUR CAMBUS DELETE] {e}")


@client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    # On ignore les MESSAGE_UPDATE qui ne touchent pas le contenu (embeds, pin, etc.)
    if "content" not in payload.data:
        return

    channel = client.get_channel(payload.channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(payload.channel_id)
        except discord.HTTPException:
            return

    try:
        message = await channel.fetch_message(payload.message_id)
    except discord.HTTPException:
        return

    if message.author.bot:
        return

    if message.channel.id in (CHANNEL_CAMBUS, CHANNEL_DIGISCANNE):
        await gerer_edition_cambus(message)
    else:
        await gerer_edition_recolte(message)


@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    await gerer_suppression_recolte(payload.message_id)
    await gerer_suppression_cambus(payload.message_id)


@client.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    for message_id in payload.message_ids:
        await gerer_suppression_recolte(message_id)
        await gerer_suppression_cambus(message_id)


# ─── Lancement ────────────────────────────────────────────────────────────────
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN manquant dans .env")

client.run(token)
