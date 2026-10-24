import os
import asyncio
import threading
import random
import logging
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Select, View, button, Button, Modal, TextInput

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("BotTech")

# ============================================================
# FLASK KEEP-ALIVE (RENDER)
# ============================================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Tech online!"

@app.route("/health")
def health():
    return {"status": "ok", "bot": bot.is_ready() if bot else False}

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

threading.Thread(target=run_web_server, daemon=True).start()

# ============================================================
# CONFIGURAÇÕES DO BOT
# ============================================================
TOKEN = os.environ.get("DISCORD_TOKEN") or os.environ.get("TOKEN")
PASTA_TORRENTS = "./torrents"

# Link do seu grupo no GoLive (ATUALIZADO)
LINK_GOLIVE = "https://golive.nemtudo.me/invite/JyiBJKgC"

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)
JOGOS_EM_DOWNLOAD = set()

# ============================================================
# SISTEMA DE JOGOS CO-OP
# ============================================================
def listar_torrents():
    if not os.path.exists(PASTA_TORRENTS):
        return []
    return sorted(f for f in os.listdir(PASTA_TORRENTS) if f.endswith(".torrent"))


class DropdownJogos(Select):
    def __init__(self, arquivos: list):
        options = []
        for arq in arquivos:
            nome = arq.replace(".torrent", "")
            options.append(discord.SelectOption(
                label=nome[:100],
                description=f"Baixar {nome}"[:100],
                emoji="🎮",
                value=arq
            ))

        if not options:
            options.append(discord.SelectOption(label="Nenhum jogo encontrado", value="none"))

        super().__init__(
            placeholder="Selecione um jogo...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="menu_jogos_dropdown",
        )

    async def callback(self, interaction: discord.Interaction):
        nome_arquivo = self.values[0]
        await interaction.response.defer()

        if nome_arquivo == "none":
            return await interaction.followup.send("Nenhum jogo disponível.", ephemeral=True)

        if nome_arquivo in JOGOS_EM_DOWNLOAD:
            return await interaction.followup.send(
                f"⚠️ {interaction.user.mention}, este arquivo já foi solicitado recentemente. Aguarde.",
                ephemeral=True,
            )

        JOGOS_EM_DOWNLOAD.add(nome_arquivo)
        caminho = os.path.join(PASTA_TORRENTS, nome_arquivo)

        if not os.path.isfile(caminho):
            JOGOS_EM_DOWNLOAD.discard(nome_arquivo)
            return await interaction.followup.send(
                f"❌ Arquivo não encontrado no servidor.", ephemeral=True
            )

        try:
            arquivo = discord.File(caminho)
            await interaction.channel.send(
                content=f"📥 {interaction.user.mention} solicitou **{nome_arquivo.replace('.torrent','')}** (some em 60s):",
                file=arquivo,
                delete_after=60,
            )
        except Exception as e:
            log.exception("Erro ao enviar torrent")
            await interaction.followup.send("❌ Erro ao enviar o arquivo.", ephemeral=True)

        async def liberar():
            await asyncio.sleep(60)
            JOGOS_EM_DOWNLOAD.discard(nome_arquivo)

        asyncio.create_task(liberar())


class ModalPesquisa(Modal, title="🔍 Pesquisar Jogo"):
    termo = TextInput(
        label="Nome do jogo",
        placeholder="Digite parte do nome...",
        required=True,
        max_length=50,
    )

    async def on_submit(self, interaction: discord.Interaction):
        nova_view = DropdownView(pagina=1, termo_busca=self.termo.value)
        await interaction.response.edit_message(view=nova_view)


class DropdownView(View):
    TAM_PAGINA = 25
    NOMES_TIMES = [
        ("🔴 Time Alpha", discord.Color.red()),
        ("🔵 Time Bravo", discord.Color.blue()),
        ("🟢 Time Charlie", discord.Color.green()),
        ("🟡 Time Delta", discord.Color.gold()),
        ("🟣 Time Echo", discord.Color.purple()),
    ]

    def __init__(self, pagina: int = 1, termo_busca: str | None = None):
        super().__init__(timeout=None)
        self.pagina = max(1, pagina)
        self.termo_busca = termo_busca

        arquivos = listar_torrents()
        if termo_busca:
            arquivos = [f for f in arquivos if termo_busca.lower() in f.lower()]

        self.total_paginas = max(1, (len(arquivos) + self.TAM_PAGINA - 1) // self.TAM_PAGINA)
        self.pagina = min(self.pagina, self.total_paginas)

        inicio = (self.pagina - 1) * self.TAM_PAGINA
        bloco = arquivos[inicio:inicio + self.TAM_PAGINA]

        self.add_item(DropdownJogos(bloco))

        self.btn_anterior.disabled = self.pagina <= 1
        self.btn_proximo.disabled = self.pagina >= self.total_paginas
        self.btn_limpar_busca.disabled = not self.termo_busca

        if self.termo_busca:
            self.btn_indicador.label = f"Busca: '{self.termo_busca[:30]}' ({len(arquivos)})"
        else:
            self.btn_indicador.label = f"Página {self.pagina}/{self.total_paginas}"

    @button(label="◀️ Anterior", style=discord.ButtonStyle.primary, custom_id="btn_prev_page", row=1)
    async def btn_anterior(self, interaction: discord.Interaction, button: Button):
        if self.pagina > 1:
            await interaction.response.edit_message(
                view=DropdownView(self.pagina - 1, self.termo_busca)
            )
        else:
            await interaction.response.defer()

    @button(label="Página", style=discord.ButtonStyle.secondary, disabled=True, custom_id="btn_page_indicator", row=1)
    async def btn_indicador(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()

    @button(label="Próximo ▶️", style=discord.ButtonStyle.primary, custom_id="btn_next_page", row=1)
    async def btn_proximo(self, interaction: discord.Interaction, button: Button):
        if self.pagina < self.total_paginas:
            await interaction.response.edit_message(
                view=DropdownView(self.pagina + 1, self.termo_busca)
            )
        else:
            await interaction.response.defer()

    @button(label="🔍 Pesquisar", style=discord.ButtonStyle.success, custom_id="btn_search_game", row=2)
    async def btn_pesquisar(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ModalPesquisa())

    @button(label="❌ Limpar Busca", style=discord.ButtonStyle.danger, custom_id="btn_clear_search", row=2)
    async def btn_limpar_busca(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(view=DropdownView(pagina=1, termo_busca=None))


# ============================================================
# PAINEL DE STREAM (GOLIVE)
# ============================================================
class StreamPainelView(View):
    def __init__(self):
        super().__init__(timeout=None)
        # Botão principal para acessar o grupo de salas do GoLive
        self.add_item(Button(
            label="Entrar no Grupo de Transmissão", 
            url=LINK_GOLIVE, 
            style=discord.ButtonStyle.link, 
            emoji="🍿"
        ))


# ============================================================
# EVENTOS
# ============================================================
@bot.event
async def on_ready():
    log.info(f"✅ Bot online: {bot.user} (ID: {bot.user.id})")
    bot.add_view(StreamPainelView())
    bot.add_view(DropdownView(pagina=1))

    try:
        synced = await bot.tree.sync()
        log.info(f"🔁 Slash commands sincronizados: {len(synced)}")
    except Exception as e:
        log.warning(f"Falha ao sincronizar comandos: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        try:
            await ctx.send("❌ Você não tem permissão para isso.", delete_after=5)
        except Exception:
            pass
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        log.exception("Erro em comando", exc_info=error)


# ============================================================
# COMANDOS
# ============================================================
@bot.command()
@commands.has_permissions(administrator=True)
async def enviar_menu(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🎮 Jogos Co-op Liberados!",
        description="Escolha o jogo no menu abaixo para receber o `.torrent`.",
        color=discord.Color.blue(),
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
        title="🖥️ Transmissões - Tech Ninjas",
        description="Clique no botão abaixo para entrar no nosso grupo!\nLá dentro você pode escolher a sala (1 a 5) para assistir ou compartilhar sua tela.",
        color=discord.Color.orange(),
    )
    await ctx.send(embed=embed, view=StreamPainelView())


@bot.command(name="times", aliases=["sortear", "dividir"])
async def sortear_times(ctx, num_times: int = 2):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    nome_canal = ctx.channel.name.lower().replace("︱", "").replace(" ", "").replace("_", "-")
    if "sortear" not in nome_canal:
        canal = next((c for c in ctx.guild.text_channels if "sortear" in c.name.lower()), None)
        return await ctx.send(
            f"❌ Use no canal {canal.mention if canal else 'de sorteio'}!",
            delete_after=5,
        )

    if not ctx.author.voice or not ctx.author.voice.channel:
        return await ctx.send("❌ Entre em um canal de voz primeiro!", delete_after=5)

    if num_times < 2:
        return await ctx.send("❌ Mínimo de 2 times.", delete_after=5)

    canal_voz = ctx.author.voice.channel
    jogadores = [m.display_name for m in canal_voz.members if not m.bot]

    if len(jogadores) < num_times:
        return await ctx.send(f"❌ Poucas pessoas ({len(jogadores)}) para {num_times} times.", delete_after=5)

    random.shuffle(jogadores)
    times = [[] for _ in range(num_times)]
    for i, j in enumerate(jogadores):
        times[i % num_times].append(j)

    embed = discord.Embed(
        title="🎲 Divisão de Times",
        description=f"Sorteio em **{canal_voz.name}** ({len(jogadores)} jogadores):",
        color=discord.Color.gold(),
    )

    for idx, integrantes in enumerate(times):
        nome = DropdownView.NOMES_TIMES[idx][0] if idx < len(DropdownView.NOMES_TIMES) else f"⚪ Time {idx+1}"
        embed.add_field(
            name=f"{nome} ({len(integrantes)})",
            value="\n".join(f"• {p}" for p in integrantes) or "—",
            inline=True,
        )

    embed.set_footer(text="Some em 3 minutos.")
    await ctx.send(embed=embed, delete_after=180)


@bot.command()
@commands.has_permissions(administrator=True)
async def comandos(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    embed = discord.Embed(
        title="🛠️ Ajuda Admin",
        description="Comandos disponíveis:",
        color=discord.Color.gold(),
    )
    embed.add_field(name="`!enviar_menu`", value="Painel de torrents com paginação e busca.", inline=False)
    embed.add_field(name="`!painel_stream`", value="Painel de transmissão do GoLive.", inline=False)
    embed.add_field(name="`!times [qtd]`", value="Divide o canal de voz em equipes.", inline=False)
    embed.set_footer(text="Some em 30s.")
    await ctx.send(embed=embed, delete_after=30)


# ============================================================
# STARTUP
# ============================================================
async def main():
    if not TOKEN:
        log.critical("❌ DISCORD_TOKEN não configurado!")
        return

    async with bot:
        for tentativa in range(5):
            try:
                log.info("🚀 Iniciando bot...")
                await bot.start(TOKEN)
                break
            except discord.HTTPException as e:
                if e.status == 429:
                    espera = 60 * (2 ** tentativa)
                    log.warning(f"⏳ 429 detectado. Aguardando {espera}s...")
                    await asyncio.sleep(espera)
                else:
                    log.exception("Erro HTTP")
                    break
            except discord.LoginFailure:
                log.critical("❌ Token inválido!")
                break
            except Exception:
                log.exception("Erro inesperado no startup")
                await asyncio.sleep(30)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Encerrado manualmente.")
