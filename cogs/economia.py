"""
cogs/economia.py
Sistema de economia: loja, inventário, itens, dar itens.
"""
import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db


class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="loja", description="Veja os itens disponíveis na loja")
    async def loja(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        config = data["config"]
        loja = data.get("loja", {})
        emoji = config.get("moeda_emoji", "🪙")
        nome = config.get("moeda_nome", "Moedas")

        embed = discord.Embed(title="🛒 Loja", color=discord.Color.green())

        if not loja:
            embed.description = "Nenhum item na loja ainda. Configure com `/central` → Itens."
        else:
            for item_id, item in loja.items():
                embed.add_field(
                    name=f"{item.get('emoji', '📦')} {item['nome']}",
                    value=f"{emoji} {item['preco']} {nome}\n{item.get('descricao', '')}",
                    inline=True
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="inventario-usuario", description="Veja seu inventário ou o de outro jogador")
    async def inventario(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        data = db.load(interaction.guild.id)
        uid = str(alvo.id)
        jogador = data["jogadores"].get(uid, {})
        inventario = jogador.get("inventario", [])

        embed = discord.Embed(
            title=f"🎒 Inventário — {alvo.display_name}",
            color=discord.Color.blurple()
        )

        if not inventario:
            embed.description = "Inventário vazio."
        else:
            from collections import Counter
            contagem = Counter(inventario)
            linhas = [f"• **{item}** x{qtd}" for item, qtd in contagem.items()]
            embed.description = "\n".join(linhas)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="item-dar", description="[ADM] Dá um item a um jogador")
    async def item_dar(self, interaction: discord.Interaction, usuario: discord.Member, item: str):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)

        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()

        data["jogadores"][uid].setdefault("inventario", []).append(item)
        db.save(interaction.guild.id, data)

        await interaction.response.send_message(
            f"✅ Item **{item}** dado a {usuario.mention}.", ephemeral=True
        )


async def setup(bot):
    await bot.add_cog(Economia(bot))
