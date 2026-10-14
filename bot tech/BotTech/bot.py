import os
import asyncio
import threading
import random
from datetime import datetime, timedelta, timezone
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View, button, Button, Modal, TextInput

# --- CONFIGURAÇÃO DO SERVIDOR WEB (RENDER KEEP-ALIVE) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Tech está online e operacional!"

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Inicia o servidor Flask em background
threading.Thread(target=run_web_server, daemon=True).start()

# --- CONFIGURAÇÃO DO BOT DO DISCORD ---
TOKEN = os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

# --- MAPA DE SALAS KOSMI ---
SALAS_KOSMI = {
    "1": {"nome": "Tech Ninjas Live [1]", "url": "https://app.kosmi.io/room/f8m0ed", "emoji": "⭐", "cor": discord.Color.teal()},
    "2": {"nome": "Tech Ninjas Live [2]", "url": "https://app.kosmi.io/room/w276in", "emoji": "🔵", "cor": discord.Color.blue()},
    "3": {"nome": "Tech Ninjas Live [3]", "url": "https://app.kosmi.io/room/obybsv", "emoji": "🟢", "cor": discord.Color.green()},
    "4": {"nome": "Tech Ninjas Live [4]", "url": "https://app.kosmi.io/room/4t50cc", "emoji": "🟡", "cor": discord.Color.gold()},
    "5": {"nome": "Tech Ninjas Live [5]", "url": "https://app.kosmi.io/room/ywu834", "emoji": "🟣", "cor": discord.Color.purple()}
}

# --- CONTROLE DE ESTADO ---
SALAS_EM_USO = {}
JOGOS_EM_DOWNLOAD = set()

# --- SISTEMA DE JOGOS CO-OP ---

class DropdownJogos(Select):
    def __init__(self, lista_arquivos: list, pagina_atual: int):
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
                f"⚠️ {interaction.user.mention}, o arquivo para este jogo já foi solicitado recentemente e está ativo no chat. Aguarde um instante!",
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
        placeholder="Digite parte do nome...",
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
            await interaction.response.edit_message(view=DropdownView(self.pagina, self.termo_busca))

    @button(label="Página 1/1", style=discord.ButtonStyle.secondary, disabled=True, custom_id="btn_page_indicator", row=1)
    async def btn_indicador(self, interaction: discord.Interaction, button: Button):
        pass

    @button(label="Próximo ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next_page", row=1)
    async def btn_proximo(self, interaction: discord.Interaction, button: Button):
        if self.pagina < self.total_paginas:
            self.pagina += 1
            await interaction.response.edit_message(view=DropdownView(self.pagina, self.termo_busca))

    @button(label="🔍 Pesquisar", style=discord.ButtonStyle.success, custom_id="btn_search_game", row=2)
    async def btn_pesquisar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalPesquisa())

    @button(label="❌ Limpar Busca", style=discord.ButtonStyle.danger, custom_id="btn_clear_search", disabled=True, row=2)
    async def btn_limpar_busca(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=DropdownView(pagina=1, termo_busca=None))


# --- VIEWS DE STREAM / KOSMI ---

class StreamPublicoView(View):
    def __init__(self, url_sala: str):
        super().__init__(timeout=None)
        self.add_item(Button(label="ASSISTIR LIVE", url=url_sala, style=discord.ButtonStyle.link, emoji="🍿", row=0))

class StreamDonoView(View):
    def __init__(self, author_id: int, sala_id: str, url_sala: str, dados_sala: dict):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.sala_id = sala_id
        self.url_sala = url_sala
        self.dados_sala = dados_sala
        self.horas_totais = 3
        self.tempo_encerramento = datetime.now(timezone.utc) + timedelta(hours=3)
        self.msg_publica = None
        self.msg_dono = None
        self.stream_publico_view = None

    async def atualizar_embed_dono(self, interaction: discord.Interaction):
        timestamp_unix = int(self.tempo_encerramento.timestamp())
        embed_dono = discord.Embed(
            description=f"🛠️ **PAINEL DO DONO (<@{self.author_id}>):**\n\n⏳ **Encerramento Previsto:** <t:{timestamp_unix}:R>",
            color=self.dados_sala["cor"]
        )
        await interaction.response.edit_message(embed=embed_dono, view=self)

    @button(label="Abrir Sua Live", style=discord.ButtonStyle.primary, emoji="🎥", custom_id="btn_abrir_live_protegido", row=1)
    async def btn_abrir_live(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id != self.author_id and not is_admin:
            return await interaction.response.send_message(f"⚠️ Apenas <@{self.author_id}> ou administradores podem abrir esta live!", ephemeral=True)

        view_link = View()
        view_link.add_item(Button(label=f"Acessar {self.dados_sala['nome']}", url=self.url_sala, style=discord.ButtonStyle.link, emoji="🔗"))
        await interaction.response.send_message("🚀 Clique abaixo para entrar na sua sala:", view=view_link, ephemeral=True)

    @button(label="Prorrogar (+1h)", style=discord.ButtonStyle.success, emoji="⏱️", custom_id="btn_prorrogar_stream", row=0)
    async def btn_prorrogar(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id != self.author_id and not is_admin:
            await interaction.response.defer()
            return await interaction.channel.send(f"⚠️ Apenas <@{self.author_id}> ou administradores podem prorrogar!", delete_after=5)

        if self.horas_totais >= 5:
            await interaction.response.defer()
            return await interaction.channel.send(f"⚠️ Limite máximo de **5 horas** atingido!", delete_after=5)

        self.horas_totais += 1
        self.tempo_encerramento += timedelta(hours=1)
        if self.stream_publico_view:
            self.stream_publico_view.tempo_encerramento = self.tempo_encerramento

        await self.atualizar_embed_dono(interaction)
        await interaction.channel.send("⏱️ Transmissão prorrogada em +1 hora!", delete_after=3)

    @button(label="Encerrar Transmissão", style=discord.ButtonStyle.danger, emoji="⏹️", custom_id="btn_fechar_stream_publico", row=0)
    async def fechar_stream(self, interaction: discord.Interaction, button: Button):
        is_admin = interaction.user.guild_permissions.administrator if interaction.guild else False
        if interaction.user.id != self.author_id and not is_admin:
            await interaction.response.defer()
            return await interaction.channel.send(f"⚠️ Apenas <@{self.author_id}> ou administradores podem encerrar!", delete_after=5)

        if self.sala_id in SALAS_EM_USO:
            del SALAS_EM_USO[self.sala_id]

        try:
            if self.msg_publica: await self.msg_publica.delete()
            if self.msg_dono: await self.msg_dono.delete()
            await interaction.response.defer()
            await interaction.channel.send("🛑 Transmissão encerrada!", delete_after=3)
        except Exception:
            pass

class SelectSalaKosmi(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=SALAS_KOSMI[s]["nome"], description=f"Iniciar transmissão na sala {s}", emoji=SALAS_KOSMI[s]["emoji"], value=s)
            for s in SALAS_KOSMI
        ]
        super().__init__(placeholder="Selecione a sala para iniciar transmissão...", min_values=1, max_values=1, options=options, custom_id="select_sala_kosmi_fixo")

    async def callback(self, interaction: discord.Interaction):
        sala_id = self.values[0]
        dados_sala = SALAS_KOSMI.get(sala_id)

        if not dados_sala:
            return await interaction.response.send_message("❌ Sala não encontrada.", ephemeral=True)

        if sala_id in SALAS_EM_USO:
            dono_atual_id = SALAS_EM_USO[sala_id]
            await interaction.response.defer()
            return await interaction.channel.send(f"⚠️ Esta sala já está sendo usada por <@{dono_atual_id}>!", delete_after=5)

        user = interaction.user
        SALAS_EM_USO[sala_id] = user.id

        try:
            await interaction.message.edit(view=StreamPainelView())
        except Exception:
            pass

        view_publica = StreamPublicoView(dados_sala['url'])
        view_dono = StreamDonoView(user.id, sala_id, dados_sala['url'], dados_sala)
        view_dono.stream_publico_view = view_publica

        embed_publico = discord.Embed(
            title=f"{dados_sala['emoji']} TRANSMISSÃO INICIADA",
            description=f"🎮 {user.mention} iniciou uma transmissão na **{dados_sala['nome']}**!\n\nClique no botão abaixo para assistir.",
            color=dados_sala["cor"]
        )

        msg_publica = await interaction.channel.send(embed=embed_publico, view=view_publica, delete_after=18000)
        view_dono.msg_publica = msg_publica

        timestamp_unix = int(view_dono.tempo_encerramento.timestamp())
        embed_dono = discord.Embed(
            description=f"🛠️ **PAINEL DO DONO ({user.mention}):**\n\n⏳ **Encerramento Previsto:** <t:{timestamp_unix}:R>",
            color=dados_sala["cor"]
        )

        msg_dono = await interaction.channel.send(embed=embed_dono, view=view_dono, delete_after=18000)
        view_dono.msg_dono = msg_dono

        await interaction.response.defer()

        async def limpar_sala_expirada():
            await asyncio.sleep(18000)
            if sala_id in SALAS_EM_USO and SALAS_EM_USO[sala_id] == user.id:
                del SALAS_EM_USO[sala_id]
            try:
                await msg_publica.delete()
                await msg_dono.delete()
            except Exception:
                pass

        asyncio.create_task(limpar_sala_expirada())

class StreamPainelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelectSalaKosmi())


# --- EVENTOS E COMANDOS DO BOT ---

@bot.event
async def on_ready():
    bot.add_view(DropdownView())
    bot.add_view(StreamPainelView())
    print(f'✅ Bot online e conectado como {bot.user.name}')

@bot.command()
@commands.has_permissions(administrator=True)
async def enviar_menu(ctx):
    try: await ctx.message.delete()
    except Exception: pass
    
    embed = discord.Embed(
        title="🎮 Jogos Co-op Liberados!",
        description="Escolha o jogo no menu abaixo para receber o `.torrent` no chat.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=DropdownView(pagina=1))

@bot.command()
@commands.has_permissions(administrator=True)
async def painel_stream(ctx):
    try: await ctx.message.delete()
    except Exception: pass
        
    embed = discord.Embed(
        title="🖥️ Painel de Transmissões - Tech Ninjas",
        description="Selecione uma sala abaixo para iniciar sua transmissão:",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed, view=StreamPainelView())

@bot.command(name="times", aliases=["sortear", "dividir"])
async def sortear_times(ctx, num_times: int = 2):
    try: await ctx.message.delete()
    except Exception: pass

    nome_canal_limpo = ctx.channel.name.lower().replace("︱", "").replace(" ", "").replace("_", "-")
    if "sortear" not in nome_canal_limpo:
        canal_destino = next((c for c in ctx.guild.text_channels if "sortear" in c.name.lower()), None)
        mencao_canal = f"<#{canal_destino.id}>" if canal_destino else "no canal de sorteio"
        return await ctx.send(f"❌ {ctx.author.mention}, use este comando no canal {mencao_canal}!", delete_after=5)

    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("❌ Você precisa estar em um canal de voz!", delete_after=5)

    canal_voz = ctx.author.voice.channel
    jogadores = [m.display_name for m in canal_voz.members if not m.bot]

    if len(jogadores) < num_times:
        return await ctx.send(f"❌ Pessoas insuficientes no canal **{canal_voz.name}** para {num_times} times.", delete_after=5)

    if num_times < 2:
        return await ctx.send("❌ O número mínimo de times é 2.", delete_after=5)

    random.shuffle(jogadores)
    nomes_times = [
        ("🔴 Time Alpha", discord.Color.red()),
        ("🔵 Time Bravo", discord.Color.blue()),
        ("🟢 Time Charlie", discord.Color.green()),
        ("🟡 Time Delta", discord.Color.gold()),
        ("🟣 Time Echo", discord.Color.purple())
    ]

    times = [[] for _ in range(num_times)]
    for i, jogador in enumerate(jogadores):
        times[i % num_times].append(jogador)

    embed = discord.Embed(
        title="🎲 Divisão de Times",
        description=f"Sorteio realizado no canal **{canal_voz.name}** ({len(jogadores)} jogadores):",
        color=discord.Color.gold()
    )

    for idx, integrantes in enumerate(times):
        nome_time = nomes_times[idx][0] if idx < len(nomes_times) else f"⚪ Time {idx+1}"
        embed.add_field(name=f"{nome_time} ({len(integrantes)})", value="\n".join([f"• {p}" for p in integrantes]), inline=True)

    embed.set_footer(text="Esta mensagem será apagada em 3 minutos.")
    await ctx.send(embed=embed, delete_after=180)

@bot.command()
@commands.has_permissions(administrator=True)
async def comandos(ctx):
    try: await ctx.message.delete()
    except Exception: pass

    embed = discord.Embed(
        title="🛠️ Painel de Ajuda - Administrador",
        description="Lista de comandos administrativos:",
        color=discord.Color.gold()
    )
    embed.add_field(name="`!enviar_menu`", value="Envia o painel de torrents com paginação e busca.", inline=False)
    embed.add_field(name="`!painel_stream`", value="Envia o painel de gerenciamento das salas Kosmi.", inline=False)
    embed.add_field(name="`!times [qtd]`", value="Divide o canal de voz em equipes.", inline=False)
    embed.set_footer(text="Mensagem automática de ajuda.")
    await ctx.send(embed=embed, delete_after=30)

# --- EXECUÇÃO COM DELAY DE SEGURANÇA CONTRA CLOUDFLARE ---
async def main():
    if not TOKEN:
        print("❌ ERRO CRÍTICO: Token não configurado nas Variáveis de Ambiente do Render.")
        return
    
    print("⏳ Aguardando 15 segundos para estabilizar a conexão e evitar rate limit da Cloudflare...")
    await asyncio.sleep(15)
    
    try:
        await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Erro crítico ao conectar o bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
