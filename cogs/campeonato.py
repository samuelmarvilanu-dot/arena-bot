"""
cogs/campeonato.py — Sistema completo de campeonatos Arena X1
"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import math
import asyncio
from utils import database as db


# ══════════════════════════════════════════════════════════
#  QR CODE
# ══════════════════════════════════════════════════════════

def gerar_qrcode_pix(pix_key):
    try:
        import qrcode
        import io
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data(pix_key)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="qrcode.png")
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════

def gerar_bracket(jogadores):
    lista = list(jogadores)
    random.shuffle(lista)
    prox = 2 ** math.ceil(math.log2(max(len(lista), 2)))
    while len(lista) < prox:
        lista.append(None)
    partidas = []
    for i in range(0, len(lista), 2):
        partidas.append({"j1": lista[i], "j2": lista[i+1], "vencedor": None})
    return [partidas]


def embed_campeonato(camp, guild):
    status = camp.get("status", "aberto")
    cores = {
        "aberto": 0x00FF00,
        "em_andamento": 0x5865F2,
        "finalizado": 0xFFD700,
        "configurando": 0x888888,
    }
    embed = discord.Embed(
        title="🏆 " + camp["nome"],
        description=camp.get("descricao", ""),
        color=cores.get(status, 0x5865F2)
    )
    if camp.get("banner"):
        embed.set_image(url=camp["banner"])
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    fmt = {
        "mata-mata": "⚔️ Mata-mata",
        "grupos": "📊 Grupos + Mata-mata",
        "pontos": "📋 Pontos corridos"
    }
    embed.add_field(name="📋 Formato", value=fmt.get(camp.get("formato", "mata-mata"), "Mata-mata"), inline=True)

    confirmados = [uid for uid, info in camp.get("inscritos", {}).items() if info.get("confirmado")]
    embed.add_field(name="👥 Vagas", value=str(len(confirmados)) + "/" + str(camp.get("max_jogadores", 16)), inline=True)

    valor = camp.get("valor", 0)
    embed.add_field(name="💰 Inscrição", value="R$ " + str(round(valor, 2)) if valor > 0 else "Gratuito", inline=True)

    if camp.get("premio"):
        embed.add_field(name="🎁 Prêmio", value=camp["premio"], inline=True)

    embed.add_field(name="📅 Início", value=camp.get("data_inicio", "A definir"), inline=True)

    status_txt = {
        "aberto": "✅ Inscrições abertas",
        "em_andamento": "⚔️ Em andamento",
        "finalizado": "🏆 Finalizado",
        "configurando": "⚙️ Configurando"
    }.get(status, status)
    embed.add_field(name="Status", value=status_txt, inline=True)

    if confirmados:
        nomes = []
        for uid in confirmados[:10]:
            m = guild.get_member(int(uid))
            nomes.append("✅ " + (m.display_name if m else uid))
        if len(confirmados) > 10:
            nomes.append("... e mais " + str(len(confirmados) - 10))
        embed.add_field(name="Confirmados (" + str(len(confirmados)) + ")", value="\n".join(nomes), inline=False)

    espera = camp.get("lista_espera", [])
    if espera:
        embed.add_field(name="⏳ Lista de Espera (" + str(len(espera)) + ")", value="Aguardando vagas", inline=False)

    embed.set_footer(text="Arena X1 • " + datetime.now().strftime("%d/%m/%Y %H:%M"))
    return embed


def embed_bracket(camp, guild):
    embed = discord.Embed(title="⚔️ Chaves — " + camp["nome"], color=0x5865F2)
    rodadas = camp.get("rodadas", [])
    rodada_atual = camp.get("rodada_atual", 0)
    nomes_rodada = ["Oitavas de Final", "Quartas de Final", "Semifinal", "Final"]

    for i, rodada in enumerate(rodadas):
        nome_r = nomes_rodada[i] if i < len(nomes_rodada) else "Rodada " + str(i+1)
        atual = "▶️ " if i == rodada_atual else "✅ " if i < rodada_atual else ""
        linhas = []
        for j, p in enumerate(rodada):
            j1 = guild.get_member(int(p["j1"])) if p["j1"] else None
            j2 = guild.get_member(int(p["j2"])) if p["j2"] else None
            n1 = j1.display_name if j1 else ("BYE" if not p["j1"] else str(p["j1"]))
            n2 = j2.display_name if j2 else ("BYE" if not p["j2"] else str(p["j2"]))
            if p.get("vencedor"):
                v = guild.get_member(int(p["vencedor"]))
                vn = v.display_name if v else str(p["vencedor"])
                linhas.append("`" + str(j+1) + ".` ~~" + n1 + "~~ vs ~~" + n2 + "~~ → 🏆 **" + vn + "**")
            else:
                linhas.append("`" + str(j+1) + ".` **" + n1 + "** vs **" + n2 + "**")
        embed.add_field(name=atual + nome_r, value="\n".join(linhas) if linhas else "Aguardando...", inline=False)

    embed.set_footer(text="Arena X1 • Rodada: " + (nomes_rodada[rodada_atual] if rodada_atual < len(nomes_rodada) else "Rodada " + str(rodada_atual+1)))
    return embed


async def atualizar_embed_camp(guild, camp):
    canal_id = camp.get("canal_id")
    msg_id = camp.get("msg_id")
    if not canal_id or not msg_id:
        return
    canal = guild.get_channel(canal_id)
    if not canal:
        return
    try:
        msg = await canal.fetch_message(msg_id)
        pix = camp.get("pix", "")
        await msg.edit(embed=embed_campeonato(camp, guild), view=ViewInscricao(camp["id"], pix))
    except Exception:
        pass


async def limpar_e_iniciar_rodada(guild, camp, camp_id):
    """Apaga todas as msgs do canal org e posta nova rodada."""
    canal_org_id = camp.get("canal_org_id")
    if not canal_org_id:
        return
    canal = guild.get_channel(canal_org_id)
    if not canal:
        return

    # Apaga todas as mensagens
    try:
        await canal.purge(limit=200)
    except Exception:
        pass

    # Slow mode 30s para evitar spam
    try:
        await canal.edit(slowmode_delay=30)
    except Exception:
        pass

    rodada_idx = camp.get("rodada_atual", 0)
    rodada = camp["rodadas"][rodada_idx]
    nomes_rodada = ["Oitavas de Final", "Quartas de Final", "Semifinal", "Final"]
    nome_r = nomes_rodada[rodada_idx] if rodada_idx < len(nomes_rodada) else "Rodada " + str(rodada_idx+1)

    # Posta bracket atualizado
    embed_br = embed_bracket(camp, guild)
    await canal.send(embed=embed_br, view=ViewBracket(camp_id))

    # Menciona todos os jogadores da rodada
    mencoes = []
    for p in rodada:
        if p["j1"] and p["j2"]:
            j1 = guild.get_member(int(p["j1"]))
            j2 = guild.get_member(int(p["j2"]))
            n1 = j1.mention if j1 else str(p["j1"])
            n2 = j2.mention if j2 else str(p["j2"])
            mencoes.append("⚔️ " + n1 + " vs " + n2)
        elif p["j1"] and not p["j2"]:
            j1 = guild.get_member(int(p["j1"]))
            n1 = j1.mention if j1 else str(p["j1"])
            mencoes.append("🏆 " + n1 + " avança automaticamente (BYE)")

    if mencoes:
        await canal.send(
            "**" + nome_r + " — Joguem suas partidas e aguardem a confirmação do admin!**\n\n" +
            "\n".join(mencoes)
        )


async def chamar_lista_espera(guild, camp_id, data):
    camp = data["campeonatos"].get(camp_id)
    if not camp:
        return
    espera = camp.get("lista_espera", [])
    if not espera:
        return
    proximo_uid = espera.pop(0)
    camp["lista_espera"] = espera
    db.save(guild.id, data)
    membro = guild.get_member(int(proximo_uid))
    if not membro:
        return
    canal_camp = guild.get_channel(camp.get("canal_id"))
    if canal_camp:
        await canal_camp.send(
            membro.mention + " uma vaga abriu no campeonato **" + camp["nome"] + "**! Clique em **Me Inscrever** para garantir sua vaga!"
        )


async def dar_cargo_participante(guild, camp, uid):
    """Dá cargo temporário de participante."""
    cargo_id = camp.get("cargo_participante_id")
    if not cargo_id:
        return
    cargo = guild.get_role(cargo_id)
    membro = guild.get_member(int(uid))
    if cargo and membro:
        try:
            await membro.add_roles(cargo, reason="Participante do campeonato " + camp["nome"])
        except Exception:
            pass


async def remover_cargo_participante(guild, camp, uid):
    """Remove cargo de participante quando eliminado."""
    cargo_id = camp.get("cargo_participante_id")
    if not cargo_id:
        return
    cargo = guild.get_role(cargo_id)
    membro = guild.get_member(int(uid))
    if cargo and membro:
        try:
            await membro.remove_roles(cargo, reason="Eliminado do campeonato " + camp["nome"])
        except Exception:
            pass


# ══════════════════════════════════════════════════════════
#  MODAIS
# ══════════════════════════════════════════════════════════

class ModalCriarCampeonato(discord.ui.Modal, title="Criar Campeonato"):
    nome = discord.ui.TextInput(label="Nome do campeonato", placeholder="ex: Copa Arena X1", max_length=50)
    descricao = discord.ui.TextInput(label="Descrição", placeholder="ex: Campeonato mensal de EFootball!", max_length=200, style=discord.TextStyle.paragraph, required=False)
    premio = discord.ui.TextInput(label="Prêmio", placeholder="ex: R$ 35,00 para o 1º lugar", max_length=100, required=False)
    data_inicio = discord.ui.TextInput(label="Data de início (DD/MM/YYYY)", placeholder="ex: 20/07/2026", max_length=20, required=False)
    banner = discord.ui.TextInput(label="URL do banner (opcional)", placeholder="https://...", max_length=300, required=False)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        if "campeonatos" not in data:
            data["campeonatos"] = {}
        camp_id = str(int(datetime.now().timestamp()))
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
            "pix": data["config"].get("pix_cargos", ""),
            "prazo_horas": 24,
            "status": "configurando",
            "inscritos": {},
            "pendentes": {},
            "lista_espera": [],
            "rodadas": [],
            "rodada_atual": 0,
            "canal_id": None,
            "msg_id": None,
            "canal_org_id": None,
            "cargo_participante_id": None,
            "criado_em": datetime.now().isoformat(),
            "criado_por": interaction.user.id,
        }
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="✅ Campeonato criado!", color=0x00FF00)
        embed.description = "**" + self.nome.value + "** criado! Configure abaixo."
        await interaction.response.send_message(embed=embed, view=ViewConfigurarCampeonato(camp_id), ephemeral=True)


class ModalValorPix(discord.ui.Modal, title="Valor e PIX"):
    valor = discord.ui.TextInput(label="Valor (R$) — 0 para gratuito", placeholder="ex: 3.50", max_length=10)
    pix = discord.ui.TextInput(label="Chave PIX", placeholder="ex: email@gmail.com", max_length=100)
    prazo = discord.ui.TextInput(label="Prazo para pagar (horas)", placeholder="ex: 24", max_length=3, required=False)

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
        data["campeonatos"][self.camp_id]["pix"] = self.pix.value
        data["campeonatos"][self.camp_id]["prazo_horas"] = int(self.prazo.value or 24)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(
            "✅ R$ " + str(round(v, 2)) + " | PIX: `" + self.pix.value + "` | Prazo: " + str(self.prazo.value or 24) + "h",
            ephemeral=True
        )


# ══════════════════════════════════════════════════════════
#  VIEWS
# ══════════════════════════════════════════════════════════

class ViewConfigurarCampeonato(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=300)
        self.camp_id = camp_id

        sel_fmt = discord.ui.Select(placeholder="Formato do campeonato", options=[
            discord.SelectOption(label="Mata-mata", value="mata-mata", emoji="⚔️"),
            discord.SelectOption(label="Grupos + Mata-mata", value="grupos", emoji="📊"),
            discord.SelectOption(label="Pontos corridos", value="pontos", emoji="📋"),
        ], row=0)
        sel_fmt.callback = self._formato
        self.add_item(sel_fmt)

        sel_jog = discord.ui.Select(placeholder="Número de participantes", options=[
            discord.SelectOption(label="4 jogadores", value="4"),
            discord.SelectOption(label="8 jogadores", value="8"),
            discord.SelectOption(label="16 jogadores", value="16"),
            discord.SelectOption(label="32 jogadores", value="32"),
            discord.SelectOption(label="64 jogadores", value="64"),
        ], row=1)
        sel_jog.callback = self._max_jogadores
        self.add_item(sel_jog)

        sel_cargo = discord.ui.RoleSelect(placeholder="Cargo dos participantes (opcional)", row=2)
        sel_cargo.callback = self._cargo
        self.add_item(sel_cargo)

    async def _formato(self, interaction):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["formato"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Formato: " + interaction.data["values"][0], ephemeral=True)

    async def _max_jogadores(self, interaction):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["max_jogadores"] = int(interaction.data["values"][0])
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ " + interaction.data["values"][0] + " participantes!", ephemeral=True)

    async def _cargo(self, interaction):
        v = interaction.data["values"][0]
        cargo_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["cargo_participante_id"] = cargo_id
        db.save(interaction.guild.id, data)
        cargo = interaction.guild.get_role(cargo_id)
        await interaction.response.send_message("✅ Cargo: " + (cargo.mention if cargo else str(cargo_id)), ephemeral=True)

    @discord.ui.button(label="💰 Valor e PIX", style=discord.ButtonStyle.blurple, row=3)
    async def valor(self, interaction, button):
        await interaction.response.send_modal(ModalValorPix(self.camp_id))

    @discord.ui.button(label="📢 Postar no Canal", style=discord.ButtonStyle.green, row=3)
    async def postar(self, interaction, button):
        await interaction.response.edit_message(
            embed=discord.Embed(title="Selecione o canal", color=0x5865F2),
            view=ViewSelecionarCanalCamp(self.camp_id)
        )

    @discord.ui.button(label="🗑️ Cancelar", style=discord.ButtonStyle.red, row=3)
    async def cancelar(self, interaction, button):
        data = db.load(interaction.guild.id)
        del data["campeonatos"][self.camp_id]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(content="❌ Cancelado.", embed=None, view=None)


class ViewSelecionarCanalCamp(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=120)
        self.camp_id = camp_id
        sel = discord.ui.ChannelSelect(
            placeholder="Canal onde o campeonato será postado",
            channel_types=[discord.ChannelType.text],
            row=0
        )
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
        db.save(interaction.guild.id, data)

        pix = camp.get("pix", "")
        embed = embed_campeonato(camp, interaction.guild)
        view = ViewInscricao(self.camp_id, pix)
        msg = await canal.send(
            "@everyone 🏆 **Novo campeonato disponível!** Inscreva-se em **" + camp["nome"] + "**!",
            embed=embed,
            view=view
        )
        camp["msg_id"] = msg.id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(
            content="✅ Postado em " + canal.mention + "!",
            embed=None, view=None
        )


class ViewInscricao(discord.ui.View):
    def __init__(self, camp_id, pix=""):
        super().__init__(timeout=None)
        self.camp_id = camp_id
        self.pix = pix

    @discord.ui.button(label="✅ Me Inscrever", style=discord.ButtonStyle.green, custom_id="CAMP|inscrever")
    async def inscrever(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp or camp["status"] != "aberto":
            await interaction.response.send_message("❌ Inscrições encerradas!", ephemeral=True)
            return

        uid = str(interaction.user.id)

        if uid in camp.get("inscritos", {}) and camp["inscritos"][uid].get("confirmado"):
            await interaction.response.send_message("✅ Você já está confirmado!", ephemeral=True)
            return
        if uid in camp.get("pendentes", {}):
            pend = camp["pendentes"][uid]
            canal_pag = interaction.guild.get_channel(pend.get("canal_id"))
            await interaction.response.send_message(
                "⏳ Seu pagamento está sendo analisado! " + (canal_pag.mention if canal_pag else ""),
                ephemeral=True
            )
            return
        if uid in camp.get("lista_espera", []):
            pos = camp["lista_espera"].index(uid) + 1
            await interaction.response.send_message("⏳ Você está na lista de espera, posição **" + str(pos) + "**!", ephemeral=True)
            return

        confirmados = [u for u, i in camp.get("inscritos", {}).items() if i.get("confirmado")]
        if len(confirmados) >= camp["max_jogadores"]:
            camp.setdefault("lista_espera", []).append(uid)
            db.save(interaction.guild.id, data)
            pos = camp["lista_espera"].index(uid) + 1
            await interaction.response.send_message(
                "⏳ Campeonato lotado! Você está na **lista de espera** na posição **" + str(pos) + "**.\nSe uma vaga abrir, você será notificado!",
                ephemeral=True
            )
            return

        if camp.get("valor", 0) == 0:
            camp.setdefault("inscritos", {})[uid] = {"confirmado": True, "inscrito_em": datetime.now().isoformat()}
            db.save(interaction.guild.id, data)
            await dar_cargo_participante(interaction.guild, camp, uid)
            await interaction.response.send_message("✅ Inscrição confirmada gratuitamente!", ephemeral=True)
            await atualizar_embed_camp(interaction.guild, camp)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            # Cria thread privada dentro do canal do campeonato
            canal_camp = interaction.guild.get_channel(camp.get("canal_id"))
            if not canal_camp:
                await interaction.followup.send("❌ Canal do campeonato não encontrado.", ephemeral=True)
                return

            nome_thread = "pag-" + interaction.user.display_name[:20]
            thread = await canal_camp.create_thread(
                name=nome_thread,
                type=discord.ChannelType.private_thread,
                invitable=False
            )
            # Adiciona o jogador e admins na thread
            await thread.add_user(interaction.user)
            cargo_adm_id = data["config"].get("cargo_mediador")
            if cargo_adm_id:
                cargo_adm = interaction.guild.get_role(cargo_adm_id)
                if cargo_adm:
                    for m in interaction.guild.members:
                        if cargo_adm in m.roles and not m.bot:
                            try:
                                await thread.add_user(m)
                            except Exception:
                                pass

            camp.setdefault("pendentes", {})[uid] = {
                "canal_id": thread.id,
                "thread": True,
                "iniciado_em": datetime.now().isoformat(),
                "prazo": (datetime.now() + timedelta(hours=camp.get("prazo_horas", 24))).isoformat()
            }
            db.save(interaction.guild.id, data)

            embed = discord.Embed(
                title="💳 Pagamento — " + camp["nome"],
                description="Olá " + interaction.user.mention + "! Para confirmar sua vaga, realize o pagamento abaixo.",
                color=0x5865F2
            )
            embed.add_field(name="🏆 Campeonato", value=camp["nome"], inline=True)
            embed.add_field(name="💰 Valor", value="R$ " + str(round(camp["valor"], 2)), inline=True)
            embed.add_field(name="⏰ Prazo", value=str(camp.get("prazo_horas", 24)) + " horas", inline=True)
            embed.add_field(name="🔑 Chave PIX", value="```" + camp.get("pix", "Não configurado") + "```", inline=False)
            embed.add_field(
                name="📋 Como pagar",
                value="1️⃣ Copie a chave PIX acima\n2️⃣ Faça o pagamento no seu banco\n3️⃣ Envie o **comprovante** aqui\n4️⃣ Aguarde a confirmação do admin",
                inline=False
            )
            embed.set_footer(text="Após o prazo, sua inscrição será cancelada automaticamente.")
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)

            qr_file = gerar_qrcode_pix(camp.get("pix", ""))
            view_pag = ViewPagamento(self.camp_id, uid, thread.id)

            if qr_file:
                await thread.send(embed=embed, file=qr_file, view=view_pag)
            else:
                await thread.send(embed=embed, view=view_pag)

            await interaction.followup.send(
                "✅ Tópico criado! Acesse " + thread.mention + " para pagar.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send("❌ Erro: " + str(e), ephemeral=True)

    @discord.ui.button(label="❌ Cancelar Inscrição", style=discord.ButtonStyle.red, custom_id="CAMP|cancelar_inscricao")
    async def cancelar(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        uid = str(interaction.user.id)
        removido = False

        if uid in camp.get("inscritos", {}) and camp["inscritos"][uid].get("confirmado"):
            del camp["inscritos"][uid]
            removido = True
            await remover_cargo_participante(interaction.guild, camp, uid)
            await chamar_lista_espera(interaction.guild, self.camp_id, data)
        elif uid in camp.get("pendentes", {}):
            info = camp["pendentes"][uid]
            canal_pag = interaction.guild.get_channel(info["canal_id"])
            if canal_pag:
                try:
                    await canal_pag.delete()
                except Exception:
                    pass
            else:
                thread_pag = interaction.guild.get_thread(info["canal_id"])
                if thread_pag:
                    try:
                        await thread_pag.delete()
                    except Exception:
                        pass
            del camp["pendentes"][uid]
            removido = True
        elif uid in camp.get("lista_espera", []):
            camp["lista_espera"].remove(uid)
            removido = True

        if removido:
            db.save(interaction.guild.id, data)
            await interaction.response.send_message("✅ Inscrição cancelada.", ephemeral=True)
            await atualizar_embed_camp(interaction.guild, camp)
        else:
            await interaction.response.send_message("❌ Você não está inscrito.", ephemeral=True)

    @discord.ui.button(label="📋 Ver Inscritos", style=discord.ButtonStyle.grey, custom_id="CAMP|ver_inscritos")
    async def ver(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        confirmados = {uid: info for uid, info in camp.get("inscritos", {}).items() if info.get("confirmado")}
        pendentes = camp.get("pendentes", {})
        espera = camp.get("lista_espera", [])

        embed = discord.Embed(title="📋 " + camp["nome"], color=0x5865F2)
        if confirmados:
            linhas = []
            for uid in confirmados:
                m = interaction.guild.get_member(int(uid))
                linhas.append("✅ " + (m.display_name if m else uid))
            embed.add_field(name="Confirmados (" + str(len(confirmados)) + ")", value="\n".join(linhas), inline=False)
        if pendentes:
            linhas = []
            for uid in pendentes:
                m = interaction.guild.get_member(int(uid))
                linhas.append("⏳ " + (m.display_name if m else uid))
            embed.add_field(name="Aguardando pagamento (" + str(len(pendentes)) + ")", value="\n".join(linhas), inline=False)
        if espera:
            linhas = [str(i+1) + ". " + ((interaction.guild.get_member(int(uid)).display_name if interaction.guild.get_member(int(uid)) else uid)) for i, uid in enumerate(espera)]
            embed.add_field(name="Lista de espera (" + str(len(espera)) + ")", value="\n".join(linhas), inline=False)
        if not confirmados and not pendentes and not espera:
            embed.description = "Nenhum inscrito ainda."
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ViewPagamento(discord.ui.View):
    def __init__(self, camp_id, uid, canal_id):
        super().__init__(timeout=None)
        self.camp_id = camp_id
        self.uid = uid
        self.canal_id = canal_id

    async def _check_admin(self, interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        data = db.load(interaction.guild.id)
        cargo_adm_id = data["config"].get("cargo_mediador")
        if cargo_adm_id:
            cargo = interaction.guild.get_role(cargo_adm_id)
            if cargo and cargo in interaction.user.roles:
                return True
        return False

    @discord.ui.button(label="✅ Confirmar Pagamento", style=discord.ButtonStyle.green, custom_id="CAMP|confirmar_pag")
    async def confirmar(self, interaction, button):
        if not await self._check_admin(interaction):
            await interaction.response.send_message("❌ Apenas admins podem confirmar.", ephemeral=True)
            return

        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp or self.uid not in camp.get("pendentes", {}):
            await interaction.response.send_message("❌ Jogador não está pendente.", ephemeral=True)
            return

        del camp["pendentes"][self.uid]
        camp.setdefault("inscritos", {})[self.uid] = {
            "confirmado": True,
            "inscrito_em": datetime.now().isoformat(),
            "confirmado_por": interaction.user.id,
        }
        db.save(interaction.guild.id, data)

        membro = interaction.guild.get_member(int(self.uid))
        await dar_cargo_participante(interaction.guild, camp, self.uid)

        embed = discord.Embed(
            title="✅ Pagamento Confirmado!",
            description=(membro.mention if membro else self.uid) + ", sua vaga no **" + camp["nome"] + "** está garantida! Boa sorte! 🏆",
            color=0x00FF00
        )
        await interaction.response.send_message(embed=embed)
        await atualizar_embed_camp(interaction.guild, camp)

        # Verifica se lotou
        confirmados = [u for u, i in camp["inscritos"].items() if i.get("confirmado")]
        if len(confirmados) >= camp["max_jogadores"]:
            canal_camp = interaction.guild.get_channel(camp.get("canal_id"))
            if canal_camp:
                await canal_camp.send("🏆 **Vagas esgotadas!** O admin pode iniciar o campeonato agora!")

        await asyncio.sleep(30)
        try:
            # Tenta deletar thread ou canal
            obj = interaction.guild.get_channel(self.canal_id)
            if not obj:
                obj = interaction.guild.get_thread(self.canal_id)
            if obj:
                await obj.delete()
        except Exception:
            pass

    @discord.ui.button(label="❌ Rejeitar Comprovante", style=discord.ButtonStyle.red, custom_id="CAMP|rejeitar_pag")
    async def rejeitar(self, interaction, button):
        if not await self._check_admin(interaction):
            await interaction.response.send_message("❌ Apenas admins podem rejeitar.", ephemeral=True)
            return
        membro = interaction.guild.get_member(int(self.uid))
        embed = discord.Embed(
            title="❌ Comprovante Rejeitado",
            description=(membro.mention if membro else self.uid) + ", seu comprovante foi rejeitado.\nEnvie um novo comprovante válido ou cancele sua inscrição.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)


class ViewBracket(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=None)
        self.camp_id = camp_id

    @discord.ui.button(label="🏆 Confirmar Vencedor", style=discord.ButtonStyle.green, custom_id="CAMP|vencedor")
    async def vencedor(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            data = db.load(interaction.guild.id)
            cargo_adm_id = data["config"].get("cargo_mediador")
            if cargo_adm_id:
                cargo = interaction.guild.get_role(cargo_adm_id)
                if not cargo or cargo not in interaction.user.roles:
                    await interaction.response.send_message("❌ Apenas admins podem confirmar.", ephemeral=True)
                    return

        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp or camp["status"] != "em_andamento":
            await interaction.response.send_message("❌ Campeonato não está em andamento.", ephemeral=True)
            return

        rodada_idx = camp.get("rodada_atual", 0)
        rodada = camp["rodadas"][rodada_idx]
        pendentes = [(i, p) for i, p in enumerate(rodada) if not p.get("vencedor") and p["j1"] and p["j2"]]

        if not pendentes:
            await interaction.response.send_message("✅ Todos os vencedores já foram confirmados!", ephemeral=True)
            return

        opcoes = []
        for i, p in pendentes[:25]:
            j1 = interaction.guild.get_member(int(p["j1"]))
            j2 = interaction.guild.get_member(int(p["j2"]))
            n1 = j1.display_name if j1 else str(p["j1"])
            n2 = j2.display_name if j2 else str(p["j2"])
            opcoes.append(discord.SelectOption(label=n1 + " vs " + n2, value=str(i)))

        sel_partida = discord.ui.Select(placeholder="Selecione a partida", options=opcoes)
        view_p = discord.ui.View(timeout=60)

        async def sel_partida_cb(i):
            idx_p = int(sel_partida.values[0])
            partida = rodada[idx_p]
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
                perdedor_id = str(partida["j2"]) if vencedor_id == str(partida["j1"]) else str(partida["j1"])

                data2 = db.load(i2.guild.id)
                camp2 = data2["campeonatos"][self.camp_id]
                camp2["rodadas"][rodada_idx][idx_p]["vencedor"] = vencedor_id
                db.save(i2.guild.id, data2)

                # Remove cargo do perdedor
                await remover_cargo_participante(i2.guild, camp2, perdedor_id)

                rodada2 = camp2["rodadas"][rodada_idx]
                todos_prontos = all(p.get("vencedor") or not p["j2"] for p in rodada2)
                vn = i2.guild.get_member(int(vencedor_id))
                vn_nome = vn.mention if vn else vencedor_id

                if todos_prontos:
                    vencedores = [p["vencedor"] or p["j1"] for p in rodada2]

                    if len(vencedores) == 1:
                        # CAMPEÃO!
                        camp2["status"] = "finalizado"
                        camp2["campeao"] = vencedores[0]
                        data2.setdefault("historico_campeoes", []).append({
                            "campeonato": camp2["nome"],
                            "campeao_id": vencedores[0],
                            "data": datetime.now().isoformat(),
                            "premio": camp2.get("premio", ""),
                        })
                        db.save(i2.guild.id, data2)

                        m = i2.guild.get_member(int(vencedores[0]))
                        embed_fim = discord.Embed(
                            title="🏆 CAMPEÃO!",
                            description=(m.mention if m else vencedores[0]) + " é o grande campeão de **" + camp2["nome"] + "**! 🎉🎉🎉",
                            color=0xFFD700
                        )
                        if camp2.get("premio"):
                            embed_fim.add_field(name="🎁 Prêmio", value=camp2["premio"])
                        embed_fim.set_footer(text="Arena X1 • " + datetime.now().strftime("%d/%m/%Y"))
                        if i2.guild.icon:
                            embed_fim.set_thumbnail(url=i2.guild.icon.url)

                        canal_org = i2.guild.get_channel(camp2.get("canal_org_id"))
                        if canal_org:
                            try:
                                await canal_org.purge(limit=200)
                            except Exception:
                                pass
                            await canal_org.send("@everyone", embed=embed_fim)

                        await atualizar_embed_camp(i2.guild, camp2)
                        await i2.response.send_message("🏆 " + vn_nome + " é o campeão!", ephemeral=True)

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

                        # Limpa canal e inicia nova rodada
                        await limpar_e_iniciar_rodada(i2.guild, camp2, self.camp_id)
                        await i2.response.send_message("✅ Rodada avançada! " + vn_nome + " venceu.", ephemeral=True)
                else:
                    # Apenas atualiza o bracket
                    embed_br = embed_bracket(camp2, i2.guild)
                    canal_org = i2.guild.get_channel(camp2.get("canal_org_id"))
                    if canal_org:
                        async for msg in canal_org.history(limit=5):
                            if msg.author == i2.guild.me and msg.embeds:
                                await msg.edit(embed=embed_br)
                                break
                    await i2.response.send_message("✅ " + vn_nome + " venceu a partida!", ephemeral=True)

            sel_venc.callback = sel_venc_cb
            view_v.add_item(sel_venc)
            await i.response.send_message("Quem venceu?", view=view_v, ephemeral=True)

        sel_partida.callback = sel_partida_cb
        view_p.add_item(sel_partida)
        await interaction.response.send_message("Selecione a partida:", view=view_p, ephemeral=True)

    @discord.ui.button(label="📊 Ver Bracket Completo", style=discord.ButtonStyle.grey, custom_id="CAMP|ver_bracket")
    async def ver_bracket(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        if not camp:
            await interaction.response.send_message("❌ Campeonato não encontrado.", ephemeral=True)
            return
        embed_br = embed_bracket(camp, interaction.guild)
        await interaction.response.send_message(embed=embed_br, ephemeral=True)


class ViewPainelCampeonato(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🏆 Criar Campeonato", style=discord.ButtonStyle.green, custom_id="CAMP|criar")
    async def criar(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            data = db.load(interaction.guild.id)
            cargo_adm_id = data["config"].get("cargo_mediador")
            if cargo_adm_id:
                cargo = interaction.guild.get_role(cargo_adm_id)
                if not cargo or cargo not in interaction.user.roles:
                    await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
                    return
        await interaction.response.send_modal(ModalCriarCampeonato())

    @discord.ui.button(label="⚙️ Gerenciar Campeonato", style=discord.ButtonStyle.blurple, custom_id="CAMP|gerenciar")
    async def gerenciar(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return
        data = db.load(interaction.guild.id)
        camps = {cid: c for cid, c in data.get("campeonatos", {}).items() if c["status"] != "finalizado"}
        if not camps:
            await interaction.response.send_message("Nenhum campeonato ativo.", ephemeral=True)
            return
        opcoes = [discord.SelectOption(label=c["nome"], description=c["status"], value=cid) for cid, c in list(camps.items())[:25]]
        sel = discord.ui.Select(placeholder="Selecione o campeonato", options=opcoes)
        view = discord.ui.View(timeout=60)
        async def cb(i):
            camp_id = sel.values[0]
            camp = data["campeonatos"][camp_id]
            await i.response.send_message(embed=embed_campeonato(camp, i.guild), view=ViewAdminCampeonato(camp_id), ephemeral=True)
        sel.callback = cb
        view.add_item(sel)
        await interaction.response.send_message("Selecione:", view=view, ephemeral=True)


class ViewAdminCampeonato(discord.ui.View):
    def __init__(self, camp_id):
        super().__init__(timeout=300)
        self.camp_id = camp_id

    @discord.ui.button(label="⚔️ Iniciar Campeonato", style=discord.ButtonStyle.green, row=0)
    async def iniciar(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        confirmados = [uid for uid, info in camp.get("inscritos", {}).items() if info.get("confirmado")]

        if len(confirmados) < 2:
            await interaction.response.send_message("❌ Mínimo 2 jogadores confirmados!", ephemeral=True)
            return

        rodadas = gerar_bracket(confirmados)
        camp["rodadas"] = rodadas
        camp["rodada_atual"] = 0
        camp["status"] = "em_andamento"

        try:
            # Cria canal org com permissões corretas
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False),
            }
            # Participantes podem escrever
            cargo_part_id = camp.get("cargo_participante_id")
            if cargo_part_id:
                cargo_part = interaction.guild.get_role(cargo_part_id)
                if cargo_part:
                    overwrites[cargo_part] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            # Admin pode tudo
            overwrites[interaction.guild.me] = discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_messages=True)

            cat = None
            canal_camp = interaction.guild.get_channel(camp.get("canal_id"))
            if canal_camp and canal_camp.category:
                cat = canal_camp.category

            canal_org = await interaction.guild.create_text_channel(
                "bracket-" + camp["nome"].lower().replace(" ", "-")[:20],
                overwrites=overwrites,
                category=cat,
                slowmode_delay=30
            )
            camp["canal_org_id"] = canal_org.id
            db.save(interaction.guild.id, data)

            await limpar_e_iniciar_rodada(interaction.guild, camp, self.camp_id)
            await interaction.response.send_message("⚔️ Campeonato iniciado! " + canal_org.mention, ephemeral=True)
            await atualizar_embed_camp(interaction.guild, camp)

        except Exception as e:
            await interaction.response.send_message("❌ Erro: " + str(e), ephemeral=True)

    @discord.ui.button(label="🔒 Fechar Inscrições", style=discord.ButtonStyle.blurple, row=0)
    async def fechar(self, interaction, button):
        data = db.load(interaction.guild.id)
        camp = data["campeonatos"].get(self.camp_id)
        camp["status"] = "fechado"
        db.save(interaction.guild.id, data)
        await atualizar_embed_camp(interaction.guild, camp)
        await interaction.response.send_message("🔒 Inscrições fechadas!", ephemeral=True)

    @discord.ui.button(label="🏁 Encerrar", style=discord.ButtonStyle.red, row=0)
    async def encerrar(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["campeonatos"][self.camp_id]["status"] = "finalizado"
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Encerrado.", ephemeral=True)


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

        if acao == "criar":
            view = ViewPainelCampeonato()
            await view.criar.callback(view, interaction, None)
            return
        elif acao == "gerenciar":
            view = ViewPainelCampeonato()
            await view.gerenciar.callback(view, interaction, None)
            return

        # Canal de pagamento privado
        if acao in ("confirmar_pag", "rejeitar_pag"):
            canal_id = interaction.channel.id
            found = False
            for camp_id, camp in data.get("campeonatos", {}).items():
                for uid, pend in camp.get("pendentes", {}).items():
                    if pend.get("canal_id") == canal_id:
                        view = ViewPagamento(camp_id, uid, canal_id)
                        if acao == "confirmar_pag":
                            await view.confirmar.callback(view, interaction, view.confirmar)
                        else:
                            await view.rejeitar.callback(view, interaction, view.rejeitar)
                        found = True
                        return
            if not found:
                await interaction.response.send_message(
                    "Pendente nao encontrado para este topico. ID: " + str(canal_id),
                    ephemeral=True
                )
            return

        # Encontra campeonato pelo canal
        camp_id = None
        for cid_k, camp in data.get("campeonatos", {}).items():
            if (camp.get("canal_id") == interaction.channel.id or
                    camp.get("canal_org_id") == interaction.channel.id):
                camp_id = cid_k
                break

        if not camp_id:
            await interaction.response.send_message("❌ Campeonato não encontrado.", ephemeral=True)
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
        elif acao == "ver_bracket":
            view = ViewBracket(camp_id)
            await view.ver_bracket.callback(view, interaction, None)

    @app_commands.command(name="campeonato-painel", description="[ADM] Posta painel de campeonatos no canal")
    async def painel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏆 Central de Campeonatos",
            description="Inscreva-se nos campeonatos disponíveis ou acompanhe os em andamento!\n\nAdmins: clique em **Criar Campeonato** para começar.",
            color=0x5865F2
        )
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        embed.set_footer(text="Arena X1")
        await interaction.channel.send(embed=embed, view=ViewPainelCampeonato())
        await interaction.response.send_message("✅ Painel postado!", ephemeral=True)

    @app_commands.command(name="campeonato-criar", description="[ADM] Cria um novo campeonato")
    async def criar(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalCriarCampeonato())

    @app_commands.command(name="campeonato-admin", description="[ADM] Gerencia campeonatos ativos")
    async def admin(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        camps = {cid: c for cid, c in data.get("campeonatos", {}).items() if c["status"] != "finalizado"}
        if not camps:
            await interaction.response.send_message("Nenhum campeonato ativo.", ephemeral=True)
            return
        opcoes = [discord.SelectOption(label=c["nome"], description=c["status"], value=cid) for cid, c in list(camps.items())[:25]]
        sel = discord.ui.Select(placeholder="Selecione", options=opcoes)
        view = discord.ui.View(timeout=60)
        async def cb(i):
            camp_id = sel.values[0]
            camp = data["campeonatos"][camp_id]
            await i.response.send_message(embed=embed_campeonato(camp, i.guild), view=ViewAdminCampeonato(camp_id), ephemeral=True)
        sel.callback = cb
        view.add_item(sel)
        await interaction.response.send_message("Selecione:", view=view, ephemeral=True)

    @app_commands.command(name="campeoes", description="Histórico de campeões")
    async def campeoes(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        historico = data.get("historico_campeoes", [])
        if not historico:
            await interaction.response.send_message("Nenhum campeão ainda.", ephemeral=True)
            return
        embed = discord.Embed(title="🏆 Hall dos Campeões", color=0xFFD700)
        linhas = []
        for c in reversed(historico[-20:]):
            m = interaction.guild.get_member(int(c["campeao_id"]))
            nome = m.mention if m else "ID:" + c["campeao_id"]
            premio = " — " + c["premio"] if c.get("premio") else ""
            linhas.append("🥇 **" + c["campeonato"] + "** → " + nome + " (" + c["data"][:10] + ")" + premio)
        embed.description = "\n".join(linhas)
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Campeonato(bot))
