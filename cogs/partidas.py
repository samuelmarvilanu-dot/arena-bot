"""
cogs/partidas.py — Sistema de partidas baseado na documentação oficial
"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime
from utils import database as db

try:
    import qrcode
    from PIL import Image
    import io
    TEM_QR = True
except ImportError:
    TEM_QR = False


# ══════════════════════════════════════════════════════════
#  QR CODE
# ══════════════════════════════════════════════════════════

def gerar_qrcode(pix_key, cor_borda="#FF0000"):
    if not TEM_QR or not pix_key:
        return None
    try:
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(pix_key)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        try:
            r = int(cor_borda[1:3], 16)
            g = int(cor_borda[3:5], 16)
            b = int(cor_borda[5:7], 16)
        except Exception:
            r, g, b = 255, 0, 0
        borda = 15
        nova = Image.new("RGB", (img.width + borda*2, img.height + borda*2), (r, g, b))
        nova.paste(img, (borda, borda))
        buf = io.BytesIO()
        nova.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="pix_qrcode.png")
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  PAINEL DE ANDAMENTO (pós-confirmação)
# ══════════════════════════════════════════════════════════

async def postar_painel_andamento(canal, partida, guild, config):
    """Painel com Definir Vencedor / Alterar Valor / Encerrar Aposta"""
    jogo_id = partida.get("jogo_id", "").upper()
    mod_id = partida.get("modalidade", "")
    valor = partida["valor"]
    premio = partida.get("premio", valor * 2)
    taxa = partida.get("taxa_por_jogador", 0)
    custo_ad = partida.get("custo_adicional", 0)
    partida_id = partida["id"]

    j1 = guild.get_member(partida["jogador1"])
    j2 = guild.get_member(partida["jogador2"])
    med_id = partida.get("mediador")
    mediador = guild.get_member(med_id) if med_id else None

    embed = discord.Embed(title="Vitória!", color=0x2d6a2d)
    embed.add_field(name="\u200b", value="**" + jogo_id + "**\n" + mod_id + " ( Mobile )", inline=False)
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
    embed.add_field(name="Mediador", value=mediador.mention if mediador else "Nenhum", inline=False)
    embed.add_field(name="Valor Adicional", value="R$ " + str(round(custo_ad, 2)), inline=False)

    view = discord.ui.View(timeout=None)
    btn1 = discord.ui.Button(label="Definir Vencedor", style=discord.ButtonStyle.green,
                              custom_id="PARTIDA|" + partida_id + "|vencedor", row=0)
    btn2 = discord.ui.Button(label="Alterar Valor", style=discord.ButtonStyle.blurple,
                              custom_id="PARTIDA|" + partida_id + "|alterar", row=0)
    btn3 = discord.ui.Button(label="Encerrar Aposta", style=discord.ButtonStyle.red,
                              custom_id="PARTIDA|" + partida_id + "|encerrar", row=1)
    view.add_item(btn1)
    view.add_item(btn2)
    view.add_item(btn3)

    await canal.send(embed=embed, view=view)

    # PIX do mediador como mensagem separada + QR Code
    if med_id:
        data = db.load(guild.id)
        pix_med = data["jogadores"].get(str(med_id), {}).get("pix", "")
        if pix_med:
            cor = config.get("qrcode_cor_borda", "#FF0000")
            qr_file = gerar_qrcode(pix_med, cor)
            if qr_file:
                await canal.send(file=qr_file)
            await canal.send("`" + pix_med + "`")


# ══════════════════════════════════════════════════════════
#  DEFINIR VENCEDOR
# ══════════════════════════════════════════════════════════

class ViewSelecionarVencedor(discord.ui.View):
    def __init__(self, partida_id, j1_id, j2_id, j1, j2):
        super().__init__(timeout=60)
        self.partida_id = partida_id
        sel = discord.ui.Select(
            placeholder="Selecione o Jogador.",
            options=[
                discord.SelectOption(
                    label=j1.display_name if j1 else str(j1_id),
                    description=(j1.name if j1 else str(j1_id)),
                    value=str(j1_id)
                ),
                discord.SelectOption(
                    label=j2.display_name if j2 else str(j2_id),
                    description=(j2.name if j2 else str(j2_id)),
                    value=str(j2_id)
                ),
            ]
        )
        sel.callback = self._selecionar
        self.add_item(sel)

    async def _selecionar(self, interaction):
        vencedor_id = int(interaction.data["values"][0])
        await decretar_vitoria(interaction, self.partida_id, vencedor_id)


async def decretar_vitoria(interaction, partida_id, vencedor_id):
    guild = interaction.guild
    data = db.load(guild.id)
    partida = data["partidas"].get(partida_id)

    if not partida:
        await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)
        return

    perdedor_id = partida["jogador2"] if vencedor_id == partida["jogador1"] else partida["jogador1"]
    valor = partida["valor"]
    taxa = partida.get("taxa_por_jogador", 0)
    premio = partida.get("premio", valor * 2)

    # Atualiza perfis
    uid_v = str(vencedor_id)
    uid_p = str(perdedor_id)
    for uid in [uid_v, uid_p]:
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()

    data["jogadores"][uid_v]["vitorias"] = data["jogadores"][uid_v].get("vitorias", 0) + 1
    data["jogadores"][uid_p]["derrotas"] = data["jogadores"][uid_p].get("derrotas", 0) + 1

    # Maior sequência
    seq_atual = data["jogadores"][uid_v].get("seq_atual", 0) + 1
    data["jogadores"][uid_v]["seq_atual"] = seq_atual
    if seq_atual > data["jogadores"][uid_v].get("maior_sequencia", 0):
        data["jogadores"][uid_v]["maior_sequencia"] = seq_atual
    data["jogadores"][uid_p]["seq_atual"] = 0

    # Ranking
    data["ranking"]["geral"][uid_v] = data["ranking"]["geral"].get(uid_v, 0) + 1

    # Moedas só pro vencedor
    jogo_config = data["filas"].get(partida.get("jogo_id", ""), {})
    moedas = jogo_config.get("moedas_por_partida", 1)
    data["jogadores"][uid_v]["moedas"] = data["jogadores"][uid_v].get("moedas", 0) + moedas

    # Receita mediador (taxa de AMBOS)
    med_id = partida.get("mediador")
    if med_id:
        uid_m = str(med_id)
        if uid_m not in data["jogadores"]:
            data["jogadores"][uid_m] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid_m]["receita_total"] = data["jogadores"][uid_m].get("receita_total", 0) + (taxa * 2)
        data["jogadores"][uid_m]["partidas_mediadas"] = data["jogadores"][uid_m].get("partidas_mediadas", 0) + 1

    # Finaliza partida
    partida.update({
        "status": "finalizada", "vencedor": vencedor_id, "perdedor": perdedor_id,
        "data_fim": datetime.now().isoformat(),
    })
    if "historico" not in data:
        data["historico"] = []
    data["historico"].append(dict(partida))
    del data["partidas"][partida_id]

    if "stats" not in data:
        data["stats"] = []
    data["stats"].append({
        "tipo": "encerrada", "jogo_id": partida.get("jogo_id", ""),
        "modalidade": partida.get("modalidade", ""), "valor": valor,
        "partida_id": partida_id, "data": datetime.now().isoformat(),
    })
    db.save(guild.id, data)

    vencedor = guild.get_member(vencedor_id)
    perdedor = guild.get_member(perdedor_id)

    # Embed resultado — igual ao original
    embed = discord.Embed(title="Vitória!", color=0x2d6a2d)
    jogo_id = partida.get("jogo_id", "").upper()
    mod_id = partida.get("modalidade", "")
    embed.add_field(name="\u200b", value="**" + jogo_id + "**\n" + mod_id, inline=False)
    embed.add_field(name="Valor da aposta", value="R$ " + str(round(valor, 2)), inline=True)
    embed.add_field(name="Valor do ganho", value="R$ " + str(round(premio, 2)), inline=True)
    embed.add_field(name="🟢 Vencedor", value=vencedor.mention if vencedor else str(vencedor_id), inline=True)
    embed.add_field(name="🔴 Perdedor", value=perdedor.mention if perdedor else str(perdedor_id), inline=True)

    view = ViewPosResultado(partida_id, vencedor_id, perdedor_id)

    await interaction.response.send_message("✅ Vencedor definido!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=view)

    # Log
    canal_log_id = data["config"].get("log_partidas_concluidas") or data["config"].get("canal_logs")
    if canal_log_id:
        canal_log = guild.get_channel(canal_log_id)
        if canal_log:
            try:
                await canal_log.send(embed=embed)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════
#  VIEW PÓS-RESULTADO
# ══════════════════════════════════════════════════════════

class ViewPosResultado(discord.ui.View):
    def __init__(self, partida_id, vencedor_id, perdedor_id):
        super().__init__(timeout=None)
        self.partida_id = partida_id
        self.vencedor_id = vencedor_id
        self.perdedor_id = perdedor_id

    @discord.ui.button(label="Revanche", style=discord.ButtonStyle.green,
                       custom_id="POS|revanche", row=0)
    async def revanche(self, interaction, button):
        uid = interaction.user.id
        if uid not in [self.vencedor_id, self.perdedor_id]:
            await interaction.response.send_message("❌ Você não é jogador desta partida.", ephemeral=True)
            return

        data = db.load(interaction.guild.id)
        # Busca partida no histórico
        partida_orig = next((p for p in reversed(data.get("historico", [])) if p.get("id") == self.partida_id), None)
        if not partida_orig:
            await interaction.response.send_message("❌ Partida original não encontrada.", ephemeral=True)
            return

        import uuid as _uuid
        nova_id = str(_uuid.uuid4())[:5].upper()
        rev_num = partida_orig.get("revanche_num", 0) + 1

        nova = {
            "id": nova_id, "canal_id": interaction.channel.id,
            "jogo_id": partida_orig["jogo_id"], "modalidade": partida_orig["modalidade"],
            "valor": partida_orig["valor"], "jogador1": self.vencedor_id, "jogador2": self.perdedor_id,
            "mediador": partida_orig.get("mediador"), "status": "em_andamento",
            "confirmacoes": [self.vencedor_id, self.perdedor_id],
            "vencedor": None, "perdedor": None,
            "premio": partida_orig.get("premio", 0), "taxa_por_jogador": partida_orig.get("taxa_por_jogador", 0),
            "custo_adicional": partida_orig.get("custo_adicional", 0),
            "criado_em": datetime.now().isoformat(),
            "tipo": "revanche", "revanche_num": rev_num, "partida_pai": self.partida_id,
        }
        data["partidas"][nova_id] = nova
        if "stats" not in data:
            data["stats"] = []
        data["stats"].append({
            "tipo": "revanche", "jogo_id": nova["jogo_id"], "modalidade": nova["modalidade"],
            "valor": nova["valor"], "partida_id": nova_id, "data": datetime.now().isoformat(),
        })
        db.save(interaction.guild.id, data)

        jogo_config = data["filas"].get(nova["jogo_id"], {})
        moedas_rev = jogo_config.get("moedas_por_revanche", 1)

        await interaction.response.send_message("🔄 **Revanche #" + str(rev_num) + " iniciada!**")
        await postar_painel_andamento(interaction.channel, nova, interaction.guild, data["config"])

    @discord.ui.button(label="Vitória por W.O?", style=discord.ButtonStyle.blurple,
                       custom_id="POS|wo", row=0)
    async def wo(self, interaction, button):
        data = db.load(interaction.guild.id)
        if not _tem_permissao(interaction, data):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        await interaction.response.send_message(
            "🏆 | " + interaction.user.mention + ", a vitória foi definida como W.O."
        )

    @discord.ui.button(label="Encerrar Aposta", style=discord.ButtonStyle.red,
                       custom_id="POS|encerrar", row=1)
    async def encerrar(self, interaction, button):
        data = db.load(interaction.guild.id)
        if not _tem_permissao(interaction, data):
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        await interaction.response.send_message(
            "⏰ | " + interaction.user.mention + ", a partida está sendo encerrada, aguarde..."
        )
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  MODAL ALTERAR VALOR
# ══════════════════════════════════════════════════════════

class ModalAlterarValor(discord.ui.Modal, title="Alterar Valor da Partida"):
    novo_valor = discord.ui.TextInput(label="Novo valor (R$)", placeholder="ex: 5.00", max_length=10)

    def __init__(self, partida_id, valor_atual):
        super().__init__()
        self.partida_id = partida_id
        self.novo_valor.default = str(valor_atual)

    async def on_submit(self, interaction):
        try:
            novo = float(self.novo_valor.value)
        except ValueError:
            await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
            return
        data = db.load(interaction.guild.id)
        partida = data["partidas"].get(self.partida_id)
        if not partida:
            await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)
            return
        partida["valor"] = novo
        # Recalcula prêmio
        from cogs.filas import calcular_premio
        v_data = {}
        try:
            v_data = data["filas"][partida["jogo_id"]]["modalidades"][partida["modalidade"]]["valores"].get(str(novo), {})
        except Exception:
            pass
        premio, taxa = calcular_premio(novo, v_data)
        partida["premio"] = premio
        partida["taxa_por_jogador"] = taxa
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Valor alterado para R$ " + str(round(novo, 2)), ephemeral=True)


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def _tem_permissao(interaction, data):
    uid = interaction.user.id
    if interaction.user.guild_permissions.administrator:
        return True
    cargo_med_id = data["config"].get("cargo_mediador")
    if cargo_med_id:
        cargo = interaction.guild.get_role(cargo_med_id)
        if cargo and cargo in interaction.user.roles:
            return True
    return False


def _tem_permissao_partida(interaction, data, partida):
    if interaction.user.id == partida.get("mediador"):
        return True
    return _tem_permissao(interaction, data)


# ══════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════

class Partidas(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")

        # PARTIDA|partida_id|acao
        if custom_id.startswith("PARTIDA|"):
            partes = custom_id.split("|")
            if len(partes) >= 3:
                partida_id = partes[1]
                acao = partes[2]
                data = db.load(interaction.guild.id)
                partida = data["partidas"].get(partida_id)
                if not partida:
                    await interaction.response.send_message("❌ Partida não encontrada.", ephemeral=True)
                    return

                if not _tem_permissao_partida(interaction, data, partida):
                    await interaction.response.send_message("❌ Apenas o mediador pode usar isso.", ephemeral=True)
                    return

                if acao == "vencedor":
                    embed = discord.Embed(
                        title="❓ Selecione o jogador",
                        description="Dica: use **+v @usuario** para setar vitória rapidamente.",
                        color=discord.Color.blurple()
                    )
                    j1 = interaction.guild.get_member(partida["jogador1"])
                    j2 = interaction.guild.get_member(partida["jogador2"])
                    view = ViewSelecionarVencedor(partida_id, partida["jogador1"], partida["jogador2"], j1, j2)
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

                elif acao == "alterar":
                    await interaction.response.send_modal(ModalAlterarValor(partida_id, partida["valor"]))

                elif acao == "encerrar":
                    partida["status"] = "wo"
                    if "historico" not in data:
                        data["historico"] = []
                    data["historico"].append(dict(partida))
                    del data["partidas"][partida_id]
                    if "stats" not in data:
                        data["stats"] = []
                    data["stats"].append({
                        "tipo": "wo", "jogo_id": partida.get("jogo_id", ""),
                        "modalidade": partida.get("modalidade", ""), "valor": partida["valor"],
                        "partida_id": partida_id, "data": datetime.now().isoformat(),
                    })
                    db.save(interaction.guild.id, data)
                    await interaction.response.send_message(
                        "⏰ | " + interaction.user.mention + ", a partida está sendo encerrada, aguarde..."
                    )
                    await asyncio.sleep(5)
                    try:
                        await interaction.channel.delete()
                    except Exception:
                        pass

        # POS|acao — tratado pela ViewPosResultado mas fallback aqui
        elif custom_id.startswith("POS|"):
            pass  # Handled by ViewPosResultado buttons


async def setup(bot):
    await bot.add_cog(Partidas(bot))
