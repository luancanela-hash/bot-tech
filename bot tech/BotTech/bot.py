import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View

# --- SERVIDOR WEB DUMMY PARA EVITAR O SLEEP DO RENDER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Tech está online!"

def run_web_server():
    # O Render disponibiliza a porta na variável de ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Inicia o servidor web numa thread separada
threading.Thread(target=run_web_server, daemon=True).start()

# --- CÓDIGO DO BOT DO DISCORD ---
TOKEN = os.environ.get("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

class DropdownJogos(Select):
    def __init__(self):
        options = []
        if os.path.exists(PASTA_TORRENTS):
            arquivos = sorted([f for f in os.listdir(PASTA_TORRENTS) if f.endswith('.torrent')])
            for arq in arquivos:
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
            options.append(discord.SelectOption(label="Nenhum jogo disponível", value="none"))

        super().__init__(
            placeholder="Selecione um jogo para baixar...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )

    async def callback(self, interaction: discord.Interaction):
        nome_arquivo = self.values[0]
        if nome_arquivo == "none":
            return await interaction.response.send_message("Nenhum jogo disponível no momento.", ephemeral=True)

        caminho_arquivo = os.path.join(PASTA_TORRENTS, nome_arquivo)

        try:
            arquivo = discord.File(caminho_arquivo)
            await interaction.response.send_message(
                content=f"Aqui está o seu arquivo para **{nome_arquivo.replace('.torrent', '')}** (esta mensagem sumirá em 1 minuto):",
                file=arquivo,
                ephemeral=True,
                delete_after=60
            )
        except FileNotFoundError:
            await interaction.response.send_message(
                content="❌ O arquivo desse jogo não foi encontrado no servidor.",
                ephemeral=True
            )

class DropdownView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.clear_items()
        self.add_item(DropdownJogos())

@bot.event
async def on_ready():
    print(f'Bot online como {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def enviar_menu(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
    
    embed = discord.Embed(
        title="🎮 Jogos Co-op Liberados!",
        description="Escolha o jogo no menu suspenso abaixo para receber o arquivo `.torrent` diretamente em uma mensagem privada.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=DropdownView())

bot.run(TOKEN)
