import os
import random
import threading
import discord
from discord.ext import commands
from flask import Flask

# --- CONFIGURAÇÃO DO FLASK (Para manter o Render ativo) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot está online e operacional!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- CONFIGURAÇÃO DOS INTENTS DO DISCORD ---
intents = discord.Intents.default()
intents.message_content = True  # OBRIGATÓRIO para ler comandos de texto
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- DADOS DOS JOGOS CO-OP (Páginas) ---
JOGOS_COOP = [
    {
        "titulo": "It Takes Two",
        "descricao": "Uma aventura cooperativa inesquecível criada exclusivamente para dois jogadores. Trabalhem juntos para superar desafios absurdos.",
        "tamanho": "45 GB",
        "genero": "Aventura / Co-op Local & Online",
        "magnet": "magnet:?xt=urn:btih:exemplo_ittakestwo_aqui"
    },
    {
        "titulo": "A Way Out",
        "descricao": "Jogue na pele de dois prisioneiros em fuga épica. Cada jogador controla um dos personagens em cooperação obrigatória.",
        "tamanho": "25 GB",
        "genero": "Ação / Aventura / Co-op",
        "magnet": "magnet:?xt=urn:btih:exemplo_awayout_aqui"
    },
    {
        "titulo": "Portal 2",
        "descricao": "O clássico aclamado de puzzles em primeira pessoa com campanha cooperativa dedicada para dois jogadores.",
        "tamanho": "12 GB",
        "genero": "Puzzle / Sci-Fi / Co-op",
        "magnet": "magnet:?xt=urn:btih:exemplo_portal2_aqui"
    },
    {
        "titulo": "Helldivers 2",
        "descricao": "Junte-se à última linha de defesa da galáxia neste jogo de tiro cooperativo frenético em esquadrão.",
        "tamanho": "70 GB",
        "genero": "Tiro / Ação / Co-op Online",
        "magnet": "magnet:?xt=urn:btih:exemplo_helldivers2_aqui"
    },
    {
        "titulo": "Monster Hunter: World",
        "descricao": "Enfrente feras gigantescas em ecossistemas vivos, sozinho ou em equipe caçando monstros lendários.",
        "tamanho": "50 GB",
        "genero": "RPG de Ação / Co-op",
        "magnet": "magnet:?xt=urn:btih:exemplo_mhw_aqui"
    }
]

# --- VIEWS INTERATIVAS ---

class DropdownView(discord.ui.View):
    def __init__(self, pagina=1):
        super().__init__(timeout=None)
        self.pagina = pagina
        self.add_item(DropdownJogos())
        self.add_item(BotoesNavegacao(pagina))

class DropdownJogos(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=jogo["titulo"], description=f"Tamanho: {jogo['tamanho']} | {jogo['genero'][:40]}", emoji="🎮")
            for jogo in JOGOS_COOP
        ]
        super().__init__(placeholder="📂 Selecione um jogo para ver os detalhes...", min_values=1, max_values=1, options=options, custom_id="select_jogo")

    async def callback(self, interaction: discord.Interaction):
        jogo_escolhido = next((j for j in JOGOS_COOP if j["titulo"] == self.values[0]), None)
        if not jogo_escolhido:
            await interaction.response.send_message("❌ Jogo não encontrado.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📥 Download: {jogo_escolhido['titulo']}",
            description=jogo_escolhido['descricao'],
            color=discord.Color.green()
        )
        embed.add_field(name="📦 Tamanho", value=jogo_escolhido['tamanho'], inline=True)
        embed.add_field(name="🏷️ Gênero", value=jogo_escolhido['genero'], inline=True)
        embed.add_field(name="🔗 Link Magnet (.torrent)", value=f"```text\n{jogo_escolhido['magnet']}\n```", inline=False)
        embed.set_footer(text="Dica: Copie o link acima e cole no seu cliente BitTorrent (como qBittorrent ou uTorrent).")

        await interaction.response.send_message(embed=embed, ephemeral=True)

class BotoesNavegacao(discord.ui.View):
    def __init__(self, pagina):
        super().__init__(timeout=None)
        self.pagina = pagina

    @discord.ui.button(label="◀️ Anterior", style=discord.ButtonStyle.secondary, custom_id="btn_anterior")
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="📄 Página anterior carregada.", view=DropdownView(pagina=1))

    @discord.ui.button(label="🔍 Pesquisar Jogo", style=discord.ButtonStyle.primary, custom_id="btn_pesquisar")
    async def pesquisar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔍 Para pesquisar um jogo específico, utilize o menu suspenso acima com todos os títulos disponíveis.", ephemeral=True)

    @discord.ui.button(label="Próximo ▶️", style=discord.ButtonStyle.secondary, custom_id="btn_proximo")
    async def proximo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="📄 Próxima página carregada.", view=DropdownView(pagina=1))

class StreamPainelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(DropdownSalasTransmissao())

class DropdownSalasTransmissao(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=f"Jogatina {i}", description=f"Entrar na sala de voz Jogatina {i}", emoji="🎙️")
            for i in range(1, 6)
        ]
        super().__init__(placeholder="🎙️ Selecione uma sala de voz para transmitir...", min_values=1, max_values=1, options=options, custom_id="select_stream_sala")

    async def callback(self, interaction: discord.Interaction):
        sala = self.values[0]
        await interaction.response.send_message(f"📢 **{interaction.user.display_name}** abriu transmissão na sala **{sala}**! Quem quiser assistir, basta conectar-se ao canal de voz.", ephemeral=False)


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
        description="Escolha o jogo no menu suspenso abaixo para receber o link `.torrent` diretamente no chat.\n\nUse os botões ◀️▶️ para navegar pelas páginas ou clique em 🔍 Pesquisar Jogo para buscar diretamente.",
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

# --- COMANDO PÚBLICO PARA TODOS OS MEMBROS: SORTEADOR DE TIMES ---
@bot.command(name="times", aliases=["sortear", "dividir"])
async def sortear_times(ctx, num_times: int = 2):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    nome_canal_limpo = ctx.channel.name.lower().replace("︱", "").replace(" ", "").replace("_", "-")
    if "sortear" not in nome_canal_limpo:
        canal_destino = next((c for c in ctx.guild.text_channels if "sortear" in c.name.lower()), None)
        mencao_canal = f"<#{canal_destino.id}>" if canal_destino else "no canal de sorteio de times"
        
        await ctx.send(
            f"❌ {ctx.author.mention}, este comando só pode ser utilizado no canal {mencao_canal}!",
            delete_after=5
        )
        return

    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ Você precisa estar conectado a um canal de voz para sortear os times!", delete_after=5)
        return

    canal_voz = ctx.author.voice.channel
    jogadores = [membro.display_name for membro in canal_voz.members if not membro.bot]

    if len(jogadores) < num_times:
        await ctx.send(
            f"❌ É necessário ter pelo menos {num_times} pessoas no canal de voz **{canal_voz.name}** para criar {num_times} times.",
            delete_after=5
        )
        return

    if num_times < 2:
        await ctx.send("❌ O número de times deve ser no mínimo 2!", delete_after=5)
        return

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
        description=f"Sorteio de **{num_times} times** realizado entre os membros do canal **{canal_voz.name}** ({len(jogadores)} jogadores)!",
        color=discord.Color.gold()
    )

    for idx, integrantes in enumerate(times):
        nome_time = nomes_times[idx][0] if idx < len(nomes_times) else f"⚪ Time {idx+1}"
        embed.add_field(
            name=f"{nome_time} ({len(integrantes)})",
            value="\n".join([f"• {p}" for p in integrantes]),
            inline=True
        )

    embed.set_footer(text="Bom jogo e boa sorte aos times! (Esta mensagem será apagada em 3 minutos)")
    await ctx.send(embed=embed, delete_after=180)

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
        name="`!times [quantidade]` (ou `!sortear` / `!dividir`)",
        value="Divide os membros do canal de voz em 2 ou mais times (ex: `!times 3`). **Uso exclusivo no canal de sorteio de times** (apaga após 3 minutos).",
        inline=False
    )
    embed.add_field(
        name="`!comandos`",
        value="Mostra esta lista de ajuda administrativa.",
        inline=False
    )
    embed.set_footer(text="Esta mensagem desaparecerá automaticamente após 30 segundos.")

    await ctx.send(embed=embed, delete_after=30)

# --- INICIALIZAÇÃO ---
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERRO: Token do Discord não configurado nas variáveis de ambiente!")
    else:
        keep_alive()
        try:
            bot.run(TOKEN)
        except Exception as e:
            print(f"❌ Erro crítico ao executar o bot: {e}")
