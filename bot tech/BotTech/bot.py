import os
import asyncio
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View, button, Button

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

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

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
            options.append(discord.SelectOption(label="Nenhum jogo disponível nesta página", value="none"))

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
            return await interaction.response.send_message("Nenhum jogo disponível nesta página.", ephemeral=True)

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

        # Função para resetar o menu suspenso após 60 segundos
        async def resetar_menu():
            await asyncio.sleep(60)
            try:
                view_atualizada = DropdownView(pagina=self.view.pagina)
                await interaction.message.edit(view=view_atualizada)
            except Exception:
                pass  # Ignora caso a mensagem tenha sido apagada

        asyncio.create_task(resetar_menu())

class DropdownView(View):
    def __init__(self, pagina=1):
        super().__init__(timeout=None)
        self.pagina = pagina
        self.tamanho_pagina = 25
        
        if os.path.exists(PASTA_TORRENTS):
            self.arquivos = sorted([f for f in os.listdir(PASTA_TORRENTS) if f.endswith('.torrent')])
        else:
            self.arquivos = []

        self.total_paginas = max(1, (len(self.arquivos) + self.tamanho_pagina - 1) // self.tamanho_pagina)
        if self.pagina > self.total_paginas:
            self.pagina = self.total_paginas

        inicio = (self.pagina - 1) * self.tamanho_pagina
        fim = inicio + self.tamanho_pagina
        bloco = self.arquivos[inicio:fim]

        # Adiciona o menu dropdown dos jogos da página atual
        self.add_item(DropdownJogos(bloco, self.pagina))

        # Atualiza o estado dos botões de navegação
        self.btn_anterior.disabled = (self.pagina <= 1)
        self.btn_proximo.disabled = (self.pagina >= self.total_paginas)
        self.btn_indicador.label = f"Página {self.pagina}/{self.total_paginas}"

    @button(label="◀️ Anterior", style=discord.ButtonStyle.primary, custom_id="btn_prev_page")
    async def btn_anterior(self, interaction: discord.Interaction, button: Button):
        if self.pagina > 1:
            self.pagina -= 1
            nova_view = DropdownView(self.pagina)
            await interaction.response.edit_message(view=nova_view)

    @button(label="Página 1/1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="btn_page_indicator")
    async def btn_indicador(self, interaction: discord.Interaction, button: Button):
        pass

    @button(label="Próximo ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next_page")
    async def btn_proximo(self, interaction: discord.Interaction, button: Button):
        if self.pagina < self.total_paginas:
            self.pagina += 1
            nova_view = DropdownView(self.pagina)
            await interaction.response.edit_message(view=nova_view)

@bot.event
async def on_ready():
    bot.add_view(DropdownView())
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
        description="Escolha o jogo no menu suspenso abaixo para receber o arquivo `.torrent` diretamente em uma mensagem privada. Use os botões abaixo para navegar pelas páginas.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=DropdownView(pagina=1))

bot.run(TOKEN)
