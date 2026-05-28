"""
cogs/apostas.py
Painel de estatísticas de apostas com filtro de período.
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from utils import database as db


def filtrar_stats(stats: list, periodo: str) -> list:
    agora = datetime.now()
    if periodo == "hoje":
        inicio = agora.replace(hour=0, minute=0, second=0)
    elif periodo == "ontem":
        ontem = agora - timedelta(days=1)
        inicio = ontem.replace(hour=0, minute=0, second=0)
        fim = ontem.replace(hour=23, minute=59, second=59)
        return [s for s in stats if inicio <= datetime.fromisoformat(s["data"]) <= fim]
    elif periodo == "semana":
        inicio = agora - timedelta(days=7)
    elif periodo == "mes":
        inicio = agora - timedelta(days=30)
    else:
        inicio = agora.replace(hour=0, minute=0, second=0)
    return [s for s in stats if datetime.fromisoformat(s["data"]) >= inicio]


def gerar_embed_stats(stats: list, periodo: str, partidas_ativas: dict) -> discord.Embed:
    nomes_periodo = {
        "hoje": "Hoje",
        "ontem": "Ontem",
        "semana": "Últimos 7 dias",
        "mes": "Últimos 30 dias"
    }

    abertas = len([p for p in partidas_ativas.values() if p["status"] == "em_andamento"])
    aguardando = len([p for p in partidas_ativas.values() if p["status"] == "aguardando_confirmacao"])
    encerradas = len([s for s in stats if s["tipo"] == "encerrada"])
    sem_vencedor = len([s for s in stats if s["tipo"] == "wo"])
    canceladas = len([s for s in stats if s["tipo"] == "cancelada"])
    total = len(stats)

    # Mais frequentes
    jogos = {}
    modalidades = {}
    valores = {}
    for s in stats:
        jogo = s.get("jogo_id", "?")
        mod = s.get("modalidade", "?")
        val = s.get("valor", 0)
        jogos[jogo] = jogos.get(jogo, 0) + 1
        modalidades[mod] = modalidades.get(mod, 0) + 1
        valores[val] = valores.get(val, 0) + 1

    jogo_top = max(jogos, key=jogos.get) if jogos else "—"
    mod_top = max(modalidades, key=modalidades.get) if modalidades else "—"
    val_top = max(valores, key=valores.get) if valores else 0

    embed = discord.Embed(
        title="📊 Estatística das Partidas",
        color=discord.Color.blurple()
    )
    embed.description = f"> Período Selecionado: **{nomes_periodo.get(periodo, periodo)}**"

    embed.add_field(
        name="📋 Dados Gerais",
        value=(
            f"- **Abertas:** `{abertas}`\n"
            f"- **Aguardando Confirmações:** `{aguardando}`\n"
            f"- **Encerradas Validadas:** `{encerradas}`\n"
            f"- **Encerradas sem Vencedor:** `{sem_vencedor}`\n"
            f"- **Canceladas:** `{canceladas}`\n"
            f"- **Total:** `{total}`"
        ),
        inline=False
    )

    embed.add_field(
        name="🏆 Mais Frequentes",
        value=(
            f"- **Jogo:** {jogo_top.upper()} ({jogos.get(jogo_top, 0)})\n"
            f"- **Modalidade:** {mod_top} ({modalidades.get(mod_top, 0)})\n"
            f"- **Valor:** R$ {val_top:.2f} ({valores.get(val_top, 0)})"
        ) if jogos else "Nenhuma partida no período.",
        inline=False
    )

    # Gráfico de barras ASCII por dia
    if periodo in ["semana", "mes"] and stats:
        grafico = gerar_grafico(stats, periodo)
        embed.add_field(name="📈 Gráfico", value=grafico, inline=False)

    return embed


def gerar_grafico(stats: list, periodo: str) -> str:
    """Gera um gráfico de barras simples em texto."""
    dias = 7 if periodo == "semana" else 14
    agora = datetime.now()
    contagem = {}

    for i in range(dias):
        dia = (agora - timedelta(days=i)).strftime("%d/%m")
        contagem[dia] = 0

    for s in stats:
        dia = datetime.fromisoformat(s["data"]).strftime("%d/%m")
        if dia in contagem:
            contagem[dia] += 1

    max_val = max(contagem.values()) if contagem.values() else 1
    linhas = []
    for dia, qtd in sorted(contagem.items()):
        barras = int((qtd / max(max_val, 1)) * 10)
        barra = "█" * barras + "░" * (10 - barras)
        linhas.append(f"`{dia}` {barra} {qtd}")

    return "\n".join(linhas[-7:]) if linhas else "Sem dados."


class ViewEstatisticas(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.periodo = "hoje"

    def _atualizar_botoes(self):
        for item in self.children:
            if hasattr(item, 'custom_id'):
                item.style = discord.ButtonStyle.blurple if item.custom_id == f"stat_{self.periodo}" else discord.ButtonStyle.grey

    @discord.ui.button(label="Hoje", style=discord.ButtonStyle.blurple, custom_id="stat_hoje")
    async def hoje(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.periodo = "hoje"
        self._atualizar_botoes()
        await self._atualizar(interaction)

    @discord.ui.button(label="Ontem", style=discord.ButtonStyle.grey, custom_id="stat_ontem")
    async def ontem(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.periodo = "ontem"
        self._atualizar_botoes()
        await self._atualizar(interaction)

    @discord.ui.button(label="Semana", style=discord.ButtonStyle.grey, custom_id="stat_semana")
    async def semana(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.periodo = "semana"
        self._atualizar_botoes()
        await self._atualizar(interaction)

    @discord.ui.button(label="Mês", style=discord.ButtonStyle.grey, custom_id="stat_mes")
    async def mes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.periodo = "mes"
        self._atualizar_botoes()
        await self._atualizar(interaction)

    async def _atualizar(self, interaction: discord.Interaction):
        data = db.load(self.guild_id)
        stats = filtrar_stats(data.get("stats", []), self.periodo)
        embed = gerar_embed_stats(stats, self.periodo, data.get("partidas", {}))
        await interaction.response.edit_message(embed=embed, view=self)


class Apostas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="apostas", description="Painel de estatísticas de apostas")
    async def apostas(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        stats = filtrar_stats(data.get("stats", []), "hoje")
        embed = gerar_embed_stats(stats, "hoje", data.get("partidas", {}))
        view = ViewEstatisticas(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Apostas(bot))
