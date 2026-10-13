import os
import asyncio
import threading
import random
from datetime import datetime, timedelta, timezone
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View, button, Button, Modal, TextInput

# --- SERVIDOR WEB DUMMY PARA EVITAR O SLEEP DO RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Tech está online!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_web_server, daemon=True).start()

# --- CÓDIGO DO BOT DO DISCORD ---
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Necessário para ler os membros conectados no canal de voz

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

# --- MAPA DE 5 SALAS KOSMI REVISADO ---
SALAS_KOSMI = {
    "1": {
        "nome": "Tech Ninjas Live [1]",
        "url": "https://app.kosmi.io/room/f8m0ed",
        "emoji": "⭐",
        "cor": discord.Color.teal()
    },
    "2": {
        "nome": "Tech Ninjas Live [2]",
        "url": "https://app.kosmi.io/room/w276in",
        "emoji": "🔵",
        "cor": discord.Color.blue()
    },
    "3": {
        "nome": "Tech Ninjas Live [3]",
        "url": "https://app.kosmi.io/room/obybsv",
        "emoji": "🟢",
        "cor": discord.Color.green()
    },
    "4": {
        "nome": "Tech Ninjas Live [4]",
        "url": "https://app.kosmi.io/room/4t50cc",
        "emoji": "🟡",
        "cor": discord.Color.gold()
    },
    "5": {
        "nome": "Tech Ninjas Live [5]",
        "url": "https://app.kosmi.io/room/ywu834",
        "emoji": "🟣",
        "cor": discord.Color.purple()
    }
}

# --- DICIONÁRIOS DE CONTROLE (SALAS E JOGOS EM USO) ---
SALAS_EM_USO = {}
JOGOS_EM_DOWNLOAD = set()

# --- SISTEMA DE JOGOS CO-OP ---

class DropdownJogos(Select):
    def __init__(self, lista_arquivos, pagina_atual):
        options = []
        for arq in lista_arquivos:
            nome_jogo = arq.replace('.torrent', '')
            options.append(
                discord.SelectOption(
                    label=nome_jogo[:100],
                    description=f"Clique para baixar {nome_jogo}"[:100],
                    emoji="🎮",
                    value=arq
                )
            )

        if not options:
            options.append(discord.SelectOption(label="Nenhum jogo encontrado", value="none"))

        super().__init__(
            placeholder=f"Selecione um jogo (Página {pagina_atual})...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"menu_jogos_dropdown_page_{pagina_atual}"
        )

    async def callback(self, interaction: discord.Interaction):
        nome_arquivo = self.values[0]
        if nome_arquivo == "none":
            await interaction.response.defer()
            return await interaction.channel.send("Nenhum jogo disponível.", delete_after=5)

        if nome_arquivo in JOGOS_EM_DOWNLOAD:
            await interaction.response.defer()
            return await interaction.channel.send(
                f"⚠️ {interaction.user.mention}, o arquivo para este jogo já foi solicitado recentemente e está ativo no chat. Aguarde um instante para solicitar novamente!",
                delete_after=5
            )

        JOGOS_EM_DOWNLOAD.add(nome_arquivo)
        caminho_arquivo = os.path.join(PASTA_TORRENTS, nome_arquivo)

        try:
            arquivo = discord.File(caminho_arquivo)
            await interaction.response.defer()
            
            await interaction.channel.send(
                content=f"📥 {interaction.user.mention} solicitou o arquivo para **{nome_arquivo.replace('.torrent', '')}** (esta mensagem sumirá em 1 minuto):",
                file=arquivo,
                delete_after=60
            )
        except FileNotFoundError:
            await interaction.response.defer()
            await interaction.channel.send(
                content=f"❌ {interaction.user.mention}, o arquivo desse jogo não foi encontrado no servidor.",
                delete_after=5
            )
            JOGOS_EM_DOWNLOAD.discard(nome_arquivo)

        async def liberar_jogo():
            await asyncio.sleep(60)
            JOGOS_EM_DOWNLOAD.discard(nome_arquivo)
            try:
                view_atualizada = DropdownView(pagina=self.view.pagina, termo_busca=self.view.termo_busca)
                await interaction.message.edit(view=view_atualizada)
            except Exception:
                pass

        asyncio.create_task(liberar_jogo())

class ModalPesquisa(Modal, title="🔍 Pesquisar Jogo"):
    termo = TextInput(
        label="Nome do jogo",
        placeholder="Digite parte do nome (ex: Age, Among...)",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        nova_view = DropdownView(pagina=1, termo_busca=self.termo.value)
        await interaction.response.edit_message(view=nova_view)

class DropdownView(View):
    def __init__(self, pagina=1, termo_busca=None):
        super().__init__(timeout=None)
        self.pagina = pagina
        self.tamanho_pagina = 25
        self.termo_busca = termo_busca
        
        if os.path.
