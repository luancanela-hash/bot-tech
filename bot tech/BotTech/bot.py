import os
import discord
from discord.ext import commands
from discord.ui import Select, View

# Cole o seu TOKEN do Discord Developer Portal entre as aspas
TOKEN = "MTU1Nzg5MDgwNDIzMDY2MDA5Ng.Gml_jH.osb8mTRzknNSxBbFjszhYAVl_PowpU_Q3t6ANw"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

PASTA_TORRENTS = "./torrents"

class DropdownJogos(Select):
    def __init__(self):
        options = []
        
        # Lê os ficheiros .torrent da pasta torrents
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
            # Envia o arquivo e define delete_after=60 para apagar a mensagem após 1 minuto
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