"""
cogs/filas.py — Sistema de filas completo baseado na documentação oficial
"""
import discord
from discord.ext import commands
from discord import app_commands
import uuid
import asyncio
from datetime import datetime
from utils import database as db


# ══════════════════════════════════════════════════════════
#  EMBED DA FILA
# ══════════════════════════════════════════════════════════

async def criar_embed_fila(guild, jogo_id, mod_id, valor, jogadores_na_fila):
    data = db.load(guild.id)
    config = data["config"]
    mod = data["filas"].get(jogo_id, {}).get("modalidades", {}).get(mod_id, {})
    txt_nenhum = config.get("txt_nenhum_jogador", "Nenhum jogador na fila.")

    embed = discord.Embed(color=0x00FF00)  # Verde vivo igual ao original
    embed.title = mod_id.upper() + " |"
    embed.add_field(name="Valor Apostado", value="R$ " + str(round(valor, 2)), inline=True)
    embed.add_field(name="Modo", value="Partidas " + mod_id, inline=True)

    if jogadores_na_fila:
        texto = "\n".join(["Mobile | <@" + str(uid) + ">" for uid in jogadores_na_fila])
    else:
        texto = txt_nenhum

    embed.add_field(name="Jogadores na fila", value=texto, inline=False)

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    return embed


# ══════════════════════════════════════════════════════════
#  REGENERAR FILAS
# ══════════════════════════════════════════════════════════

async def regenerar_filas_canal(guild, canal, jogo_id, mod_id, valores):
    data = db.load(guild.id)
    config = data["config"]
    nome_btn = config.get("btn_entrar_label", "Mobile")
    nome_sair = config.get("btn_sair_label", "Sair")

    try:
        async for msg in canal.history(limit=200):
            if msg.author.id == guild.me.id:
                try:
                    await msg.delete()
                except Exception:
                    pass
    except Exception:
        pass

    if "mensagens_fila" not in data:
        data["mensagens_fila"] = {}

    for v_str in sorted(valores.keys(), key=lambda x: float(x), reverse=True):
        valor = float(v_str)
        fila_key = jogo_id + "_" + mod_id + "_" + str(valor)
        jogadores = [f["uid"] for f in data.get("filas_espera", {}).get(fila_key, [])]
        embed = await criar_embed_fila(guild, jogo_id, mod_id, valor, jogadores)

        view = discord.ui.View(timeout=None)
        btn1 = discord.ui.Button(
            label=nome_btn,
            style=discord.ButtonStyle.grey,
            custom_id="FILA|" + jogo_id + "|" + mod_id + "|" + str(valor) + "|entrar"
        )
        btn2 = discord.ui.Button(
            label=nome_sair,
            style=discord.ButtonStyle.red,
            custom_id="FILA|" + jogo_id + "|" + mod_id + "|" + str(valor) + "|sair"
        )
        view.add_item(btn1)
        view.add_item(btn2)

        msg = await canal.send(embed=embed, view=view)
        data["mensagens_fila"][fila_key] = {"canal_id": canal.id, "msg_id": msg.id}
        db.save(guild.id, data)


async def atualizar_embed_fila(guild, jogo_id, mod_id, valor):
    data = db.load(guild.id)
    fila_key = jogo_id + "_" + mod_id + "_" + str(valor)
    info = data.get("mensagens_fila", {}).get(fila_key)
    if not info:
        return
    canal = guild.get_channel(info["canal_id"])
    if not canal:
        return
    try:
        msg = await canal.fetch_message(info["msg_id"])
        jogadores = [f["uid"] for f in data.get("filas_espera", {}).get(fila_key, [])]
        embed = await criar_embed_fila(guild, jogo_id, mod_id, valor, jogadores)
        await msg.edit(embed=embed)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  LÓGICA DA FILA
# ══════════════════════════════════════════════════════════

async def entrar_fila(interaction, jogo_id, mod_id, valor):
    guild = interaction.guild
    data = db.load(guild.id)
    uid = interaction.user.id

    if uid in data.get("blacklist", []):
        await interaction.response.send_message("❌ Você está na blacklist.", ephemeral=True)
        return

    if not data.get("fila_mediadores", []):
        await interaction.response.send_message("❌ Nenhum mediador disponível no momento.", ephemeral=True)
        return

    fila_key = jogo_id + "_" + mod_id + "_" + str(valor)
    if "filas_espera" not in data:
        data["filas_espera"] = {}
    fila = data["filas_espera"].get(fila_key, [])

    if uid in [f["uid"] for f in fila]:
        await interaction.response.send_message("⏳ Você já está nessa fila!", ephemeral=True)
        return

    max_filas = data["config"].get("max_filas_jogador", 1)
    total = sum(1 for f in data["filas_espera"].values() if uid in [x["uid"] for x in f])
    if total >= max_filas:
        await interaction.response.send_message("❌ Limite de " + str(max_filas) + " fila(s) atingido.", ephemeral=True)
        return

    for p in data.get("partidas", {}).values():
        if uid in [p.get("jogador1"), p.get("jogador2")] and p["status"] in ("aguardando_confirmacao", "em_andamento"):
            await interaction.response.send_message("❌ Você já está em uma partida ativa.", ephemeral=True)
            return

    fila.append({"uid": uid})
    data["filas_espera"][fila_key] = fila
    db.save(guild.id, data)
    asyncio.create_task(atualizar_embed_fila(guild, jogo_id, mod_id, valor))

    if len(fila) >= 2:
        j1 = fila[0]["uid"]
        j2 = fila[1]["uid"]
        data = db.load(guild.id)
        data["filas_espera"][fila_key] = fila[2:]
        db.save(guild.id, data)
        await interaction.response.send_message("⚔️ Oponente encontrado! Criando canal...", ephemeral=True)
        await criar_canal_partida(guild, jogo_id, mod_id, valor, j1, j2)
    else:
        await interaction.response.send_message(
            "✅ Você entrou na fila **R$ " + str(round(valor, 2)) + "**! Aguardando oponente...",
            ephemeral=True
        )


async def sair_fila(interaction, jogo_id, mod_id, valor):
    guild = interaction.guild
    data = db.load(guild.id)
    uid = interaction.user.id
    fila_key = jogo_id + "_" + mod_id + "_" + str(valor)
    fila = data.get("filas_espera", {}).get(fila_key, [])

    if uid not in [f["uid"] for f in fila]:
        await interaction.response.send_message("❌ Você não está nessa fila.", ephemeral=True)
        return

    data["filas_espera"][fila_key] = [f for f in fila if f["uid"] != uid]
    db.save(guild.id, data)
    asyncio.create_task(atualizar_embed_fila(guild, jogo_id, mod_id, valor))
    await interaction.response.send_message("✅ Você saiu da fila.", ephemeral=True)


# ══════════════════════════════════════════════════════════
#  CRIAR CANAL PRIVADO
# ══════════════════════════════════════════════════════════

def calcular_premio(valor, v_data):
    tipo = v_data.get("tipo_taxa", "pct")
    if tipo == "fixo":
        taxa = v_data.get("taxa_fixo", 0)
    else:
        taxa = valor * (v_data.get("taxa_pct", 10) / 100)
    premio = (valor * 2) - (taxa * 2)
    return round(premio, 2), round(taxa, 2)


async def criar_canal_partida(guild, jogo_id, mod_id, valor, j1_id, j2_id):
    data = db.load(guild.id)
    config = data["config"]
    partida_id = str(uuid.uuid4())[:5].upper()

    # Pega taxa
    v_data = {}
    try:
        v_data = data["filas"][jogo_id]["modalidades"][mod_id]["valores"].get(str(valor), {})
    except Exception:
        pass
    premio, taxa = calcular_premio(valor, v_data)
    custo_adicional = data["filas"].get(jogo_id, {}).get("custo_adicional", 0.0)

    # Mediador
    fila_med = data.get("fila_mediadores", [])
    mediador_id = None
    if fila_med:
        modo = config.get("distribuicao_mediador", "1por1")
        if modo == "equilibrado":
            contagem = {}
            for p in data.get("partidas", {}).values():
                med = p.get("mediador")
                if med:
                    contagem[med] = contagem.get(med, 0) + 1
            mediador_id = min(fila_med, key=lambda x: contagem.get(x, 0))
        else:
            mediador_id = fila_med.pop(0)
            fila_med.append(mediador_id)
            data["fila_mediadores"] = fila_med

    # Categoria
    categoria = None
    tipo_criacao = config.get("tipo_criacao_fila", "categoria")
    if tipo_criacao in ("categoria", "mista"):
        mediador = guild.get_member(mediador_id) if mediador_id else None
        cat_nome = "Mediador-" + (mediador.display_name if mediador else "Partidas")
        for cat in guild.categories:
            if cat.name.lower() == cat_nome.lower():
                categoria = cat
                break
        if not categoria:
            try:
                categoria = await guild.create_category(cat_nome)
            except Exception:
                pass

    j1 = guild.get_member(j1_id)
    j2 = guild.get_member(j2_id)
    mediador = guild.get_member(mediador_id) if mediador_id else None

    overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
    for m in [j1, j2, mediador]:
        if m:
            overwrites[m] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            )
    cargo_med_id = config.get("cargo_mediador")
    if cargo_med_id:
        cargo = guild.get_role(cargo_med_id)
        if cargo:
            overwrites[cargo] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    nome_canal = "aguardando-" + partida_id
    canal = await guild.create_text_channel(nome_canal, category=categoria, overwrites=overwrites)

    data["partidas"][partida_id] = {
        "id": partida_id, "canal_id": canal.id,
        "jogo_id": jogo_id, "modalidade": mod_id, "valor": valor,
        "jogador1": j1_id, "jogador2": j2_id, "mediador": mediador_id,
        "status": "aguardando_confirmacao", "confirmacoes": [],
        "vencedor": None, "perdedor": None,
        "premio": premio, "taxa_por_jogador": taxa,
        "custo_adicional": custo_adicional,
        "criado_em": datetime.now().isoformat(),
    }
    if "stats" not in data:
        data["stats"] = []
    data["stats"].append({
        "tipo": "criada", "jogo_id": jogo_id, "modalidade": mod_id,
        "valor": valor, "partida_id": partida_id, "data": datetime.now().isoformat(),
    })
    db.save(guild.id, data)

    await postar_painel_aguardando(canal, data["partidas"][partida_id], j1, j2, mediador, config)


async def postar_painel_aguardando(canal, partida, j1, j2, mediador, config):
    """Painel inicial: Confirmar Partida / Cancelar"""
    jogo_id = partida.get("jogo_id", "").upper()
    mod_id = partida.get("modalidade", "")
    valor = partida["valor"]
    premio = partida.get("premio", valor * 2)
    custo_ad = partida.get("custo_adicional", 0)

    embed = discord.Embed(color=0x2d6a2d)
    embed.add_field(name="Aguardando", value="**" + jogo_id + "**\n" + mod_id + " ( Mobile )", inline=False)
    embed.add_field(
        name="Valores",
        value="Aposta: R$ " + str(round(valor, 2)) + "\nRecebe: R$ " + str(round(premio, 2)),
        inline=True
    )
    embed.add_field(
        name="Jogadores",
        value="1. " + (j1.mention if j1 else "?") + "\n2. " + (j2.mention if j2 else "?"),
        inline=True
    )
    embed.add_field(name="Valor Adicional", value="R$ " + str(round(custo_ad, 2)), inline=False)

    view = discord.ui.View(timeout=None)
    btn1 = discord.ui.Button(
        label="Confirmar Partida",
        style=discord.ButtonStyle.green,
        custom_id="CONF|" + partida["id"] + "|confirmar"
    )
    btn2 = discord.ui.Button(
        label="Cancelar",
        style=discord.ButtonStyle.red,
        custom_id="CONF|" + partida["id"] + "|cancelar"
    )
    view.add_item(btn1)
    view.add_item(btn2)

    mencoes = " ".join(filter(None, [
        j1.mention if j1 else None,
        j2.mention if j2 else None,
        mediador.mention if mediador else None,
    ]))
    await canal.send(mencoes, embed=embed, view=view)


# ══════════════════════════════════════════════════════════
#  HANDLERS DE CONFIRMAÇÃO
# ══════════════════════════════════════════════════════════

async def handler_confirmar(interaction, partida_id):
    guild = interaction.guild
    data = db.load(guild.id)
    partida = data["partidas"].get(partida_id)

    if not partida:
        await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)
        return

    uid = interaction.user.id
    if uid not in [partida["jogador1"], partida["jogador2"]]:
        await interaction.response.send_message("❌ Você não é jogador desta partida.", ephemeral=True)
        return

    if uid in partida["confirmacoes"]:
        await interaction.response.send_message("✅ Você já confirmou!", ephemeral=True)
        return

    partida["confirmacoes"].append(uid)

    if len(partida["confirmacoes"]) >= 2:
        partida["status"] = "em_andamento"
        db.save(guild.id, data)

        # Renomeia canal: aguardando-XXXX → fila-XXXX-mobile
        mod = partida.get("modalidade", "")
        try:
            await interaction.channel.edit(name="fila-" + partida_id + "-" + mod)
        except Exception:
            pass

        # Log de confirmação
        j1 = guild.get_member(partida["jogador1"])
        j2 = guild.get_member(partida["jogador2"])
        await interaction.response.send_message(
            "✅ " + interaction.user.mention + " confirmou a partida.\nTodos confirmaram! Partida iniciando..."
        )

        # Posta painel de andamento
        from cogs.partidas import postar_painel_andamento
        await postar_painel_andamento(interaction.channel, partida, guild, data["config"])
    else:
        db.save(guild.id, data)
        outro = partida["jogador2"] if uid == partida["jogador1"] else partida["jogador1"]
        await interaction.response.send_message(
            "✅ " + interaction.user.mention + " confirmou a partida.\nAgora falta apenas <@" + str(outro) + "> para confirmar."
        )


async def handler_cancelar(interaction, partida_id):
    guild = interaction.guild
    data = db.load(guild.id)
    partida = data["partidas"].get(partida_id)

    if not partida:
        await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)
        return

    uid = interaction.user.id
    if uid not in [partida["jogador1"], partida["jogador2"], partida.get("mediador")]:
        await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
        return

    partida["status"] = "cancelada"
    if "stats" not in data:
        data["stats"] = []
    data["stats"].append({
        "tipo": "cancelada", "jogo_id": partida.get("jogo_id", ""),
        "modalidade": partida.get("modalidade", ""), "valor": partida.get("valor", 0),
        "partida_id": partida_id, "data": datetime.now().isoformat(),
    })
    del data["partidas"][partida_id]
    db.save(guild.id, data)

    await interaction.response.send_message("❌ Partida cancelada por " + interaction.user.mention + ". Canal deletado em 5s.")
    await asyncio.sleep(5)
    try:
        await interaction.channel.delete()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════

class Filas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        if custom_id.startswith("FILA|"):
            partes = custom_id.split("|")
            if len(partes) >= 5:
                jogo_id = partes[1]
                mod_id = partes[2]
                try:
                    valor = float(partes[3])
                except ValueError:
                    return
                acao = partes[4]
                if acao == "entrar":
                    await entrar_fila(interaction, jogo_id, mod_id, valor)
                elif acao == "sair":
                    await sair_fila(interaction, jogo_id, mod_id, valor)

        elif custom_id.startswith("CONF|"):
            partes = custom_id.split("|")
            if len(partes) >= 3:
                partida_id = partes[1]
                acao = partes[2]
                if acao == "confirmar":
                    await handler_confirmar(interaction, partida_id)
                elif acao == "cancelar":
                    await handler_cancelar(interaction, partida_id)

    @app_commands.command(name="fila-regenerar", description="[ADM] Apaga e reosta todas as embeds de fila")
    async def fila_regenerar(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        data = db.load(guild.id)
        filas = data.get("filas", {})

        if not filas:
            await interaction.followup.send("❌ Nenhuma fila configurada.", ephemeral=True)
            return

        total = 0
        erros = []
        for jogo_id, jogo in filas.items():
            for mod_id, mod in jogo.get("modalidades", {}).items():
                canal_id = mod.get("canal_id")
                if not canal_id:
                    erros.append("⚠️ " + jogo["nome"] + " > " + mod["nome"] + ": sem canal")
                    continue
                canal = guild.get_channel(canal_id)
                if not canal:
                    erros.append("⚠️ " + jogo["nome"] + " > " + mod["nome"] + ": canal não encontrado")
                    continue
                valores = mod.get("valores", {})
                if not valores:
                    erros.append("⚠️ " + jogo["nome"] + " > " + mod["nome"] + ": sem valores")
                    continue
                await regenerar_filas_canal(guild, canal, jogo_id, mod_id, valores)
                total += len(valores)

        msg = "✅ **" + str(total) + " embed(s)** postadas!"
        if erros:
            msg += "\n" + "\n".join(erros)
        await interaction.followup.send(msg, ephemeral=True)

    @app_commands.command(name="ping", description="Verifica latência")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("🏓 Pong! `" + str(round(self.bot.latency * 1000)) + "ms`", ephemeral=True)

    @app_commands.command(name="fila-controle", description="[ADM] Remove mediador da fila")
    async def fila_controle(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        fila = data.get("fila_mediadores", [])
        if usuario.id not in fila:
            await interaction.response.send_message("❌ Não está na fila.", ephemeral=True)
            return
        fila.remove(usuario.id)
        data["fila_mediadores"] = fila
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ " + usuario.mention + " removido.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Filas(bot))
