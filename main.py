import discord
from discord import app_commands
import json
import os
import threading
import io
from datetime import datetime

# ==================== CONFIGURAZIONE SERVER & LOG ====================
GUILD_ID = discord.Object(id=1219336770835976302)

LOG_CHANNEL_MATRICOLE_PUBLIC = 1502245107716329632  # Canale matricole visibile a tutti
LOG_CHANNEL_MATRICOLE_LOGS   = 1545705022359343197  # Canale log riservato ai Direttori

LOG_CHANNEL_RIMOZIONI = 1545745750619856997  # Log per QUALSIASI RIMOZIONE
LOG_CHANNEL_AGGIUNTE  = 1545745781892321351  # Log per QUALSIASI AGGIUNTA / CRAFT

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
file_lock = threading.Lock()

DEV_CREDIT = "Developed By andreeee.07"

# ==================== GESTIONE DATA.JSON SICURA ====================

def load_data():
    with file_lock:
        if not os.path.exists(DATA_FILE):
            default_data = {
                "deposito_minerali": {
                    "Argento": 0, "Carbone": 0, "Diamante": 0,
                    "Ferro": 0, "Legno": 0, "Oro": 0,
                    "Pietra": 0, "Rubino": 0, "Smeraldo": 0
                },
                "deposito_prodotti": {},
                "deposito_cibo": {
                    "Cibo": 0,
                    "Bere": 0
                },
                "matricole": [],
                "deposito_msg_id": None,
                "deposito_channel_id": None,
                "prodotti_msg_id": None,
                "prodotti_channel_id": None,
                "cibo_msg_id": None,
                "cibo_channel_id": None
            }
            try:
                with open(DATA_FILE, "w", encoding="utf-8") as f:
                    json.dump(default_data, f, indent=4)
            except Exception as e:
                print(f"Errore creazione data.json: {e}")
            return default_data

        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "deposito_minerali" not in data and "deposito" in data:
                    data["deposito_minerali"] = data.pop("deposito")
                elif "deposito_minerali" not in data:
                    data["deposito_minerali"] = {
                        "Argento": 0, "Carbone": 0, "Diamante": 0,
                        "Ferro": 0, "Legno": 0, "Oro": 0,
                        "Pietra": 0, "Rubino": 0, "Smeraldo": 0
                    }
                if "deposito_prodotti" not in data:
                    data["deposito_prodotti"] = {}
                if "deposito_cibo" not in data:
                    data["deposito_cibo"] = {"Cibo": 0, "Bere": 0}
                if "matricole" not in data:
                    data["matricole"] = []
                for key in ["deposito_msg_id", "deposito_channel_id", "prodotti_msg_id", "prodotti_channel_id", "cibo_msg_id", "cibo_channel_id"]:
                    if key not in data:
                        data[key] = None
                return data
        except Exception as e:
            print(f"Errore lettura data.json: {e}")
            return {
                "deposito_minerali": {},
                "deposito_prodotti": {},
                "deposito_cibo": {"Cibo": 0, "Bere": 0},
                "matricole": [],
                "deposito_msg_id": None, "deposito_channel_id": None,
                "prodotti_msg_id": None, "prodotti_channel_id": None,
                "cibo_msg_id": None, "cibo_channel_id": None
            }

def save_data(data):
    with file_lock:
        try:
            temp_file = DATA_FILE + ".tmp"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            os.replace(temp_file, DATA_FILE)
        except Exception as e:
            print(f"Errore salvataggio data.json: {e}")

def trova_chiave_case_insensitive(dizionario, cerca):
    for k in dizionario.keys():
        if k.lower() == cerca.lower():
            return k
    return None

# ==================== STRUTTURA BOT ====================

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        self.add_view(MatricolaView())
        self.add_view(RegistroSupervisoreView())
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)
        print(f"✅ Bot pronto e comandi sincronizzati per il server {GUILD_ID.id}")

client = MyClient()

@client.event
async def on_ready():
    print(f"🤖 Bot connesso con successo come {client.user}")

# ==================== FUNZIONI EMBED ====================

def genera_embed_deposito(deposito):
    embed = discord.Embed(
        title="⛏️ Deposito Craft (Minerali)",
        description="Ecco i minerali attualmente disponibili:",
        color=discord.Color.gold()
    )
    for minerale, qta in deposito.items():
        embed.add_field(name=f"⛏️ {minerale}", value=f"{qta}x", inline=True)
    embed.set_footer(text=DEV_CREDIT)
    return embed

def genera_embed_prodotti(prodotti):
    embed = discord.Embed(
        title="📦 Deposito",
        description="Ecco il contenuto attuale del deposito:",
        color=discord.Color.gold()
    )
    for prod, qta in prodotti.items():
        if qta > 0:
            embed.add_field(name=f"• {prod}", value=f"{qta}", inline=False)
    if not any(qta > 0 for qta in prodotti.values()):
        embed.add_field(name="Stato", value="Il deposito è attualmente vuoto.", inline=False)
    embed.set_footer(text=DEV_CREDIT)
    return embed

def genera_embed_cibo(cibo_data):
    embed = discord.Embed(
        title="📦 Deposito",
        description="Ecco il contenuto attuale del deposito:",
        color=discord.Color.gold()
    )
    for voce, qta in cibo_data.items():
        embed.add_field(name=f"• {voce}", value=f"{qta}", inline=False)
    embed.set_footer(text=DEV_CREDIT)
    return embed

async def aggiorna_messaggio_deposito(data):
    msg_id = data.get("deposito_msg_id")
    channel_id = data.get("deposito_channel_id")
    if msg_id and channel_id:
        channel = client.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = genera_embed_deposito(data["deposito_minerali"])
                await msg.edit(embed=embed)
            except Exception as e:
                print(f"Impossibile aggiornare deposito minerali: {e}")

async def aggiorna_messaggio_prodotti(data):
    msg_id = data.get("prodotti_msg_id")
    channel_id = data.get("prodotti_channel_id")
    if msg_id and channel_id:
        channel = client.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = genera_embed_prodotti(data["deposito_prodotti"])
                await msg.edit(embed=embed)
            except Exception as e:
                print(f"Impossibile aggiornare deposito prodotti: {e}")

async def aggiorna_messaggio_cibo(data):
    msg_id = data.get("cibo_msg_id")
    channel_id = data.get("cibo_channel_id")
    if msg_id and channel_id:
        channel = client.get_channel(channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                embed = genera_embed_cibo(data["deposito_cibo"])
                await msg.edit(embed=embed)
            except Exception as e:
                print(f"Impossibile aggiornare deposito cibo: {e}")

# ==================== PREZZI & RICETTE ====================

MATERIAL_PRICES = {
    "Legno": 180, "Pietra": 170, "Carbone": 230,
    "Ferro": 280, "Argento": 340, "Rubino": 400,
    "Oro": 450, "Smeraldo": 510, "Diamante": 570
}

RECIPES = {
    "Pistola 9mm": {"quantita": 1, "materiali": {"Oro": 14, "Rubino": 28, "Argento": 42, "Ferro": 64}},
    "Pistola SNS": {"quantita": 1, "materiali": {"Oro": 8, "Rubino": 19, "Argento": 26, "Ferro": 39}},
    "Pistola Pesante": {"quantita": 1, "materiali": {"Carbone": 13, "Oro": 19, "Rubino": 37, "Argento": 55, "Ferro": 89}},
    "Pistola MK2": {"quantita": 1, "materiali": {"Smeraldo": 12, "Carbone": 18, "Oro": 26, "Rubino": 44, "Argento": 66, "Ferro": 106}},
    "Taser": {"quantita": 1, "materiali": {"Carbone": 9, "Rubino": 11, "Argento": 16, "Ferro": 25}},
    "Silenziatore Base": {"quantita": 1, "materiali": {"Oro": 3, "Rubino": 8, "Argento": 15, "Ferro": 20}},
    "Caricatore Esteso": {"quantita": 1, "materiali": {"Pietra": 7, "Carbone": 10, "Ferro": 15}},
    "Torcia Arma": {"quantita": 1, "materiali": {"Pietra": 5, "Carbone": 5, "Ferro": 10}},
    "Giubbotto": {"quantita": 1, "materiali": {"Pietra": 10, "Carbone": 10, "Ferro": 15}},
    "Mazza da Baseball": {"quantita": 1, "materiali": {"Pietra": 11, "Legno": 20}},
    "Coltello": {"quantita": 1, "materiali": {"Carbone": 7, "Pietra": 10, "Ferro": 17}},
    "Colpi 9mm": {"quantita": 1, "materiali": {"Carbone": 2, "Ferro": 4}},
    "Munizioni .45 ACP": {"quantita": 1, "materiali": {"Ferro": 2, "Carbone": 4}}
}

# ==================== REGISTRAZIONE MATRICOLA ====================

class MatricolaModal(discord.ui.Modal):
    def __init__(self, arma_nome: str):
        super().__init__(title=f"Registrazione - {arma_nome}")
        self.arma_nome = arma_nome

        self.nome = discord.ui.TextInput(label="Nome", placeholder="Inserisci il nome...", required=True)
        self.cognome = discord.ui.TextInput(label="Cognome", placeholder="Inserisci il cognome...", required=True)
        self.data_nascita = discord.ui.TextInput(label="Data di Nascita", placeholder="GG/MM/AAAA", required=True)
        self.matricola = discord.ui.TextInput(label="Matricola Pistola", placeholder="Inserisci la matricola...", required=True)

        self.add_item(self.nome)
        self.add_item(self.cognome)
        self.add_item(self.data_nascita)
        self.add_item(self.matricola)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        
        nome_formattato = self.nome.value.strip().upper()
        cognome_formattato = self.cognome.value.strip().upper()
        proprietario_completo = f"{nome_formattato} {cognome_formattato}"
        
        record = {
            "utente": str(interaction.user),
            "arma": self.arma_nome,
            "proprietario": proprietario_completo,
            "data_nascita": self.data_nascita.value,
            "matricola": self.matricola.value,
            "data": datetime.now().strftime("%d/%m/%Y %H:%M")
        }
        data["matricole"].append(record)
        save_data(data)

        await interaction.followup.send("✅ Registrazione inviata con successo!", ephemeral=True)

        data_ora = datetime.now().strftime("%d/%m/%Y %H:%M")

        if LOG_CHANNEL_MATRICOLE_PUBLIC != 0:
            ch_pub = interaction.guild.get_channel(LOG_CHANNEL_MATRICOLE_PUBLIC)
            if ch_pub:
                embed_pub = discord.Embed(title="✅ Registrazione Arma", color=discord.Color.blue())
                embed_pub.add_field(name="👤 Proprietario", value=proprietario_completo, inline=True)
                embed_pub.add_field(name="🔫 Modello", value=self.arma_nome, inline=True)
                embed_pub.add_field(name="🔢 Matricola", value=f"`{self.matricola.value}`", inline=True)
                embed_pub.set_footer(text=f"Ufficiale: {interaction.user.name} • {data_ora}")
                await ch_pub.send(embed=embed_pub)

        if LOG_CHANNEL_MATRICOLE_LOGS != 0:
            ch_logs = interaction.guild.get_channel(LOG_CHANNEL_MATRICOLE_LOGS)
            if ch_logs:
                embed_log = discord.Embed(title="📋 LOG - NUOVA MATRICOLA", color=discord.Color.dark_embed())
                embed_log.add_field(name="🔫 Arma", value=self.arma_nome, inline=False)
                embed_log.add_field(name="🔢 Matricola", value=f"`{self.matricola.value}`", inline=True)
                embed_log.add_field(name="👤 Nome", value=self.nome.value.strip().capitalize(), inline=True)
                embed_log.add_field(name="👤 Cognome", value=self.cognome.value.strip().capitalize(), inline=True)
                embed_log.add_field(name="🎂 Data di nascita", value=self.data_nascita.value, inline=False)
                embed_log.add_field(name="🛡️ Registrata da", value=interaction.user.mention, inline=False)
                embed_log.set_footer(text=f"{DEV_CREDIT} • {data_ora}")
                await ch_logs.send(embed=embed_log)

class MatricolaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Pistola Pesante", style=discord.ButtonStyle.primary, custom_id="btn_pesante")
    async def pesante(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatricolaModal("Pistola Pesante"))

    @discord.ui.button(label="Pistola 9mm", style=discord.ButtonStyle.primary, custom_id="btn_9mm")
    async def nove_mm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatricolaModal("Pistola 9mm"))

    @discord.ui.button(label="Pistola SNS", style=discord.ButtonStyle.primary, custom_id="btn_sns")
    async def sns(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(MatricolaModal("Pistola SNS"))

# ==================== PANNELLO SUPERVISORE MATRICOLE ====================

class CercaMatricolaModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🔍 Cerca Matricola")
        self.matricola = discord.ui.TextInput(label="Codice Matricola", placeholder="Inserisci il codice da cercare...", required=True)
        self.add_item(self.matricola)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        cerca = self.matricola.value.strip().lower()
        
        risultati = [r for r in data.get("matricole", []) if r.get("matricola", "").lower() == cerca]
        
        if not risultati:
            return await interaction.followup.send(f"❌ Nessuna arma trovata con la matricola `{self.matricola.value}`.", ephemeral=True)
        
        rec = risultati[0]
        embed = discord.Embed(title="🔍 Esito Ricerca Matricola", color=discord.Color.blue())
        embed.add_field(name="🔢 Matricola", value=f"`{rec.get('matricola')}`", inline=True)
        embed.add_field(name="🔫 Arma", value=rec.get('arma'), inline=True)
        embed.add_field(name="👤 Proprietario", value=rec.get('proprietario'), inline=False)
        embed.add_field(name="🎂 Data Nascita", value=rec.get('data_nascita', 'N/D'), inline=True)
        embed.add_field(name="📅 Data Registrazione", value=rec.get('data', 'N/D'), inline=True)
        embed.add_field(name="🛡️ Registrata da", value=rec.get('utente', 'N/D'), inline=False)
        embed.set_footer(text=DEV_CREDIT)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class RimuoviMatricolaModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="🗑️ Rimuovi Arma da Archivio")
        self.matricola = discord.ui.TextInput(label="Codice Matricola", placeholder="Inserisci la matricola da eliminare...", required=True)
        self.add_item(self.matricola)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        cerca = self.matricola.value.strip().lower()
        
        iniziali = len(data.get("matricole", []))
        data["matricole"] = [r for r in data.get("matricole", []) if r.get("matricola", "").lower() != cerca]
        
        if len(data["matricole"]) == iniziali:
            return await interaction.followup.send(f"❌ Nessun record trovato per la matricola `{self.matricola.value}`.", ephemeral=True)
        
        save_data(data)
        await interaction.followup.send(f"✅ Record per la matricola `{self.matricola.value}` eliminato dall'archivio.", ephemeral=True)

class RegistroSupervisoreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerca Matricola", style=discord.ButtonStyle.primary, emoji="🔍", custom_id="btn_cerca_mat")
    async def cerca(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CercaMatricolaModal())

    @discord.ui.button(label="Esporta Archivio", style=discord.ButtonStyle.secondary, emoji="📁", custom_id="btn_esporta_mat")
    async def esporta(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=False)
        data = load_data()
        matricole = data.get("matricole", [])
        
        if not matricole:
            return await interaction.followup.send("📂 L'archivio matricole è vuoto.", ephemeral=False)
        
        testo = "📁 --- ARCHIVIO GLOBALE MATRICOLE ARMI ---\n"
        testo += "=" * 80 + "\n"
        for m in matricole:
            data_reg = m.get('data', '00/00/0000 00:00')
            mat = m.get('matricola', 'N/D')
            arma = m.get('arma', 'N/D').ljust(18)
            proprietario = m.get('proprietario', 'N/D')
            testo += f"[{data_reg}] {mat} | 🔫 {arma} | {proprietario}\n"
        
        file_bytes = io.BytesIO(testo.encode("utf-8"))
        dis_file = discord.File(file_bytes, filename="archivio_matricole.txt")
        
        await interaction.followup.send("📁 Ecco l'archivio globale delle matricole:", file=dis_file, ephemeral=False)

    @discord.ui.button(label="Rimuovi Arma", style=discord.ButtonStyle.danger, emoji="🗑️", custom_id="btn_rimuovi_mat")
    async def rimuovi(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RimuoviMatricolaModal())

    @discord.ui.button(label="Svuota Database", style=discord.ButtonStyle.danger, emoji="⚠️", custom_id="btn_svuota_mat")
    async def svuota(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        data = load_data()
        data["matricole"] = []
        save_data(data)
        await interaction.followup.send("⚠️ Database delle matricole svuotato con successo.", ephemeral=True)

@client.tree.command(name="pannello_supervisore", description="Mostra il registro di gestione amministrativa delle matricole.")
@app_commands.checks.has_permissions(administrator=True)
async def pannello_supervisore(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🛡️ REGISTRO ARMI - SUPERVISORE",
        description="Accesso amministrativo all'archivio matricole.\n\n🔍 **Cerca**: Trova proprietario tramite matricola.\n📁 **Archivio**: Esporta database completo.\n🗑️ **Rimuovi**: Elimina record specifico.\n⚠️ **Svuota**: Reset totale archivio.",
        color=discord.Color.blue()
    )
    embed.set_footer(text=DEV_CREDIT)
    await interaction.channel.send(embed=embed, view=RegistroSupervisoreView())
    await interaction.followup.send("Pannello supervisore inviato!", ephemeral=True)

@client.tree.command(name="pannello_matricole", description="Mostra il pannello per registrare le matricole delle armi.")
@app_commands.checks.has_permissions(administrator=True)
async def pannello_matricole(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    embed = discord.Embed(
        title="🔫 REGISTRAZIONE MATRICOLE",
        description="Seleziona l'arma utilizzando uno dei pulsanti qui sotto.\nDopo aver selezionato l'arma, verrà aperto un modulo.\n\nSistema Registrazione Matricole",
        color=discord.Color.blue()
    )
    embed.set_footer(text=DEV_CREDIT)
    await interaction.channel.send(embed=embed, view=MatricolaView())
    await interaction.followup.send("Pannello inviato!", ephemeral=True)

# ==================== COMANDI PANNELLI DEPOSITO ====================

@client.tree.command(name="deposito_craft", description="Avvia il pannello del deposito minerali.")
async def deposito_craft(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    embed = genera_embed_deposito(data["deposito_minerali"])
    msg = await interaction.channel.send(embed=embed)
    data["deposito_msg_id"] = msg.id
    data["deposito_channel_id"] = msg.channel.id
    save_data(data)
    await interaction.followup.send("✅ Pannello deposito minerali avviato!", ephemeral=True)

@client.tree.command(name="deposito_vendita", description="Avvia il pannello del deposito prodotti/armi.")
async def deposito_vendita(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    embed = genera_embed_prodotti(data["deposito_prodotti"])
    msg = await interaction.channel.send(embed=embed)
    data["prodotti_msg_id"] = msg.id
    data["prodotti_channel_id"] = msg.channel.id
    save_data(data)
    await interaction.followup.send("✅ Pannello deposito prodotti avviato!", ephemeral=True)

@client.tree.command(name="deposito_cibo", description="Avvia il pannello del deposito cibo e bere.")
async def deposito_cibo(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    embed = genera_embed_cibo(data["deposito_cibo"])
    msg = await interaction.channel.send(embed=embed)
    data["cibo_msg_id"] = msg.id
    data["cibo_channel_id"] = msg.channel.id
    save_data(data)
    await interaction.followup.send("✅ Pannello deposito cibo avviato!", ephemeral=True)

# ==================== COMANDI AGGIUNGI / RIMUOVI MINERALI ====================

@client.tree.command(name="aggiungi_minerali", description="Aggiunge minerali al deposito.")
@app_commands.describe(minerale="Seleziona il minerale", quantita="Quantità da aggiungere")
@app_commands.choices(minerale=[
    app_commands.Choice(name="Argento", value="Argento"), app_commands.Choice(name="Carbone", value="Carbone"),
    app_commands.Choice(name="Diamante", value="Diamante"), app_commands.Choice(name="Ferro", value="Ferro"),
    app_commands.Choice(name="Legno", value="Legno"), app_commands.Choice(name="Oro", value="Oro"),
    app_commands.Choice(name="Pietra", value="Pietra"), app_commands.Choice(name="Rubino", value="Rubino"),
    app_commands.Choice(name="Smeraldo", value="Smeraldo")
])
async def aggiungi_minerali(interaction: discord.Interaction, minerale: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    if quantita <= 0:
        return await interaction.followup.send("Inserisci una quantità maggiore di zero.", ephemeral=True)
    data = load_data()
    chiave_reale = trova_chiave_case_insensitive(data["deposito_minerali"], minerale.value) or minerale.value
    data["deposito_minerali"][chiave_reale] = data["deposito_minerali"].get(chiave_reale, 0) + quantita
    save_data(data)
    await aggiorna_messaggio_deposito(data)
    
    if LOG_CHANNEL_AGGIUNTE != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_AGGIUNTE)
        if ch:
            await ch.send(f"📦 {interaction.user.mention} ha aggiunto **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"✅ Aggiunti **{quantita}x** di **{chiave_reale}**.", ephemeral=True)

@client.tree.command(name="rimuovi_minerali", description="Rimuove minerali dal deposito.")
@app_commands.describe(minerale="Seleziona il minerale", quantita="Quantità da rimuovere")
@app_commands.choices(minerale=[
    app_commands.Choice(name="Argento", value="Argento"), app_commands.Choice(name="Carbone", value="Carbone"),
    app_commands.Choice(name="Diamante", value="Diamante"), app_commands.Choice(name="Ferro", value="Ferro"),
    app_commands.Choice(name="Legno", value="Legno"), app_commands.Choice(name="Oro", value="Oro"),
    app_commands.Choice(name="Pietra", value="Pietra"), app_commands.Choice(name="Rubino", value="Rubino"),
    app_commands.Choice(name="Smeraldo", value="Smeraldo")
])
async def rimuovi_minerali(interaction: discord.Interaction, minerale: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    chiave_reale = trova_chiave_case_insensitive(data["deposito_minerali"], minerale.value)
    attuale = data["deposito_minerali"].get(chiave_reale, 0) if chiave_reale else 0
    if quantita <= 0 or not chiave_reale or quantita > attuale:
        return await interaction.followup.send(f"❌ Quantità non valida o insufficiente (Disponibili: {attuale}x).", ephemeral=True)
    data["deposito_minerali"][chiave_reale] -= quantita
    save_data(data)
    await aggiorna_messaggio_deposito(data)
    
    if LOG_CHANNEL_RIMOZIONI != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_RIMOZIONI)
        if ch:
            await ch.send(f"🗑️ {interaction.user.mention} ha rimosso **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"🔻 Rimossi **{quantita}x** di **{chiave_reale}**.", ephemeral=True)

# ==================== COMANDI AGGIUNGI / RIMUOVI ARMI (PRODOTTI) ====================

LISTA_ARTICOLI_PRODOTTI = [
    app_commands.Choice(name="Pistola 9mm", value="Pistola 9mm"),
    app_commands.Choice(name="Pistola Pesante", value="Pistola Pesante"),
    app_commands.Choice(name="Pistola SNS", value="Pistola SNS"),
    app_commands.Choice(name="Pistola MK2", value="Pistola MK2"),
    app_commands.Choice(name="Coltello", value="Coltello"),
    app_commands.Choice(name="Colpi .45 ACP", value="Colpi .45 ACP"),
    app_commands.Choice(name="Colpi 9mm", value="Colpi 9mm"),
    app_commands.Choice(name="Impugnatura", value="Impugnatura"),
    app_commands.Choice(name="Caricatore Pistola", value="Caricatore Pistola"),
    app_commands.Choice(name="Torcia", value="Torcia"),
    app_commands.Choice(name="Taser", value="Taser"),
    app_commands.Choice(name="Silenziatore Base", value="Silenziatore Base"),
    app_commands.Choice(name="Caricatore Esteso", value="Caricatore Esteso"),
    app_commands.Choice(name="Torcia Arma", value="Torcia Arma"),
    app_commands.Choice(name="Giubbotto", value="Giubbotto"),
    app_commands.Choice(name="Mazza da Baseball", value="Mazza da Baseball")
]

@client.tree.command(name="aggiungi_armi", description="Aggiunge armi o prodotti al deposito vendita.")
@app_commands.describe(articolo="Seleziona l'articolo", quantita="Quantità da aggiungere")
@app_commands.choices(articolo=LISTA_ARTICOLI_PRODOTTI)
async def aggiungi_armi(interaction: discord.Interaction, articolo: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    if quantita <= 0:
        return await interaction.followup.send("Inserisci una quantità maggiore di zero.", ephemeral=True)
    data = load_data()
    
    chiave_reale = trova_chiave_case_insensitive(data["deposito_prodotti"], articolo.value) or articolo.value
    data["deposito_prodotti"][chiave_reale] = data["deposito_prodotti"].get(chiave_reale, 0) + quantita
    save_data(data)
    
    await aggiorna_messaggio_prodotti(data)
    
    if LOG_CHANNEL_AGGIUNTE != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_AGGIUNTE)
        if ch:
            await ch.send(f"📦 {interaction.user.mention} ha aggiunto **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"✅ Aggiunti **{quantita}x** di **{chiave_reale}** al deposito vendita.", ephemeral=True)

@client.tree.command(name="rimuovi_armi", description="Rimuove armi o prodotti dal deposito vendita.")
@app_commands.describe(articolo="Seleziona l'articolo", quantita="Quantità da rimuovere")
@app_commands.choices(articolo=LISTA_ARTICOLI_PRODOTTI)
async def rimuovi_armi(interaction: discord.Interaction, articolo: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    
    chiave_reale = trova_chiave_case_insensitive(data["deposito_prodotti"], articolo.value)
    attuale = data["deposito_prodotti"].get(chiave_reale, 0) if chiave_reale else 0
    
    if quantita <= 0 or not chiave_reale or quantita > attuale:
        return await interaction.followup.send(f"❌ Quantità non valida o insufficiente (Disponibili: {attuale}x).", ephemeral=True)
    
    data["deposito_prodotti"][chiave_reale] -= quantita
    if data["deposito_prodotti"][chiave_reale] <= 0:
        del data["deposito_prodotti"][chiave_reale]
    save_data(data)
    
    await aggiorna_messaggio_prodotti(data)
    
    if LOG_CHANNEL_RIMOZIONI != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_RIMOZIONI)
        if ch:
            await ch.send(f"🗑️ {interaction.user.mention} ha rimosso **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"🔻 Rimossi **{quantita}x** di **{chiave_reale}** dal deposito vendita.", ephemeral=True)

# ==================== COMANDI AGGIUNGI / RIMUOVI CIBO ====================

@client.tree.command(name="aggiungi_cibo", description="Aggiunge cibo o bere al deposito.")
@app_commands.describe(voce="Seleziona Cibo o Bere", quantita="Quantità da aggiungere")
@app_commands.choices(voce=[
    app_commands.Choice(name="Cibo", value="Cibo"),
    app_commands.Choice(name="Bere", value="Bere")
])
async def aggiungi_cibo(interaction: discord.Interaction, voce: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    if quantita <= 0:
        return await interaction.followup.send("Inserisci una quantità maggiore di zero.", ephemeral=True)
    data = load_data()
    chiave_reale = trova_chiave_case_insensitive(data["deposito_cibo"], voce.value) or voce.value
    data["deposito_cibo"][chiave_reale] = data["deposito_cibo"].get(chiave_reale, 0) + quantita
    save_data(data)
    await aggiorna_messaggio_cibo(data)
    
    if LOG_CHANNEL_AGGIUNTE != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_AGGIUNTE)
        if ch:
            await ch.send(f"📦 {interaction.user.mention} ha aggiunto **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"✅ Aggiunti **{quantita}x** di **{chiave_reale}** al deposito.", ephemeral=True)

@client.tree.command(name="rimuovi_cibo", description="Rimuove cibo o bere dal deposito.")
@app_commands.describe(voce="Seleziona Cibo o Bere", quantita="Quantità da rimuovere")
@app_commands.choices(voce=[
    app_commands.Choice(name="Cibo", value="Cibo"),
    app_commands.Choice(name="Bere", value="Bere")
])
async def rimuovi_cibo(interaction: discord.Interaction, voce: app_commands.Choice[str], quantita: int):
    await interaction.response.defer(ephemeral=True)
    data = load_data()
    chiave_reale = trova_chiave_case_insensitive(data["deposito_cibo"], voce.value)
    attuale = data["deposito_cibo"].get(chiave_reale, 0) if chiave_reale else 0
    if quantita <= 0 or not chiave_reale or quantita > attuale:
        return await interaction.followup.send(f"❌ Quantità non valida o insufficiente (Disponibili: {attuale}x).", ephemeral=True)
    data["deposito_cibo"][chiave_reale] -= quantita
    save_data(data)
    await aggiorna_messaggio_cibo(data)
    
    if LOG_CHANNEL_RIMOZIONI != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_RIMOZIONI)
        if ch:
            await ch.send(f"🗑️ {interaction.user.mention} ha rimosso **{quantita}x {chiave_reale}** al deposito.")

    await interaction.followup.send(f"🔻 Rimossi **{quantita}x** di **{chiave_reale}** al deposito.", ephemeral=True)

# ==================== CRAFT OGGETTO ====================

@client.tree.command(name="craft_oggetto", description="Crafta uno o più oggetti scalando i minerali e aggiornando il deposito prodotti.")
@app_commands.describe(oggetto="Seleziona l'oggetto da craftare", quantita="Quantità da craftare (default 1)")
async def craft_oggetto(interaction: discord.Interaction, oggetto: str, quantita: int = 1):
    await interaction.response.defer()
    if quantita <= 0:
        return await interaction.followup.send("Inserisci una quantità valida maggiore di 0.", ephemeral=True)

    data = load_data()
    recipe = RECIPES.get(oggetto)
    if not recipe:
        return await interaction.followup.send("Oggetto non trovato nel listino.", ephemeral=True)

    deposito = data["deposito_minerali"]
    mancanti = []
    req_materials = {}
    resolved_mat_keys = {}
    costo_craft_unitario = 0

    for mat, qta_base in recipe["materiali"].items():
        tot_richiesto = qta_base * quantita
        req_materials[mat] = tot_richiesto
        costo_craft_unitario += qta_base * MATERIAL_PRICES.get(mat, 0)
        
        chiave_mat_reale = trova_chiave_case_insensitive(deposito, mat) or mat
        resolved_mat_keys[mat] = chiave_mat_reale
        
        disponibile = deposito.get(chiave_mat_reale, 0)
        if disponibile < tot_richiesto:
            mancanti.append(f"• **{mat}**: ne servono {tot_richiesto}x (disponibili: {disponibile}x)")

    if mancanti:
        msg = f"❌ **Materiali insufficienti nel deposito per x{quantita}:**\n" + "\n".join(mancanti)
        return await interaction.followup.send(msg, ephemeral=True)

    for mat, tot_richiesto in req_materials.items():
        chiave_mat_reale = resolved_mat_keys[mat]
        deposito[chiave_mat_reale] -= tot_richiesto

    qta_prodotta = recipe['quantita'] * quantita
    chiave_prod = trova_chiave_case_insensitive(data["deposito_prodotti"], oggetto) or oggetto
    data["deposito_prodotti"][chiave_prod] = data["deposito_prodotti"].get(chiave_prod, 0) + qta_prodotta

    save_data(data)

    await aggiorna_messaggio_deposito(data)
    await aggiorna_messaggio_prodotti(data)
    
    if LOG_CHANNEL_AGGIUNTE != 0:
        ch = interaction.guild.get_channel(LOG_CHANNEL_AGGIUNTE)
        if ch:
            await ch.send(f"🛠️ {interaction.user.mention} ha craftato **{qta_prodotta}x {chiave_prod}**.")

    embed = discord.Embed(
        title="🛠️ Craft completato",
        description=f"**{oggetto}**",
        color=discord.Color.from_rgb(46, 204, 113)
    )
    embed.add_field(name="📦 Quantità prodotta:", value=f"`{qta_prodotta}`", inline=False)
    mat_list = "\n".join([f"• **{mat}** ➔ `{qta}x`" for mat, qta in req_materials.items()])
    embed.add_field(name="Materiali utilizzati:", value=mat_list, inline=False)

    costo_totale = costo_craft_unitario * quantita
    costo_formattato = f"${costo_totale:,}".replace(",", ".")
    embed.add_field(name="💸 Costo", value=f"**{costo_formattato}**", inline=False)
    embed.set_footer(text=DEV_CREDIT)

    await interaction.followup.send(embed=embed, ephemeral=False)

@craft_oggetto.autocomplete("oggetto")
async def craft_oggetto_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=name, value=name)
        for name in RECIPES.keys()
        if current.lower() in name.lower()
    ][:25]

client.run(os.getenv("DISCORD_TOKEN"))
