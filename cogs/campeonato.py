"""
cogs/campeonato.py — Sistema completo de campeonatos
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
import math
from utils import database as db


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def gerar_bracket(jogadores):
    """Gera chaves mata-mata embaralhadas."""
    lista = list(jogadores)
    random.shuffle(lista)
    rodadas = []
    while len(lista) < 2:
        lista.append(None)
    # Completa pra potencia de 2
    prox = 2 ** math.ceil(math.log2(max(len(lista), 2)))
    while len(lista) < prox:
        lista.append(None)  # bye
    # Primeira rodada
    partidas = []
    for i in range(0, len(lista), 2):
        partidas.append({"j1": lista[i], "j2": lista[i+1], "vencedor": None})
    rodadas.append(partidas)
    return rodadas


def embed_campeonato(camp, guild):
    """Embed principal do campeonato."""
    cor_map = {
        "aberto": discord.Color.green(),
        "em_andamento": discord.Color.blurple(),
        "finalizado": discord.Color.gold(),
    }
    status = camp.get("status", "aberto")
    embed = discord.Embed(
        title="🏆 " + camp["nome"],
        description=camp.get("descricao", ""),
        color=cor_map.get(status, discord.Color.blurple())
    )
    if camp.get("banner"):
        embed.set_image(url=camp["banner"])
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="📋 Formato", value=camp.get("formato", "Mata-mata").title(), inline=True)
    embed.add_field(name="👥 Vagas", value=str(len(camp.get("inscritos", {}))) + "/" + str(camp.get("max_jogadores", 16)), inline=True)
    embed.add_field(name="💰 Inscrição", value="R$ " + str(round(camp.get("valor", 0), 2)) if camp.get("valor", 0) > 0 else "Gratuito", inline=True)

    premio = camp.get("premio", "")
    if premio:
        embed.add_field(name="🎁 Prêmio", value=premio, inline=True)

    data_ini = camp.get("data_inicio", "A definir")
    embed.add_field(name="📅 Início", value=data_ini, inline=True)

    status_txt = {"aberto": "✅ Inscrições abertas", "em_andamento": "⚔️ Em andamento", "finalizado": "🏆 Finalizado"}.get(status, status)
    embed.add_field(name="Status", value=status_txt, inline=True)

    inscritos = camp.get("inscritos", {})
    if inscritos:
        nomes = []
        for uid, info in list(inscritos.items())[:10]:
            m = guild.get_member(int(uid))
            nome = m.display_name if m else "ID:" + uid
            pago = "✅" if info.get("pago") else "⏳"
            nomes.append(pago + " " + nome)
        embed.add_field(name="Inscritos (" + str(len(inscritos)) + ")", value="\n".join(nomes), inline=False)

    embed.set_footer(text="Arena X1 • " + datetime.now().strftime("%d/%m/%Y %H:%M"))
    return embed


def embed_bracket(camp, guild, rodada_idx=0):
    """Embed das chaves do campeonato."""
    embed = discord.Embed(title="⚔️ Chaves — " + camp["nome"], color=discord.Color.blurple())
    rodadas = camp.get("rodadas", [])

    nomes_rodada = ["Oitavas", "Quartas", "Semifinal", "Final"]

    for i, rodada in enumerate(rodadas):
        if i < rodada_idx or not rodada:
            continue
        nome_r = nomes_rodada[i] if i < len(nomes_rodada) else "Rodada " + str(i+1)
        linhas = []
        for j, p in enumerate(rodada):
            j1 = guild.get_member(int(p["j1"])) if p["j1"] else None
            j2 = guild.get_member(int(p["j2"])) if p["j2"] else None
            n1 = j1.display_name if j1 else ("BYE" if p["j1"] is None else str(p["j1"]))
            n2 = j2.display_name if j2 else ("BYE" if p["j2"] is None else str(p["j2"]))
            if p.get("vencedor"):
                v = guild.get_member(int(p["vencedor"]))
                vn = v.display_name if v else str(p["vencedor"])
                linhas.append("`" + str(j+1) + ".` **" + n1 + "** vs **" + n2 + "** → 🏆 " + vn)
            else:
                linhas.append("`" + str(j+1) + ".` **" + n1 + "** vs **" + n2 + "**")
        embed.add_field(name=nome_r, value="\n".join(linhas) if linhas else "Aguardando...", inline=False)
        break  # Mostra só rodada atual

    return embed


# ══════════════════════════════════════════════════════════
#  MODAIS
# ══════════════════════════════════════════════════════════

class ModalCriarCampeonato(discord.ui.Modal, title="Criar Campeonato"):
    nome = discord.ui.TextInput(label="Nome do campeonato", placeholder="ex: Copa Arena X1", max_length=50)
    descricao = discord.ui.TextInput(label="Descrição", placeholder="ex: Campeonato mensal de EFootball", max_length=200, style=discord.TextStyle.paragraph, required=False)
    premio = discord.ui.TextInput(label="Prêmio", placeholder="ex: R$ 50,00 + cargo Campeão", max_length=100, required=False)
    data_inicio = discord.ui.TextInput(label="Data de início (DD/MM/YYYY)", placeholder="ex: 20/07/2026", max_length=20, required=False)
    banner = discord.ui.TextInput(label="URL do banner (imagem)", placeholder="https://...", max_length=300, required=False)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        if "campeonatos" not in data:
            data["campeonatos"] = {}

        camp_id = str(len(data["campeonatos"]) + 1)
        data["campeonatos"][camp_id] = {
            "id": camp_id,
            "nome": self.nome.value,
            "descricao": self.descricao.value,
            "premio": self.premio.value,
            "data_inicio": self.data_inicio.value or "A definir",
            "banner": self.banner.value or "",
            "formato": "mata-mata",
            "max_jogadores": 16,
            "valor": 0.0,
            "status": "configurando",
            "inscritos": {},
            "rodadas": [],
            "rodada_atual": 0,
            "canal_id": None,
            "msg_id": None,
            "criado_em": datetime.now().isoformat(),
            "criado_por": interaction.user.id,
        }
        db.save(interaction.guild.id, data)

        embed = discord.Embed(title="Campeonato criado!", color=discord.Color.green())
        embed.description = "**" + self.nome.value + "** criado! Agora configure abaixo."
        await interaction.response.send_message(embed=embed, view=ViewConfigurarCampeonato(camp_id), ephemeral=True)


class ModalEditarValor(discord.ui.Modal, title="Valor da Inscrição"):
    valor = discord.ui.TextInput(label="Valor (R$) — 0 para gratuito", placeholder="ex: 10.00", max_length=10)
    pix = discord.ui.TextInput(label="Chave PIX para pagamento", placeholder="ex: email@gmail.com", max_length=100, required=False)

    def __init__(self, camp_id):
        super().__init__()
        self.camp_id = camp_id

    async def on_submit(self, interaction):
        try:
            v = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.response.send_message("Valor inválido!", ephemeral=True)
            return
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["valor"] = v
        if self.pix.value:
            data["campeonatos"][self.camp_id]["pix"] = self.pix.value
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Valor: R$ " + str(round(v, 2)), ephemeral=True)


# ══════════════════════════════════════════════════════════
#  VIEWS
# ══════════════════════════════════════════════════════════

class ViewConfigurarCampeonato(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=300)
        self.camp_id = camp_id
        # Select formato
        sel_fmt = discord.ui.Select(placeholder="Formato", options=[
            discord.SelectOption(label="Mata-mata", value="mata-mata", emoji="⚔️"),
            discord.SelectOption(label="Fase de grupos + Mata-mata", value="grupos", emoji="📊"),
            discord.SelectOption(label="Pontos corridos", value="pontos", emoji="📋"),
        ], row=0)
        sel_fmt.callback = self._formato
        self.add_item(sel_fmt)
        # Select max jogadores
        sel_jog = discord.ui.Select(placeholder="Máximo de jogadores", options=[
            discord.SelectOption(label="4 jogadores", value="4"),
            discord.SelectOption(label="8 jogadores", value="8"),
            discord.SelectOption(label="16 jogadores", value="16"),
            discord.SelectOption(label="32 jogadores", value="32"),
            discord.SelectOption(label="64 jogadores", value="64"),
        ], row=1)
        sel_jog.callback = self._max_jogadores
        self.add_item(sel_jog)

    async def _formato(self, interaction):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["formato"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Formato: " + interaction.data["values"][0], ephemeral=True)

    async def _max_jogadores(self, interaction):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["max_jogadores"] = int(interaction.data["values"][0])
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Máximo: " + interaction.data["values"][0] + " jogadores", ephemeral=True)

    @discord.ui.button(label="💰 Valor/PIX", style=discord.ButtonStyle.blurple, row=2)
    async def valor(self, interaction, button):
        await interaction.response.send_modal(ModalEditarValor(self.camp_id))

    @discord.ui.button(label="📢 Postar no Canal", style=discord.ButtonStyle.green, row=2)
    async def postar(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="Selecione o canal", color=0x5865F2),
            view=ViewSelecionarCanalCamp(self.camp_id)
        )

    @discord.ui.button(label="🗑️ Cancelar", style=discord.ButtonStyle.red, row=2)
    async def cancelar(self, interaction, button):
        data = db.load(interaction.guild.id)
        del data["campeonatos"][self.camp_id]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(content="Campeonato cancelado.", embed=None, view=None)


class ViewSelecionarCanalCamp(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=120)
        self.camp_id = camp_id
        sel = discord.ui.ChannelSelect(placeholder="Selecione o canal do campeonato", channel_types=[discord.ChannelType.text], row=0)
        sel.callback = self._canal
        self.add_item(sel)

    async def _canal(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        canal = interaction.guild.get_channel(canal_id)
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"][self.camp_id]
        camp["canal_id"] = canal_id
        camp["status"] = "aberto"

        embed = embed_campeonato(camp, interaction.guild)
        pix = camp.get("pix", data["config"].get("pix_cargos", "Não configurado"))
        view = ViewInscricao(self.camp_id, pix)
        msg = await canal.send(embed=embed, view=view)
        camp["msg_id"] = msg.id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(
            content="✅ Campeonato **" + camp["nome"] + "** postado em " + canal.mention + "!",
            embed=None, view=None
        )


class ViewInscricao(discord.ui.View):
    """Painel público de inscrição no campeonato."""
    def __init__(self, camp_id, pix=""):
        super().__init__(timeout=None)
        self.camp_id = camp_id
        self.pix = pix

    @discord.ui.button(label="✅ Me Inscrever", style=discord.ButtonStyle.green, custom_id="CAMP|inscrever")
    async def inscrever(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp:
            await interaction.response.send_message("Campeonato não encontrado.", ephemeral=True)
            return
        if camp["status"] != "aberto":
            await interaction.response.send_message("Inscrições encerradas!", ephemeral=True)
            return
        uid = str(interaction.user.id)
        if uid in camp["inscritos"]:
            await interaction.response.send_message("Você já está inscrito!", ephemeral=True)
            return
        if len(camp["inscritos"]) >= camp["max_jogadores"]:
            await interaction.response.send_message("Campeonato lotado!", ephemeral=True)
            return

        camp["inscritos"][uid] = {"pago": camp["valor"] == 0, "inscrito_em": datetime.now().isoformat()}
        db.save(interaction.guild.id, data)

        if camp["valor"] > 0:
            pix = camp.get("pix", self.pix)
            embed = discord.Embed(title="Inscrição pendente!", color=discord.Color.yellow())
            embed.description = "Você foi inscrito! Faça o pagamento para confirmar sua vaga."
            embed.add_field(name="Valor", value="R$ " + str(round(camp["valor"], 2)), inline=True)
            embed.add_field(name="PIX", value="`" + pix + "`", inline=False)
            embed.set_footer(text="Após pagar, aguarde o admin confirmar.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("✅ Inscrição confirmada!", ephemeral=True)

        # Atualiza embed do campeonato
        await _atualizar_embed_camp(interaction, data, camp)

    @discord.ui.button(label="❌ Cancelar Inscrição", style=discord.ButtonStyle.red, custom_id="CAMP|cancelar_inscricao")
    async def cancelar(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        uid = str(interaction.user.id)
        if not camp or uid not in camp["inscritos"]:
            await interaction.response.send_message("Você não está inscrito.", ephemeral=True)
            return
        del camp["inscritos"][uid]
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Inscrição cancelada.", ephemeral=True)
        await _atualizar_embed_camp(interaction, data, camp)

    @discord.ui.button(label="📋 Ver Inscritos", style=discord.ButtonStyle.grey, custom_id="CAMP|ver_inscritos")
    async def ver(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp:
            await interaction.response.send_message("Campeonato não encontrado.", ephemeral=True)
            return
        inscritos = camp.get("inscritos", {})
        if not inscritos:
            await interaction.response.send_message("Nenhum inscrito ainda.", ephemeral=True)
            return
        linhas = []
        for uid, info in inscritos.items():
            m = interaction.guild.get_member(int(uid))
            nome = m.display_name if m else uid
            pago = "✅" if info.get("pago") else "⏳ Aguardando pagamento"
            linhas.append(pago + " " + nome)
        embed = discord.Embed(title="Inscritos — " + camp["nome"], color=discord.Color.blurple())
        embed.description = "\n".join(linhas)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def _atualizar_embed_camp(interaction, data, camp):
    """Atualiza a embed do campeonato no canal."""
    canal_id = camp.get("canal_id")
    msg_id = camp.get("msg_id")
    if not canal_id or not msg_id:
        return
    canal = interaction.guild.get_channel(canal_id)
    if not canal:
        return
    try:
        msg = await canal.fetch_message(msg_id)
        pix = camp.get("pix", "")
        await msg.edit(embed=embed_campeonato(camp, interaction.guild), view=ViewInscricao(camp["id"], pix))
    except Exception:
        pass


class ViewAdminCampeonato(discord.ui.View):
    """Painel admin do campeonato."""
    def __init__(self, camp_id):
        super().__init__(timeout=300)
        self.camp_id = camp_id

    @discord.ui.button(label="✅ Confirmar Pagamento", style=discord.ButtonStyle.green, row=0)
    async def confirmar_pag(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        inscritos = {uid: info for uid, info in camp["inscritos"].items() if not info.get("pago")}
        if not inscritos:
            await interaction.response.send_message("Todos já pagaram!", ephemeral=True)
            return
        opcoes = []
        for uid, info in list(inscritos.items())[:25]:
            m = interaction.guild.get_member(int(uid))
            nome = m.display_name if m else uid
            opcoes.append(discord.SelectOption(label=nome, value=uid))
        sel = discord.ui.Select(placeholder="Selecione quem pagou", options=opcoes)
        view = discord.ui.View(timeout=60)
        async def cb(i):
            uid = sel.values[0]
            data2 = db.load(i.guild.id)
            data2["campeonatos"][self.camp_id]["inscritos"][uid]["pago"] = True
            db.save(i.guild.id, data2)
            m = i.guild.get_member(int(uid))
            await i.response.send_message("✅ Pagamento de " + (m.mention if m else uid) + " confirmado!", ephemeral=True)
            await _atualizar_embed_camp(i, data2, data2["campeonatos"][self.camp_id])
        sel.callback = cb
        view.add_item(sel)
        await interaction.response.send_message("Confirmar pagamento:", view=view, ephemeral=True)

    @discord.ui.button(label="⚔️ Iniciar Campeonato", style=discord.ButtonStyle.blurple, row=0)
    async def iniciar(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        pagantes = [uid for uid, info in camp["inscritos"].items() if info.get("pago")]
        if len(pagantes) < 2:
            await interaction.response.send_message("Mínimo 2 jogadores confirmados!", ephemeral=True)
            return
        rodadas = gerar_bracket(pagantes)
        camp["rodadas"] = rodadas
        camp["rodada_atual"] = 0
        camp["status"] = "em_andamento"
        db.save(interaction.guild.id, data)

        # Cria canal de organização
        cat = None
        canal_org = await interaction.guild.create_text_channel("bracket-" + camp["nome"].lower().replace(" ", "-"), category=cat)
        camp["canal_org_id"] = canal_org.id
        db.save(interaction.guild.id, data)

        embed_br = embed_bracket(camp, interaction.guild, 0)
        view_bracket = ViewBracket(self.camp_id)
        await canal_org.send(embed=embed_br, view=view_bracket)
        await interaction.response.send_message("⚔️ Campeonato iniciado! Canal: " + canal_org.mention, ephemeral=True)
        await _atualizar_embed_camp(interaction, data, camp)

    @discord.ui.button(label="🗑️ Encerrar", style=discord.ButtonStyle.red, row=1)
    async def encerrar(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["status"] = "finalizado"
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Campeonato encerrado.", ephemeral=True)


class ViewBracket(discord.ui.View):
    """View do bracket com confirmação de vencedores."""
    def __init__(self, camp_id):
        super().__init__(timeout=None)
        self.camp_id = camp_id

    @discord.ui.button(label="🏆 Confirmar Vencedor", style=discord.ButtonStyle.green, custom_id="CAMP|vencedor")
    async def vencedor(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp:
            await interaction.response.send_message("Campeonato não encontrado.", ephemeral=True)
            return
        rodada_idx = camp.get("rodada_atual", 0)
        rodada = camp["rodadas"][rodada_idx]

        # Pega partidas sem vencedor
        pendentes = [(i, p) for i, p in enumerate(rodada) if not p.get("vencedor") and p["j1"] and p["j2"]]
        if not pendentes:
            await interaction.response.send_message("Todas as partidas desta rodada já têm vencedor!", ephemeral=True)
            return

        # Select de partida
        opcoes_partida = []
        for i, p in pendentes[:25]:
            j1 = interaction.guild.get_member(int(p["j1"]))
            j2 = interaction.guild.get_member(int(p["j2"]))
            n1 = j1.display_name if j1 else str(p["j1"])
            n2 = j2.display_name if j2 else str(p["j2"])
            opcoes_partida.append(discord.SelectOption(label=n1 + " vs " + n2, value=str(i)))

        sel_partida = discord.ui.Select(placeholder="Selecione a partida", options=opcoes_partida)
        view_p = discord.ui.View(timeout=60)

        async def sel_partida_cb(i):
            idx_partida = int(sel_partida.values[0])
            partida = rodada[idx_partida]
            j1 = i.guild.get_member(int(partida["j1"]))
            j2 = i.guild.get_member(int(partida["j2"]))
            n1 = j1.display_name if j1 else str(partida["j1"])
            n2 = j2.display_name if j2 else str(partida["j2"])

            sel_venc = discord.ui.Select(placeholder="Quem venceu?", options=[
                discord.SelectOption(label=n1, value=str(partida["j1"]), emoji="🏆"),
                discord.SelectOption(label=n2, value=str(partida["j2"]), emoji="🏆"),
            ])
            view_v = discord.ui.View(timeout=60)

            async def sel_venc_cb(i2):
                vencedor_id = sel_venc.values[0]
                data2 = db.load(i2.guild.id)
                camp2 = data2["campeonatos"][self.camp_id]
                camp2["rodadas"][rodada_idx][idx_partida]["vencedor"] = vencedor_id
                db.save(i2.guild.id, data2)

                # Verifica se rodada terminou
                rodada2 = camp2["rodadas"][rodada_idx]
                todos_prontos = all(p.get("vencedor") or not p["j2"] for p in rodada2)

                if todos_prontos:
                    # Avança para próxima rodada
                    vencedores = [p["vencedor"] or p["j1"] for p in rodada2]
                    if len(vencedores) == 1:
                        # Campeão!
                        camp2["status"] = "finalizado"
                        camp2["campeao"] = vencedores[0]
                        db.save(i2.guild.id, data2)
                        m = i2.guild.get_member(int(vencedores[0]))
                        embed_fim = discord.Embed(title="🏆 CAMPEÃO!", color=discord.Color.gold())
                        embed_fim.description = (m.mention if m else vencedores[0]) + " é o campeão de **" + camp2["nome"] + "**!"
                        if camp2.get("premio"):
                            embed_fim.add_field(name="Prêmio", value=camp2["premio"])
                        await i2.channel.send(embed=embed_fim)

                        # Salva no histórico de campeões
                        data2.setdefault("historico_campeoes", []).append({
                            "campeonato": camp2["nome"],
                            "campeao_id": vencedores[0],
                            "data": datetime.now().isoformat(),
                            "premio": camp2.get("premio", ""),
                        })
                        db.save(i2.guild.id, data2)
                        await i2.response.send_message("🏆 " + (m.mention if m else vencedores[0]) + " é o campeão!", ephemeral=False)
                    else:
                        # Próxima rodada
                        nova_rodada = []
                        for k in range(0, len(vencedores), 2):
                            nova_rodada.append({
                                "j1": vencedores[k],
                                "j2": vencedores[k+1] if k+1 < len(vencedores) else None,
                                "vencedor": None
                            })
                        camp2["rodadas"].append(nova_rodada)
                        camp2["rodada_atual"] += 1
                        db.save(i2.guild.id, data2)

                        embed_br = embed_bracket(camp2, i2.guild, camp2["rodada_atual"])
                        await i2.channel.send(embed=embed_br, view=ViewBracket(self.camp_id))
                        await i2.response.send_message("✅ Rodada avançada!", ephemeral=True)
                else:
                    # Atualiza bracket atual
                    embed_br = embed_bracket(camp2, i2.guild, rodada_idx)
                    await i2.channel.send(embed=embed_br, view=ViewBracket(self.camp_id))
                    vn = i2.guild.get_member(int(vencedor_id))
                    await i2.response.send_message("✅ Vencedor confirmado: " + (vn.mention if vn else vencedor_id), ephemeral=True)

            sel_venc.callback = sel_venc_cb
            view_v.add_item(sel_venc)
            await i.response.send_message("Quem venceu?", view=view_v, ephemeral=True)

        sel_partida.callback = sel_partida_cb
        view_p.add_item(sel_partida)
        await interaction.response.send_message("Selecione a partida:", view=view_p, ephemeral=True)

    @discord.ui.button(label="📊 Ver Bracket", style=discord.ButtonStyle.grey, custom_id="CAMP|bracket")
    async def ver_bracket(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp:
            await interaction.response.send_message("Campeonato não encontrado.", ephemeral=True)
            return
        embed_br = embed_bracket(camp, interaction.guild, camp.get("rodada_atual", 0))
        await interaction.response.send_message(embed=embed_br, ephemeral=True)


# ══════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════

class Campeonato(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if not cid.startswith("CAMP|"):
            return
        if interaction.response.is_done():
            return

        acao = cid.split("|")[1]
        data = db.load(interaction.guild.id)

        # Encontra o campeonato pelo canal
        camp_id = None
        for cid_k, camp in data.get("campeonatos", {}).items():
            if camp.get("canal_id") == interaction.channel.id or camp.get("canal_org_id") == interaction.channel.id:
                camp_id = cid_k
                break

        if not camp_id:
            await interaction.response.send_message("Campeonato não encontrado.", ephemeral=True)
            return

        camp = data["campeonatos"][camp_id]
        pix = camp.get("pix", "")

        if acao == "inscrever":
            view = ViewInscricao(camp_id, pix)
            await view.inscrever.callback(view, interaction, None)
        elif acao == "cancelar_inscricao":
            view = ViewInscricao(camp_id, pix)
            await view.cancelar.callback(view, interaction, None)
        elif acao == "ver_inscritos":
            view = ViewInscricao(camp_id, pix)
            await view.ver.callback(view, interaction, None)
        elif acao == "vencedor":
            view = ViewBracket(camp_id)
            await view.vencedor.callback(view, interaction, None)
        elif acao == "bracket":
            view = ViewBracket(camp_id)
            await view.ver_bracket.callback(view, interaction, None)

    @app_commands.command(name="campeonato-criar", description="[ADM] Cria um novo campeonato")
    async def criar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalCriarCampeonato())

    @app_commands.command(name="campeonato-admin", description="[ADM] Painel admin do campeonato")
    async def admin(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        camps = data.get("campeonatos", {})
        if not camps:
            await interaction.response.send_message("Nenhum campeonato criado.", ephemeral=True)
            return
        opcoes = [discord.SelectOption(label=c["nome"], description=c["status"], value=cid) for cid, c in camps.items()]
        sel = discord.ui.Select(placeholder="Selecione o campeonato", options=opcoes[:25])
        view = discord.ui.View(timeout=60)
        async def cb(i):
            camp_id = sel.values[0]
            camp = data["campeonatos"][camp_id]
            embed = embed_campeonato(camp, i.guild)
            await i.response.send_message(embed=embed, view=ViewAdminCampeonato(camp_id), ephemeral=True)
        sel.callback = cb
        view.add_item(sel)
        await interaction.response.send_message("Selecione o campeonato:", view=view, ephemeral=True)

    @app_commands.command(name="campeoes", description="Histórico de campeões")
    async def campeoes(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        historico = data.get("historico_campeoes", [])
        if not historico:
            await interaction.response.send_message("Nenhum campeão registrado ainda.", ephemeral=True)
            return
        embed = discord.Embed(title="🏆 Hall dos Campeões", color=discord.Color.gold())
        linhas = []
        for i, c in enumerate(reversed(historico[-20:])):
            m = interaction.guild.get_member(int(c["campeao_id"]))
            nome = m.mention if m else "ID:" + c["campeao_id"]
            data_str = c["data"][:10]
            premio = " — " + c["premio"] if c.get("premio") else ""
            linhas.append("🥇 **" + c["campeonato"] + "** → " + nome + " (" + data_str + ")" + premio)
        embed.description = "\n".join(linhas)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Campeonato(bot))
