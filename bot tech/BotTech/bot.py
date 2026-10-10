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

# --- MAPA DE SALAS KOSMI COM CORES E EMOJIS DIFERENTES ---
SALAS_KOSMI = {
    "1": {
        "nome": "Tech Ninjas Live [1]",
        "url": "https://app.kosmi.io/room/e8az5s",
        "emoji": "🔴",
        "cor": discord.Color.red()
    },
    "2": {
        "nome": "Tech Ninjas Live [2]",
        "url": "https://app.kosmi.io/room/w276in",
        "emoji": "🔵",
        "cor": discord.Color.blue()
    },
    "3": {
        "nome": "Tech Ninjas Live [3]",
        "url": "https://app.kosmi.io/room/je33qq",
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

    # Linha 1: Botões de navegação
    @button(label="◀️ Anterior", style=discord.ButtonStyle.primary, custom_id="btn_prev_page", row=1)
    async def btn_anterior(self, interaction: discord.Interaction, button: Button):
        if self.pagina > 1:
            self.pagina -= 1
            nova_view = DropdownView(self.pagina, self.termo_busca)
            await interaction.response.edit_message(view=nova_view)

    @button(label="Página 1/1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="btn_page_indicator", row=1)
    async def btn_indicador(self, interaction: discord.Interaction, button: Button):
        pass

    @button(label="Próximo ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next_page", row=1)
    async def btn_proximo(self, interaction: discord.Interaction, button: Button):
        if self.pagina < self.total_paginas:
            self.pagina += 1
            nova_view = DropdownView(self.pagina, self.termo_busca)
            await interaction.response.edit_message(view=nova_view)

    # Linha 2: Botões de pesquisa e limpeza
    @button(label="🔍 Pesquisar Jogo", style=discord.ButtonStyle.success, custom_id="btn_search_game", row=2)
    async def btn_pesquisar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalPesquisa())

    @button(label="❌ Limpar Busca", style=discord.ButtonStyle.danger, custom_id="btn_clear_search", disabled=True, row=2)
    async def btn_limpar_busca(self, interaction: discord.Interaction, button: Button):
        nova_view = DropdownView(pagina=1, termo_busca=None)
        await interaction.response.edit_message(view=nova_view)


# --- BOTÃO PARA ENCERRAR A TRANSMISSÃO (APENAS O STREAMER OU ADMIN) ---

class StreamAvisoView(View):
    def __init__(self, author_id: int):
        super().__init__(timeout=7200)
        self.author_id = author_id

    @button(label="⏹️ Encerrar Transmissão", style=discord.ButtonStyle.danger, custom_id="btn_fechar_stream_aviso")
    async def fechar_stream(self, interaction: discord.Interaction, button: Button):
        # Verifica se quem clicou é o streamer original ou um Administrador do servidor
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False

        if interaction.user.id != self.author_id and not is_admin:
            return await interaction.response.send_message(
                "⚠️ Apenas o utilizador que iniciou esta transmissão (ou um Administrador) pode encerrá-la!",
                ephemeral=True,
                delete_after=5
            )

        try:
            await interaction.message.delete()
            await interaction.response.send_message("🛑 Transmissão encerrada e aviso removido com sucesso!", ephemeral=True, delete_after=3)
        except Exception:
            await interaction.response.send_message("❌ Não foi possível apagar a mensagem.", ephemeral=True, delete_after=3)


# --- PAINEL E SELETOR DE SALAS DE TRANSMISSÃO ---

class SelectSalaKosmi(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label=SALAS_KOSMI[s]["nome"],
                description=f"Iniciar transmissão na sala {s}",
                emoji=SALAS_KOSMI[s]["emoji"],
                value=s
            ) for s in SALAS_KOSMI
        ]
        super().__init__(
            placeholder="Selecione a sala para iniciar transmissão...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_sala_kosmi_fixo"
        )

    async def callback(self, interaction: discord.Interaction):
        sala_id = self.values[0]
        dados_sala = SALAS_KOSMI.get(sala_id)

        if not dados_sala:
            return await interaction.response.send_message("❌ Sala não encontrada.", ephemeral=True)

        embed = discord.Embed(
            title=f"{dados_sala['emoji']} Transmissão Iniciada ({dados_sala['nome']})!",
            description=f"O utilizador **{interaction.user.name}** começou uma transmissão em direto!\n\n"
                        f"🔗 **Clica no link abaixo para assistir:**\n"
                        f"[Entrar em {dados_sala['nome']}]({dados_sala['url']})",
            color=dados_sala["cor"]
        )
        embed.set_footer(text="Clica no botão abaixo para encerrar ou a mensagem apagará automaticamente após 2 horas.")
        
        # Passa o ID do utilizador que iniciou a transmissão para a View do aviso
        await interaction.channel.send(
            embed=embed,
            view=StreamAvisoView(author_id=interaction.user.id),
            delete_after=7200
        )
        await interaction.response.send_message(f"✅ Aviso enviado para a **{dados_sala['nome']}** com sucesso!", ephemeral=True, delete_after=3)

        async def resetar_painel_stream():
            await asyncio.sleep(15)
            try:
                await interaction.message.edit(view=StreamPainelView())
            except Exception:
                pass

        asyncio.create_task(resetar_painel_stream())

class StreamPainelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelectSalaKosmi())


# --- EVENTOS E COMANDOS DO BOT ---

@bot.event
async def on_ready():
    bot.add_view(DropdownView())
    bot.add_view(StreamPainelView())
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
        description="Escolha o jogo no menu suspenso abaixo para receber o arquivo `.torrent` diretamente em uma mensagem privada.\n\nUse os botões ◀️▶️ para navegar pelas páginas ou clique em 🔍 Pesquisar Jogo para buscar diretamente.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=DropdownView(pagina=1))

@bot.command()
@commands.has_permissions(administrator=True)
async def painel_stream(ctx):
    try:
        await ctx.message.delete()
    except:
        pass
        
    embed = discord.Embed(
        title="🖥️ Painel de Transmissões - Tech Ninjas",
        description="Para transmitir sua tela para seus amigos selecione uma sala abaixo:",
        color=discord.Color.purple()
    )
    await ctx.send(embed=embed, view=StreamPainelView())

@bot.command()
@commands.has_permissions(administrator=True)
async def comandos(ctx):
    try:
        await ctx.message.delete()
    except:
        pass

    embed = discord.Embed(
        title="🛠️ Painel de Ajuda - Comandos do Administrador",
        description="Aqui tens a lista de todos os comandos administrativos disponíveis no bot:",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="`!enviar_menu`",
        value="Envia o painel interativo de seleção de Jogos Co-op com suporte a paginação e pesquisa de arquivos `.torrent`.",
        inline=False
    )
    embed.add_field(
        name="`!painel_stream`",
        value="Envia o painel limpo com a descrição e o menu suspenso para iniciar avisos de transmissão.",
        inline=False
    )
    embed.add_field(
        name="`!comandos`",
        value="Mostra esta lista de ajuda administrativa.",
        inline=False
    )
    embed.set_footer(text="Esta mensagem desaparecerá automaticamente após 30 segundos.")

    await ctx.send(embed=embed, delete_after=30)

bot.run(TOKEN)
