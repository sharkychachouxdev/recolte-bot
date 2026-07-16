# ─── MENU INTERACTIF DE SAISIE CAMBUS ─────────────────────────────────────────
#
# Bouton permanent → panier (choix d'un objet + quantité, répété) → validation.
# Ce module est purement UI : l'écriture réelle dans le Google Sheet est
# déléguée à la fonction `on_valider` fournie par bot.py (injection de
# dépendance), pour éviter les imports circulaires.

import discord

MAX_ITEMS_PAR_SAISIE = 10  # limite du Google Sheet (10 objets max par ligne)

ITEMS_CAMBUS = [
    "Bijoux",
    "Boite à feux d'artifices",
    "Cannabis",
    "Canne à pêche",
    "Carte Blaine County",
    "Carte Fleeca",
    "Carte Fort Carson Bank",
    "Carte pirate",
    "Champignon",
    "Champignon magique",
    "Chargeur de pistolet",
    "Clé",
    "Cocaïne",
    "Corde solide",
    "Graine cannabis",
    "Hache en Pierre",
    "Hameçon Acier",
    "Hameçon Aluminium",
    "Hameçon Cobalt",
    "Hameçon Titane",
    "Héroïne",
    "Kit crochetage",
    "Kit nettoyage",
    "Kit réparation",
    "Lecteur carte pirate",
    "Méthamphétamine",
    "Ordinateur portable",
    "Pile Lithium",
    "Pièces détachées",
    "Sac en tissus",
    "Tendeur de crochetage",
    "Tournevis",
    "Toluène",
    "Téléphone",
    "Petit chargeur de pistolet",
]


def _chunk(lst: list, size: int) -> list:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


ITEM_CHUNKS = _chunk(ITEMS_CAMBUS, 25)  # 25 = max options par menu déroulant Discord


def _build_cart_embed(cart: list, member_name: str) -> discord.Embed:
    embed = discord.Embed(title="🧾 Saisie cambus", color=discord.Color.blurple())
    if not cart:
        embed.description = "Panier vide. Choisis un objet dans le menu ci-dessous."
    else:
        embed.description = "\n".join(f"• **{e['qty']}x** {e['item']}" for e in cart)
    embed.set_footer(text=f"{len(cart)}/{MAX_ITEMS_PAR_SAISIE} objets — {member_name}")
    return embed


class QuantiteModal(discord.ui.Modal):
    quantite = discord.ui.TextInput(
        label="Quantité",
        placeholder="Ex : 4",
        default="1",
        max_length=4,
        required=True,
    )

    def __init__(self, item_name: str, cart_view: "CartView"):
        super().__init__(title=item_name[:45])
        self.item_name = item_name
        self.cart_view = cart_view

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.quantite.value.strip()
        if not raw.isdigit() or int(raw) <= 0:
            await interaction.response.send_message(
                "⚠️ Quantité invalide : entre un nombre entier positif.", ephemeral=True
            )
            return

        self.cart_view.ajouter(self.item_name, int(raw))
        self.cart_view.refresh_state()
        await interaction.response.edit_message(
            embed=self.cart_view.build_embed(), view=self.cart_view
        )


class OperateurModal(discord.ui.Modal, title="Valider la saisie"):
    operateur = discord.ui.TextInput(
        label="Opérateur (optionnel, non écrit sur le sheet)",
        placeholder="Ex : Elisa",
        required=False,
        max_length=50,
    )

    def __init__(self, cart_view: "CartView"):
        super().__init__()
        self.cart_view = cart_view

    async def on_submit(self, interaction: discord.Interaction):
        items = list(self.cart_view.cart)
        operateur_text = self.operateur.value.strip()

        success = await self.cart_view.on_valider(
            interaction, self.cart_view.member_name, items, operateur_text
        )

        if success:
            embed = discord.Embed(
                title="🧾 Saisie cambus",
                description="\n".join(f"• **{e['qty']}x** {e['item']}" for e in items),
                color=discord.Color.green(),
            )
            note = f" (opérateur : {operateur_text})" if operateur_text else ""
            embed.set_footer(text=f"✅ Envoyé pour {self.cart_view.member_name}{note}")
            for child in self.cart_view.children:
                child.disabled = True
            await interaction.response.edit_message(embed=embed, view=self.cart_view)
            self.cart_view.stop()
        else:
            await interaction.response.edit_message(
                content="❌ Erreur lors de l'envoi au sheet, réessaie.",
                embed=self.cart_view.build_embed(),
                view=self.cart_view,
            )


class ItemSelect(discord.ui.Select):
    def __init__(self, chunk_index: int, options: list, cart_view: "CartView"):
        placeholder = (
            f"Choisir un objet ({chunk_index}/{len(ITEM_CHUNKS)})"
            if len(ITEM_CHUNKS) > 1 else "Choisir un objet"
        )
        super().__init__(
            placeholder=placeholder,
            options=[discord.SelectOption(label=item) for item in options],
            min_values=1,
            max_values=1,
            row=chunk_index - 1,
        )
        self.cart_view = cart_view

    async def callback(self, interaction: discord.Interaction):
        item_name = self.values[0]
        deja_dans_panier = any(e["item"] == item_name for e in self.cart_view.cart)
        if not deja_dans_panier and len(self.cart_view.cart) >= MAX_ITEMS_PAR_SAISIE:
            await interaction.response.send_message(
                f"⚠️ Maximum {MAX_ITEMS_PAR_SAISIE} objets différents par saisie (limite du sheet).\n"
                f"Tu peux encore augmenter la quantité d'un objet déjà dans le panier, "
                f"sinon valide cette saisie puis relance **Faire ma saisie cambus** pour le reste.",
                ephemeral=True,
            )
            return
        await interaction.response.send_modal(QuantiteModal(item_name, self.cart_view))


class CartView(discord.ui.View):
    def __init__(self, member_name: str, on_valider):
        super().__init__(timeout=900)  # 15 min d'inactivité
        self.member_name = member_name
        self.on_valider = on_valider
        self.cart: list = []  # [{"item": str, "qty": int}]

        # Les boutons décorés (@discord.ui.button) sont ajoutés automatiquement
        # par super().__init__() ci-dessus, sans row explicite : ils se
        # retrouvent donc tous par défaut sur la row 0. Comme chaque
        # ItemSelect occupe à lui seul toute la largeur d'une row (5), il faut
        # d'abord les retirer, ajouter les selects sur leurs rows dédiées,
        # puis rajouter les boutons sur une row libre juste après.
        boutons = (self.valider_button, self.vider_button, self.annuler_button)
        for btn in boutons:
            self.remove_item(btn)

        for i, chunk in enumerate(ITEM_CHUNKS, start=1):
            self.add_item(ItemSelect(i, chunk, self))

        boutons_row = len(ITEM_CHUNKS)
        for btn in boutons:
            btn.row = boutons_row
            self.add_item(btn)

        self.refresh_state()

    def ajouter(self, item: str, qty: int):
        for entry in self.cart:
            if entry["item"] == item:
                entry["qty"] += qty
                return
        self.cart.append({"item": item, "qty": qty})

    def refresh_state(self):
        self.valider_button.disabled = len(self.cart) == 0

    def build_embed(self) -> discord.Embed:
        return _build_cart_embed(self.cart, self.member_name)

    @discord.ui.button(label="Valider l'envoi", style=discord.ButtonStyle.success, emoji="✅", disabled=True)
    async def valider_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.cart:
            await interaction.response.send_message("Panier vide.", ephemeral=True)
            return
        await interaction.response.send_modal(OperateurModal(self))

    @discord.ui.button(label="Vider", style=discord.ButtonStyle.secondary, emoji="🗑️")
    async def vider_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cart.clear()
        self.refresh_state()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.danger, emoji="❌")
    async def annuler_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="🧾 Saisie cambus", description="Saisie annulée.", color=discord.Color.greyple())
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class SaisieCambusButtonView(discord.ui.View):
    """Vue persistante (survit aux redémarrages du bot) portant le bouton d'ouverture."""

    def __init__(self, resolve_member, on_valider):
        super().__init__(timeout=None)
        self.resolve_member = resolve_member  # callable(user_id: str) -> str | None
        self.on_valider = on_valider          # async callable(interaction, member_name, items, operateur_text) -> bool

    @discord.ui.button(
        label="Faire ma saisie cambus",
        emoji="🧾",
        style=discord.ButtonStyle.primary,
        custom_id="cambus:ouvrir_saisie",
    )
    async def ouvrir_saisie(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_name = self.resolve_member(str(interaction.user.id))
        if member_name is None:
            await interaction.response.send_message(
                "⚠️ Ton pseudo Discord n'est pas enregistré pour la cambus.\n"
                "Demande à l'admin de t'ajouter.",
                ephemeral=True,
            )
            return

        cart_view = CartView(member_name=member_name, on_valider=self.on_valider)
        await interaction.response.send_message(
            embed=cart_view.build_embed(), view=cart_view, ephemeral=True
        )
