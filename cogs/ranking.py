"""
cogs/ranking.py — Ranking, perfil e receita completos
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
from utils import database as db


def get_periodo_range(periodo):
    agora = datetime.now()
    if periodo == "hoje":
        return agora.replace(hour=0, minute=0, second=0, microsecond=0), agora
    elif periodo == "ontem":
        ontem = agora - timedelta(days=1)
        return ontem.replace(hour=0, minute=0, second=0), ontem.replace(hour=23, minute=59, second=59)
    elif periodo == "semana":
        dias = agora.weekday() + 1 if agora.weekday() != 6 else 0
        return (agora - timedelta(days=dias)).replace(hour=0, minute=0, second=0), agora
    elif periodo == "7dias":
        return agora - timedelta(days=7), agora
    elif periodo == "mes":
        return agora.replace(day=1, hour=0, minute=0, second=0), agora
    return agora.replace(hour=0, minute=0, second=0), agora


def filtrar_por_periodo(lista, periodo):
    inicio, fim = get_periodo_range(periodo)
    resultado = []
    for item in lista:
        try:
            dt = datetime.fromisoformat(item.get("data", ""))
            if inicio <= dt <= fim:
                resultado.append(item)
        except Exception:
            pass
    return resultado


# ══════════════════════════════════════════════════════════
#  RANKING
# ══════════════════════════════════════════════════════════

def gerar_embed_ranking(guild, data, tipo, periodo):
    nomes_periodo = {
        "hoje": "Hoje", "ontem": "Ontem", "semana": "Esta Semana",
        "7dias": "Últimos 7 dias", "mes": "Este Mês", "geral": "Geral"
    }
    nomes_tipo = {"vitorias": "Vitórias", "derrotas": "Derrotas", "vd": "Vitórias/Derrotas"}

    embed = discord.Embed(
        title="🏆 Ranking — " + nomes_tipo.get(tipo, "Vitórias"),
        color=discord.Color.gold()
    )
    embed.description = "> Período: **" + nomes_periodo.get(periodo, periodo) + "**"

    historico = data.get("historico", [])
    if periodo != "geral":
        historico = filtrar_por_periodo(historico, periodo)

    contagem = {}
    for p in historico:
        if tipo in ("vitorias", "vd"):
            v = p.get("vencedor")
            if v:
                uid = str(v)
                if uid not in contagem:
                    contagem[uid] = {"v": 0, "d": 0}
                contagem[uid]["v"] += 1
        if tipo in ("derrotas", "vd"):
            per = p.get("perdedor")
            if per:
                uid = str(per)
                if uid not in contagem:
                    contagem[uid] = {"v": 0, "d": 0}
                contagem[uid]["d"] += 1

    if not contagem:
        embed.add_field(name="Sem dados", value="Nenhuma partida no período.", inline=False)
        return embed

    ordem = sorted(contagem.items(), key=lambda x: x[1].get("v", 0), reverse=True)
    medalhas = ["🥇", "🥈", "🥉"]
    linhas = []
    for i, (uid, stats) in enumerate(ordem[:10]):
        m = guild.get_member(int(uid))
        nome = m.display_name if m else "ID:" + uid
        medalha = medalhas[i] if i < 3 else "`" + str(i+1) + ".`"
        if tipo == "vd":
            linhas.append(medalha + " **" + nome + "** — ✅ " + str(stats["v"]) + "V / ❌ " + str(stats["d"]) + "D")
        elif tipo == "vitorias":
            linhas.append(medalha + " **" + nome + "** — ✅ " + str(stats["v"]) + " vitórias")
        else:
            linhas.append(medalha + " **" + nome + "** — ❌ " + str(stats["d"]) + " derrotas")

    embed.add_field(name="Top 10", value="\n".join(linhas) if linhas else "Sem dados.", inline=False)
    return embed


class ViewRankingInterativo(discord.ui.View):
    def __init__(self, guild_id, tipo="vd", periodo="geral"):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.tipo = tipo
        self.periodo = periodo
        self.add_item(SelectTipoRanking(tipo))
        self.add_item(SelectPeriodoRanking(periodo))

    async def atualizar(self, interaction):
        data = db.load(self.guild_id)
        embed = gerar_embed_ranking(interaction.guild, data, self.tipo, self.periodo)
        view = ViewRankingInterativo(self.guild_id, self.tipo, self.periodo)
        await interaction.response.edit_message(embed=embed, view=view)


class SelectTipoRanking(discord.ui.Select):
    def __init__(self, atual):
        super().__init__(placeholder="Tipo: " + atual, options=[
            discord.SelectOption(label="Vitórias/Derrotas", value="vd", emoji="📊"),
            discord.SelectOption(label="Só Vitórias", value="vitorias", emoji="✅"),
            discord.SelectOption(label="Só Derrotas", value="derrotas", emoji="❌"),
        ], row=0)

    async def callback(self, interaction):
        self.view.tipo = self.values[0]
        await self.view.atualizar(interaction)


class SelectPeriodoRanking(discord.ui.Select):
    def __init__(self, atual):
        super().__init__(placeholder="Período: " + atual, options=[
            discord.SelectOption(label="Hoje", value="hoje", emoji="📅"),
            discord.SelectOption(label="Ontem", value="ontem", emoji="📅"),
            discord.SelectOption(label="Esta Semana", value="semana", emoji="📅"),
            discord.SelectOption(label="Últimos 7 dias", value="7dias", emoji="📅"),
            discord.SelectOption(label="Este Mês", value="mes", emoji="📅"),
            discord.SelectOption(label="Geral", value="geral", emoji="🏆"),
        ], row=1)

    async def callback(self, interaction):
        self.view.periodo = self.values[0]
        await self.view.atualizar(interaction)


# ══════════════════════════════════════════════════════════
#  PERFIL
# ══════════════════════════════════════════════════════════

def gerar_embed_perfil(alvo, data):
    uid = str(alvo.id)
    j = data["jogadores"].get(uid, {})
    config = data["config"]
    emoji_moeda = config.get("moeda_emoji", "🪙")
    nome_moeda = config.get("moeda_nome", "Moedas")

    vitorias = j.get("vitorias", 0)
    derrotas = j.get("derrotas", 0)
    total = vitorias + derrotas
    wr = str(round(vitorias / total * 100, 1)) + "%" if total > 0 else "0%"

    embed = discord.Embed(
        title="👤 Perfil — " + alvo.display_name,
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=alvo.display_avatar.url)
    embed.add_field(name="✅ Vitórias", value=str(vitorias), inline=True)
    embed.add_field(name="❌ Derrotas", value=str(derrotas), inline=True)
    embed.add_field(name="📊 Winrate", value=wr, inline=True)
    embed.add_field(name="🎮 Partidas", value=str(total), inline=True)
    embed.add_field(name=emoji_moeda + " " + nome_moeda, value=str(j.get("moedas", 0)), inline=True)

    ranking = data.get("ranking", {}).get("geral", {})
    if uid in ranking:
        pos = sorted(ranking.items(), key=lambda x: x[1], reverse=True)
        posicao = next((i+1 for i, (k, _) in enumerate(pos) if k == uid), "?")
        embed.add_field(name="🏆 Posição Ranking", value="#" + str(posicao), inline=True)

    return embed


# ══════════════════════════════════════════════════════════
#  RECEITA
# ══════════════════════════════════════════════════════════

def gerar_grafico_receita(historico, periodo):
    dias = 7 if periodo in ("semana", "7dias") else (14 if periodo == "mes" else 1)
    agora = datetime.now()
    contagem = {}
    for i in range(dias):
        dia = (agora - timedelta(days=i)).strftime("%d/%m")
        contagem[dia] = 0.0
    for p in historico:
        if p.get("vencedor"):
            try:
                dia = datetime.fromisoformat(p["data"]).strftime("%d/%m")
                if dia in contagem:
                    contagem[dia] += p.get("taxa_por_jogador", 0) * 2
            except Exception:
                pass
    max_val = max(contagem.values()) if contagem.values() else 1
    linhas = []
    for dia, val in sorted(contagem.items()):
        barras = int((val / max(max_val, 0.01)) * 8)
        barra = "█" * barras + "░" * (8 - barras)
        linhas.append("`" + dia + "` " + barra + " R$" + str(round(val, 2)))
    return "\n".join(linhas[-7:]) if linhas else "Sem dados."


def gerar_embed_receita(guild, data, periodo):
    nomes_periodo = {
        "hoje": "Hoje", "ontem": "Ontem", "semana": "Esta Semana (Dom-Sáb)",
        "7dias": "Últimos 7 dias", "mes": "Este Mês"
    }

    historico = data.get("historico", [])
    if periodo != "geral":
        historico = filtrar_por_periodo(historico, periodo)

    embed = discord.Embed(title="💰 Receita da Org", color=discord.Color.green())
    embed.description = "> Período Selecionado: **" + nomes_periodo.get(periodo, periodo) + "**"

    total_partidas = len([p for p in historico if p.get("tipo") != "revanche" and p.get("vencedor")])
    total_revanches = len([p for p in historico if p.get("tipo") == "revanche"])
    total_wo = len([p for p in historico if p.get("status") == "wo"])
    total_canceladas = len([p for p in historico if p.get("status") == "cancelada"])
    receita_total = sum(p.get("taxa_por_jogador", 0) * 2 for p in historico if p.get("vencedor"))

    dados_gerais = (
        "- **Partidas Concluídas:** `" + str(total_partidas) + "`\n"
        "- **Revanches:** `" + str(total_revanches) + "`\n"
        "- **W.O.:** `" + str(total_wo) + "`\n"
        "- **Canceladas:** `" + str(total_canceladas) + "`\n"
        "- **Receita Total:** `R$ " + str(round(receita_total, 2)) + "`"
    )
    embed.add_field(name="📋 Dados Gerais", value=dados_gerais, inline=False)

    # Por jogo
    por_jogo = {}
    partidas_por_jogo = {}
    for p in historico:
        jid = p.get("jogo_id", "?").upper()
        if p.get("vencedor"):
            por_jogo[jid] = por_jogo.get(jid, 0) + p.get("taxa_por_jogador", 0) * 2
            partidas_por_jogo[jid] = partidas_por_jogo.get(jid, 0) + 1
    if por_jogo:
        linhas = []
        for k in sorted(por_jogo, key=lambda x: por_jogo[x], reverse=True):
            linhas.append("🎮 **" + k + "** — " + str(partidas_por_jogo.get(k, 0)) + " partidas | R$ " + str(round(por_jogo[k], 2)))
        embed.add_field(name="📊 Por Jogo", value="\n".join(linhas), inline=False)

    # Gráfico
    if periodo not in ("hoje", "ontem"):
        grafico = gerar_grafico_receita(historico, periodo)
        embed.add_field(name="📈 Gráfico de Receita", value=grafico, inline=False)

    # Top 3 mediadores
    receita_med = {}
    partidas_med = {}
    for uid, j in data["jogadores"].items():
        r = j.get("receita_total", 0)
        if r > 0:
            receita_med[uid] = r
            partidas_med[uid] = j.get("partidas_mediadas", 0)
    if receita_med:
        top3 = sorted(receita_med.items(), key=lambda x: x[1], reverse=True)[:3]
        medalhas = ["🥇", "🥈", "🥉"]
        linhas_med = []
        for i, (uid, r) in enumerate(top3):
            m = guild.get_member(int(uid))
            nome = m.display_name if m else uid
            linhas_med.append(medalhas[i] + " **" + nome + "** — R$ " + str(round(r, 2)) + " (" + str(partidas_med.get(uid, 0)) + " partidas)")
        embed.add_field(name="🛡️ Top 3 Mediadores", value="\n".join(linhas_med), inline=False)

    return embed


class ViewReceitaInterativa(discord.ui.View):
    def __init__(self, guild_id, periodo="hoje"):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.periodo = periodo
        self.add_item(SelectPeriodoReceita(periodo))


class SelectPeriodoReceita(discord.ui.Select):
    def __init__(self, atual):
        super().__init__(placeholder="Período: " + atual, options=[
            discord.SelectOption(label="Hoje", value="hoje", emoji="📅"),
            discord.SelectOption(label="Ontem", value="ontem", emoji="📅"),
            discord.SelectOption(label="Esta Semana (Dom-Sáb)", value="semana", emoji="📅"),
            discord.SelectOption(label="Últimos 7 dias", value="7dias", emoji="📅"),
            discord.SelectOption(label="Este Mês", value="mes", emoji="📅"),
        ], row=0)

    async def callback(self, interaction):
        self.view.periodo = self.values[0]
        data = db.load(self.view.guild_id)
        embed = gerar_embed_receita(interaction.guild, data, self.values[0])
        view = ViewReceitaInterativa(self.view.guild_id, self.values[0])
        await interaction.response.edit_message(embed=embed, view=view)


# ══════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ranking", description="Veja o ranking de jogadores")
    async def ranking(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        embed = gerar_embed_ranking(interaction.guild, data, "vd", "geral")
        view = ViewRankingInterativo(interaction.guild.id, "vd", "geral")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="perfil", description="Veja o perfil de um jogador")
    async def perfil(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        data = db.load(interaction.guild.id)
        embed = gerar_embed_perfil(alvo, data)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="receita", description="[ADM] Receita da org por período")
    async def receita(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        embed = gerar_embed_receita(interaction.guild, data, "hoje")
        view = ViewReceitaInterativa(interaction.guild.id, "hoje")
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="historico-perfil", description="Histórico de partidas de um jogador")
    async def historico(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        data = db.load(interaction.guild.id)
        uid_int = alvo.id
        config = data["config"]
        emoji_moeda = config.get("moeda_emoji", "🪙")

        partidas = [p for p in data.get("historico", [])
                    if p.get("jogador1") == uid_int or p.get("jogador2") == uid_int]

        embed = discord.Embed(
            title="📋 Histórico — " + alvo.display_name,
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=alvo.display_avatar.url)

        if not partidas:
            embed.description = "Nenhuma partida encontrada."
        else:
            linhas = []
            for p in reversed(partidas[-10:]):
                res = "🏆" if p.get("vencedor") == uid_int else "❌"
                tipo = " (Revanche)" if p.get("tipo") == "revanche" else ""
                linhas.append(res + " `#" + p["id"] + "` — R$ " + str(p.get("valor", 0)) + " — " + p.get("modalidade", "?").upper() + tipo)
            embed.description = "\n".join(linhas)

        j = data["jogadores"].get(str(alvo.id), {})
        total = j.get("vitorias", 0) + j.get("derrotas", 0)
        wr = str(round(j.get("vitorias", 0) / total * 100, 1)) + "%" if total > 0 else "0%"
        embed.add_field(name="✅ Vitórias", value=str(j.get("vitorias", 0)), inline=True)
        embed.add_field(name="❌ Derrotas", value=str(j.get("derrotas", 0)), inline=True)
        embed.add_field(name="📊 Winrate", value=wr, inline=True)
        embed.add_field(name=emoji_moeda + " Moedas", value=str(j.get("moedas", 0)), inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="moeda-adicionar", description="[ADM] Adiciona moedas a um jogador")
    async def moeda_add(self, interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["moedas"] = data["jogadores"][uid].get("moedas", 0) + quantidade
        db.save(interaction.guild.id, data)
        emoji = data["config"].get("moeda_emoji", "🪙")
        await interaction.response.send_message(
            "✅ " + str(quantidade) + " " + emoji + " adicionadas para " + usuario.mention + ". Total: " + str(data["jogadores"][uid]["moedas"]),
            ephemeral=True
        )

    @app_commands.command(name="moeda-remover", description="[ADM] Remove moedas de um jogador")
    async def moeda_rem(self, interaction: discord.Interaction, usuario: discord.Member, quantidade: int):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["moedas"] = max(0, data["jogadores"][uid].get("moedas", 0) - quantidade)
        db.save(interaction.guild.id, data)
        emoji = data["config"].get("moeda_emoji", "🪙")
        await interaction.response.send_message(
            "✅ " + str(quantidade) + " " + emoji + " removidas de " + usuario.mention + ". Total: " + str(data["jogadores"][uid]["moedas"]),
            ephemeral=True
        )

    @app_commands.command(name="vitoria-adicionar", description="[ADM] Adiciona vitória a um jogador")
    async def vitoria_add(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["vitorias"] = data["jogadores"][uid].get("vitorias", 0) + 1
        data["ranking"]["geral"][uid] = data["ranking"]["geral"].get(uid, 0) + 1
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Vitória adicionada para " + usuario.mention + ".", ephemeral=True)

    @app_commands.command(name="vitoria-remover", description="[ADM] Remove vitória de um jogador")
    async def vitoria_rem(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            await interaction.response.send_message("❌ Jogador sem registro.", ephemeral=True)
            return
        data["jogadores"][uid]["vitorias"] = max(0, data["jogadores"][uid].get("vitorias", 0) - 1)
        if uid in data["ranking"]["geral"]:
            data["ranking"]["geral"][uid] = max(0, data["ranking"]["geral"][uid] - 1)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Vitória removida de " + usuario.mention + ".", ephemeral=True)

    @app_commands.command(name="derrota-adicionar", description="[ADM] Adiciona derrota a um jogador")
    async def derrota_add(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["derrotas"] = data["jogadores"][uid].get("derrotas", 0) + 1
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Derrota adicionada para " + usuario.mention + ".", ephemeral=True)

    @app_commands.command(name="derrota-remover", description="[ADM] Remove derrota de um jogador")
    async def derrota_rem(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid not in data["jogadores"]:
            await interaction.response.send_message("❌ Jogador sem registro.", ephemeral=True)
            return
        data["jogadores"][uid]["derrotas"] = max(0, data["jogadores"][uid].get("derrotas", 0) - 1)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Derrota removida de " + usuario.mention + ".", ephemeral=True)

    @app_commands.command(name="receita-mediador-resetar", description="[ADM] Reseta receita de um mediador")
    async def receita_reset(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        if uid in data["jogadores"]:
            data["jogadores"][uid]["receita_total"] = 0.0
            data["jogadores"][uid]["partidas_mediadas"] = 0
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Receita de " + usuario.mention + " resetada.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ranking(bot))
