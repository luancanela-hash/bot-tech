import os
import asyncio
import threading
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

# --- DICIONÁRIO PARA CONTROLAR SALAS OCUPADAS ---
SALAS_EM_USO = {}

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

    @button(label="🔍 Pesquisar Jogo", style=discord.ButtonStyle.success, custom_id="btn_search_game", row=2)
    async def btn_pesquisar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalPesquisa())

    @button(label="❌ Limpar Busca", style=discord.ButtonStyle.danger, custom_id="btn_clear_search", disabled=True, row=2)
    async def btn_limpar_busca(self, interaction: discord.Interaction, button: Button):
        nova_view = DropdownView(pagina=1, termo_busca=None)
        await interaction.response.edit_message(view=nova_view)


# --- MODAL PARA DEFINIR JOGO / ATIVIDADE ---

class ModalDefinirJogo(Modal, title="🎮 Definir Jogo / Atividade"):
    nome_jogo = TextInput(
        label="Jogo ou Atividade em exibição",
        placeholder="Ex: Call of Duty, Valorant, Resenha...",
        required=True,
        max_length=80
    )

    async def on_submit(self, interaction: discord.Interaction):
        view: StreamDonoView = self.view
        view.stream_publico_view.jogo_atual = self.nome_jogo.value
        await view.stream_publico_view.atualizar_embed_publico(interaction)


# --- VIEW PÚBLICA (ESPECTADORES) ---

class StreamPublicoView(View):
    def __init__(self, author_id: int, sala_id: str, url_sala: str, dados_sala: dict):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.sala_id = sala_id
        self.url_sala = url_sala
        self.dados_sala = dados_sala
        
        self.jogo_atual = "Não especificado"
        self.horas_totais = 3
        self.tempo_encerramento = datetime.now(timezone.utc) + timedelta(hours=3)
        self.msg_publica = None
        self.msg_dono = None

        # Botão exclusivo "Assistir live"
        self.add_item(Button(
            label="Assistir live",
            url=url_sala,
            style=discord.ButtonStyle.link,
            emoji="👀",
            row=0
        ))

    async def atualizar_embed_publico(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"{self.dados_sala['emoji']} TRANSMISSÃO INICIADA POR:",
            description=(
                f"🎮 <@{self.author_id}> acabou de iniciar uma transmissão na **{self.dados_sala['nome']}**!\n\n"
                f"🕹️ **Transmitindo:** `{self.jogo_atual}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Clique no botão **Assistir live** abaixo para entrar no espaço."
            ),
            color=self.dados_sala["cor"]
        )
        if self.msg_publica:
            await self.msg_publica.edit(embed=embed, view=self)


# --- VIEW CONTROLE (DONO DA SALA / ADMIN) ---

class StreamDonoView(View):
    def __init__(self, stream_publico_view: StreamPublicoView):
        super().__init__(timeout=None)
        self.stream_publico_view = stream_publico_view

    async def atualizar_embed_dono(self, interaction: discord.Interaction):
        timestamp_unix = int(self.stream_publico_view.tempo_encerramento.timestamp())
        embed_dono = discord.Embed(
            description=(
                f"🛠️ **Funções do Dono da Sala (<@{self.stream_publico_view.author_id}>):**\n\n"
                f"⏳ **Encerramento Previsto:** <t:{timestamp_unix}:R> *(para estender a duração da live, utilize o botão **Prorrogar (+1h)** abaixo)*.\n"
                f"🎮 **Seu jogo:** *(caso queira definir o nome do jogo em exibição, utilize o botão **Definir Jogo** abaixo)*."
            ),
            color=self.stream_publico_view.dados_sala["cor"]
        )
        await interaction.response.edit_message(embed=embed_dono, view=self)

    @button(label="Definir Jogo", style=discord.ButtonStyle.primary, emoji="🎮", custom_id="btn_definir_jogo_stream", row=0)
    async def btn_definir_jogo(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id != self.stream_publico_view.author_id and not is_admin:
            return await interaction.response.send_message(
                f"⚠️ Apenas <@{self.stream_publico_view.author_id}> dono da sala (ou um Administrador) que iniciou esta transmissão pode alterar o jogo!",
                ephemeral=True,
                delete_after=5
            )
        
        modal = ModalDefinirJogo()
        modal.view = self
        await interaction.response.send_modal(modal)

    @button(label="Prorrogar (+1h)", style=discord.ButtonStyle.success, emoji="⏱️", custom_id="btn_prorrogar_stream", row=0)
    async def btn_prorrogar(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id != self.stream_publico_view.author_id and not is_admin:
            return await interaction.response.send_message(
                f"⚠️ Apenas <@{self.stream_publico_view.author_id}> dono da sala (ou um Administrador) que iniciou esta transmissão pode prorrogar a duração!",
                ephemeral=True,
                delete_after=5
            )

        if self.stream_publico_view.horas_totais >= 5:
            return await interaction.response.send_message("⚠️ A transmissão já atingiu o limite máximo permitido de **5 horas**!", ephemeral=True, delete_after=5)

        self.stream_publico_view.horas_totais += 1
        self.stream_publico_view.tempo_encerramento += timedelta(hours=1)
        await self.atualizar_embed_dono(interaction)
        await interaction.followup.send("⏱️ Transmissão prorrogada em +1 hora com sucesso!", ephemeral=True, delete_after=3)

    @button(label="Encerrar Transmissão", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="btn_fechar_stream_publico", row=0)
    async def fechar_stream(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False

        if interaction.user.id != self.stream_publico_view.author_id and not is_admin:
            return await interaction.response.send_message(
                f"⚠️ Apenas <@{self.stream_publico_view.author_id}> dono da sala (ou um Administrador) que iniciou esta transmissão pode encerrá-la!",
                ephemeral=True,
                delete_after=5
            )

        sala_id = self.stream_publico_view.sala_id
        if sala_id in SALAS_EM_USO:
            del SALAS_EM_USO[sala_id]

        try:
            if self.stream_publico_view.msg_publica:
                await self.stream_publico_view.msg_publica.delete()
            if self.stream_publico_view.msg_dono:
                await self.stream_publico_view.msg_dono.delete()
            await interaction.response.send_message("🛑 Transmissão encerrada com sucesso!", ephemeral=True, delete_after=3)
        except Exception:
            await interaction.response.send_message("❌ Não foi possível apagar a mensagem.", ephemeral=True, delete_after=3)


# --- VIEW PRIVADA DA SALA PRONTA ---

class StreamPrivadoView(View):
    def __init__(self, url_sala: str):
        super().__init__(timeout=120)
        self.add_item(Button(
            label="Abrir sua live",
            url=url_sala,
            style=discord.ButtonStyle.link,
            emoji="🚀"
        ))


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

        if sala_id in SALAS_EM_USO:
            dono_atual_id = SALAS_EM_USO[sala_id]
            return await interaction.response.send_message(
                f"⚠️ Esta sala já está sendo usada pelo(a) <@{dono_atual_id}>! Escolha outra sala disponível.",
                ephemeral=True,
                delete_after=10
            )

        SALAS_EM_USO[sala_id] = interaction.user.id

        # 1. Instancia as views
        view_publica = StreamPublicoView(
            author_id=interaction.user.id,
            sala_id=sala_id,
            url_sala=dados_sala['url'],
            dados_sala=dados_sala
        )
        view_dono = StreamDonoView(stream_publico_view=view_publica)

        # 2. Envia a Mensagem Pública (Anúncio da Live + Assistir)
        embed_publico = discord.Embed(
            title=f"{dados_sala['emoji']} TRANSMISSÃO INICIADA POR:",
            description=(
                f"🎮 {interaction.user.mention} acabou de iniciar uma transmissão na **{dados_sala['nome']}**!\n\n"
                f"🕹️ **Transmitindo:** `Não especificado`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"Clique no botão **Assistir live** abaixo para entrar no espaço."
            ),
            color=dados_sala["cor"]
        )

        msg_publica = await interaction.channel.send(
            embed=embed_publico,
            view=view_publica,
            delete_after=18000
        )
        view_publica.msg_publica = msg_publica

        # 3. Envia a Segunda Mensagem (Embed dedicado às Funções do Dono da Sala)
        timestamp_unix = int(view_publica.tempo_encerramento.timestamp())
        embed_dono = discord.Embed(
            description=(
                f"🛠️ **Funções do Dono da Sala ({interaction.user.mention}):**\n\n"
                f"⏳ **Encerramento Previsto:** <t:{timestamp_unix}:R> *(para estender a duração da live, utilize o botão **Prorrogar (+1h)** abaixo)*.\n"
                f"🎮 **Seu jogo:** *(caso queira definir o nome do jogo em exibição, utilize o botão **Definir Jogo** abaixo)*."
            ),
            color=dados_sala["cor"]
        )

        msg_dono = await interaction.channel.send(
            embed=embed_dono,
            view=view_dono,
            delete_after=18000
        )
        view_publica.msg_dono = msg_dono

        # Limpeza automatizada
        async def limpar_sala_expirada():
            await asyncio.sleep(18000)
            if sala_id in SALAS_EM_USO and SALAS_EM_USO[sala_id] == interaction.user.id:
                del SALAS_EM_USO[sala_id]
            try:
                await msg_publica.delete()
                await msg_dono.delete()
            except Exception:
                pass

        asyncio.create_task(limpar_sala_expirada())

        # 4. Aviso privado para quem iniciou a live
        embed_privado = discord.Embed(
            title=f"🚀 {interaction.user.display_name}, S U A  S A L A  E S T Á  P R O N T A !",
            description=(
                f"{dados_sala['emoji']} **Entre na sala, compartilhe a sua tela e divirta-se com o pessoal!**"
            ),
            color=dados_sala["cor"]
        )
        embed_privado.set_footer(text="Esta mensagem privada desaparecerá automaticamente após 2 minutos.")

        await interaction.response.send_message(
            embed=embed_privado,
            view=StreamPrivadoView(url_sala=dados_sala['url']),
            ephemeral=True,
            delete_after=120
        )

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
    except Exception:
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
    except Exception:
        pass
        
    embed = discord.Embed(
        title="🖥️ Painel de Transmissões - Tech Ninjas",
        description="Para transmitir sua tela para seus amigos selecione uma sala abaixo:",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, view=StreamPainelView())

@bot.command()
@commands.has_permissions(administrator=True)
async def comandos(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🛠️ Painel de Ajuda - Comandos do Administrador",
        description="Aqui tem a lista de todos os comandos administrativos disponíveis no bot:",
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
