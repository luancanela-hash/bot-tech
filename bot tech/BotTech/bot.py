import os
import asyncio
import threading
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

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

# --- SISTEMA DE JOGOS CO-OP (MANTIDO INTACTO) ---

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
            return await interaction.response.send_message("Nenhum jogo disponível.", ephemeral=True)

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

        async def resetar_menu():
            await asyncio.sleep(60)
            try:
                view_atualizada = DropdownView(pagina=self.view.pagina, termo_busca=self.view.termo_busca)
                await interaction.message.edit(view=view_atualizada)
            except Exception:
                pass

        asyncio.create_task(resetar_menu())

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
        
        if os.path.exists(PASTA_TORRENTS):
            todos_arquivos = sorted([f for f in os.listdir(PASTA_TORRENTS) if f.endswith('.torrent')])
        else:
            todos_arquivos = []

        if self.termo_busca:
            self.arquivos = [f for f in todos_arquivos if self.termo_busca.lower() in f.lower()]
        else:
            self.arquivos = todos_arquivos

        self.total_paginas = max(1, (len(self.arquivos) + self.tamanho_pagina - 1) // self.tamanho_pagina)
        if self.pagina > self.total_paginas:
            self.pagina = self.total_paginas

        inicio = (self.pagina - 1) * self.tamanho_pagina
        fim = inicio + self.tamanho_pagina
        bloco = self.arquivos[inicio:fim]

        self.add_item(DropdownJogos(bloco, self.pagina))

        self.btn_anterior.disabled = (self.pagina <= 1)
        self.btn_proximo.disabled = (self.pagina >= self.total_paginas)
        
        if self.termo_busca:
            self.btn_indicador.label = f"Busca: '{self.termo_busca}' ({len(self.arquivos)})"
            self.btn_limpar_busca.disabled = False
        else:
            self.btn_indicador.label = f"Página {self.pagina}/{self.total_paginas}"
            self.btn_limpar_busca.disabled = True

    @button(label="🔍 Pesquisar Jogo", style=discord.ButtonStyle.success, custom_id="btn_search_game", row=1)
    async def btn_pesquisar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalPesquisa())

    @button(label="❌ Limpar Busca", style=discord.ButtonStyle.danger, custom_id="btn_clear_search", disabled=True, row=1)
    async def btn_limpar_busca(self, interaction: discord.Interaction, button: Button):
        nova_view = DropdownView(pagina=1, termo_busca=None)
        await interaction.response.edit_message(view=nova_view)

    @button(label="◀️ Anterior", style=discord.ButtonStyle.primary, custom_id="btn_prev_page", row=2)
    async def btn_anterior(self, interaction: discord.Interaction, button: Button):
        if self.pagina > 1:
            self.pagina -= 1
            nova_view = DropdownView(self.pagina, self.termo_busca)
            await interaction.response.edit_message(view=nova_view)

    @button(label="Página 1/1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="btn_page_indicator", row=2)
    async def btn_indicador(self, interaction: discord.Interaction, button: Button):
        pass

    @button(label="Próximo ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next_page", row=2)
    async def btn_proximo(self, interaction: discord.Interaction, button: Button):
        if self.pagina < self.total_paginas:
            self.pagina += 1
            nova_view = DropdownView(self.pagina, self.termo_busca)
            await interaction.response.edit_message(view=nova_view)


# --- SISTEMA DE PAINEL DE MÚSICA ---

class ModalTocarMusica(Modal, title="🎵 Tocar Música"):
    termo_musica = TextInput(
        label="Nome ou Link da Música",
        placeholder="Digite o nome da música ou link...",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Envia a mensagem no chat e apaga o aviso efêmero em 3 segundos
        msg = await interaction.channel.send(f"m!play {self.termo_musica.value}")
        await interaction.response.send_message(f"✅ Pedido enviado para: **{self.termo_musica.value}**", ephemeral=True, delete_after=3)
        
        # Opcional: faz a Jockie Music detetar mais facilmente se for necessário, 
        # mas como a Jockie filtra bots, o ideal é digitar diretamente no chat caso ela recuse mensagens de outros bots.

class PainelMusicaView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="🎵 Tocar", style=discord.ButtonStyle.success, custom_id="btn_music_play", row=0)
    async def btn_tocar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalTocarMusica())

    @button(label="⏭️ Pular", style=discord.ButtonStyle.primary, custom_id="btn_music_skip", row=0)
    async def btn_pular(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send("m!skip")
        await interaction.response.send_message("⏭️ Pular enviado!", ephemeral=True, delete_after=2)

    @button(label="⏸️ Pausar/Retomar", style=discord.ButtonStyle.secondary, custom_id="btn_music_pause", row=0)
    async def btn_pausar(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send("m!pause")
        await interaction.response.send_message("⏸️ Pausa enviada!", ephemeral=True, delete_after=2)

    @button(label="📜 Fila", style=discord.ButtonStyle.secondary, custom_id="btn_music_queue", row=1)
    async def btn_fila(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send("m!queue")
        await interaction.response.send_message("📜 Fila solicitada!", ephemeral=True, delete_after=2)

    @button(label="⏹️ Parar", style=discord.ButtonStyle.danger, custom_id="btn_music_stop", row=1)
    async def btn_parar(self, interaction: discord.Interaction, button: Button):
        await interaction.channel.send("m!stop")
        await interaction.response.send_message("⏹️ Stop enviado!", ephemeral=True, delete_after=2)


@bot.event
async def on_ready():
    bot.add_view(DropdownView())
    bot.add_view(PainelMusicaView())
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
        description="Escolha o jogo no menu suspenso abaixo para receber o arquivo `.torrent` diretamente em uma mensagem privada.\n\nUse o botão de próximo ou clique em 🔍 **Pesquisar Jogo** para buscar diretamente.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=DropdownView(pagina=1))

@bot.command()
@commands.has_permissions(administrator=True)
async def painel_musica(ctx):
    # Tenta apagar a mensagem do comando !painel_musica enviada pelo admin
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🎶 Painel de Controlo Musical",
        description="Utilize os botões abaixo para interagir com o bot de música de forma rápida e limpa!",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=PainelMusicaView())

bot.run(TOKEN)
