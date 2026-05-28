"""
cogs/admin.py
Ferramentas administrativas:
- BlackList
- Logs
- Mensagens do bot
- Gerenciamento de moedas
"""
import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── BlackList ─────────────────────────────────────────────────────────────

    @app_commands.command(name="blacklist-add", description="[ADM] Adiciona jogador à blacklist")
    async def blacklist_add(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str = "Não informado"):
        data = db.load(interaction.guild.id)
        uid = usuario.id

        if uid in data["blacklist"]:
            await interaction.response.send_message("❌ Jogador já está na blacklist.", ephemeral=True)
            return

        data["blacklist"].append(uid)
        db.save(interaction.guild.id, data)

        embed = discord.Embed(title="🚫 BlackList — Adicionado", color=discord.Color.red())
        embed.add_field(name="Jogador", value=usuario.mention, inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.add_field(name="ADM", value=interaction.user.mention, inline=True)

        await interaction.response.send_message(embed=embed)
        await _log_action(interaction.guild, data, embed)

    @app_commands.command(name="blacklist-remover", description="[ADM] Remove jogador da blacklist")
    async def blacklist_remover(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)

        if usuario.id not in data["blacklist"]:
            await interaction.response.send_message("❌ Jogador não está na blacklist.", ephemeral=True)
            return

        data["blacklist"].remove(usuario.id)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(f"✅ {usuario.mention} removido da blacklist.", ephemeral=True)

    @app_commands.command(name="blacklist", description="[ADM] Veja a blacklist do servidor")
    async def blacklist_ver(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        blist = data.get("blacklist", [])
        guild = interaction.guild

        embed = discord.Embed(title="🚫 BlackList", color=discord.Color.red())
        if not blist:
            embed.description = "Nenhum jogador na blacklist."
        else:
            linhas = []
            for uid in blist:
                membro = guild.get_member(uid)
                linhas.append(f"• {membro.mention if membro else uid}")
            embed.description = "\n".join(linhas)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Moedas ────────────────────────────────────────────────────────────────

    @app_commands.command(name="moedas-historico", description="Veja seu histórico de moedas")
    async def moedas_historico(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        data = db.load(interaction.guild.id)
        uid = str(alvo.id)
        jogador = data["jogadores"].get(uid, {})
        config = data["config"]

        emoji = config.get("moeda_emoji", "🪙")
        nome = config.get("moeda_nome", "Moedas")

        embed = discord.Embed(
            title=f"{emoji} {nome} — {alvo.display_name}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Saldo atual", value=f"{emoji} {jogador.get('moedas', 0)}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Mensagens / Logs ──────────────────────────────────────────────────────

    @app_commands.command(name="mensagem", description="[ADM] Envia mensagem pelo bot em um canal")
    async def mensagem(self, interaction: discord.Interaction, canal: discord.TextChannel, texto: str):
        await canal.send(texto)
        await interaction.response.send_message(f"✅ Mensagem enviada em {canal.mention}.", ephemeral=True)

    @app_commands.command(name="logs", description="[ADM] Define o canal de logs")
    async def logs(self, interaction: discord.Interaction, canal: discord.TextChannel):
        data = db.load(interaction.guild.id)
        data["config"]["canal_logs"] = canal.id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(f"✅ Logs configurados em {canal.mention}.", ephemeral=True)

    # ── SS / Analista ─────────────────────────────────────────────────────────

    @app_commands.command(name="ss", description="Chama o SS/Analista para sua partida")
    async def ss(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        # Menciona o cargo de analista se configurado
        cargo_id = data["config"].get("cargo_ss")
        if cargo_id:
            cargo = interaction.guild.get_role(cargo_id)
            if cargo:
                await interaction.response.send_message(
                    f"📢 {cargo.mention} — SS solicitado por {interaction.user.mention} em {interaction.channel.mention}!"
                )
                return
        await interaction.response.send_message(
            f"📢 SS solicitado por {interaction.user.mention}! (Configure o cargo SS na /central)", ephemeral=False
        )

    @app_commands.command(name="streamer", description="[ADM] Configura fila de streamer/influencer")
    async def streamer(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.send_message(
            f"✅ {usuario.mention} adicionado à fila de streamer! (Em breve: fila especial com visor de audiência)",
            ephemeral=True
        )

    @app_commands.command(name="tp", description="Informações sobre transferência de pontos")
    async def tp(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "💱 **Transferência de pontos** — Use `/moeda-adicionar` e `/moeda-remover` para gestão manual.\n"
            "Em breve: transferência direta entre jogadores!",
            ephemeral=True
        )


async def _log_action(guild: discord.Guild, data: dict, embed: discord.Embed):
    canal_id = data["config"].get("canal_logs")
    if canal_id:
        canal = guild.get_channel(canal_id)
        if canal:
            await canal.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Admin(bot))
