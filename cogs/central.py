"""
cogs/central.py — Central de Controle completa do Arena System
Versão definitiva — embed que se atualiza, select menus flutuantes, hierarquia completa
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils import database as db
from datetime import datetime


# ══════════════════════════════════════════════════════════
#  HELPERS — EMBEDS
# ══════════════════════════════════════════════════════════

def embed_central(guild):
    embed = discord.Embed(title="🎛️ Central de Controle do Bot", color=0x5865F2)
    embed.description = "Configure tudo do seu bot aqui!\nSelecione, abaixo, qual central deseja acessar."
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.set_footer(text="Apenas administradores têm acesso.")
    return embed


def embed_centrais_gerais():
    embed = discord.Embed(title="⚙️ Centrais Gerais do Bot", color=0x5865F2)
    itens = [
        ("🎮", "Jogos", "Configure taxa, modalidades, etc."),
        ("📋", "Filas", "Configure tipo de criação para tópico ou categoria."),
        ("💰", "Valores das Filas", "Configure os valores das filas."),
        ("🛡️", "Mediador", "Configure o pix, cargo, fila e modo de distribuição."),
        ("🎉", "Eventos", "Configure eventos de vitórias."),
        ("🎙️", "Streamers", "Configure fila de influencer."),
        ("📦", "Item", "Configure os itens das lojas ou caixas."),
        ("🛒", "Loja", "Configure as Lojas e seus painéis."),
        ("🎁", "Caixas Misteriosas", "Configure o sistema de caixas."),
        ("🎰", "Roleta", "Configure o sistema de roleta."),
        ("🎟️", "Codiguin", "Configure os Codiguins com itens para serem resgatados."),
        ("🪙", "Moeda/Coin", "Configure e reset a Moeda/Coin do bot."),
        ("🏆", "Perfil e Ranking", "Adicione o painel para consultar o perfil ou ranking."),
        ("📊", "Destaque Ranking Automático", "Configure o destaque automático de ranking."),
        ("ℹ️", "Comandos Prefixo", "Configure o prefixo do bot e/ou canais permitidos."),
        ("🔊", "SS/Analista", "Configure o sistema de chamar SS/Analista. (B.O. Análise)"),
        ("🚫", "BlackList", "Configure os cargos e o painel de consulta."),
        ("🔑", "Permissões", "Configure quais cargos têm acesso."),
        ("📝", "Logs", "Configure os canais de logs."),
        ("⚙️", "Bot", "Configure o Bot."),
    ]
    for emoji, nome, desc in itens:
        embed.add_field(name=f"{emoji}  {nome}", value=desc, inline=False)
    return embed


def embed_personalizacoes():
    embed = discord.Embed(title="🎨 Central de Personalizações", color=0x5865F2)
    itens = [
        ("🟢", "Componentes", "Configure/personalize os botões e selects do bot."),
        ("<>", "Embeds Padrão", "Altere embeds fixas do bot, ex: fila, confirmar partida..."),
        ("<>", "Embeds Auxiliares", "Configure embeds extras do bot."),
        ("<>", "Mensagens Auxiliares", "Altere mensagens enviadas, ex: @jogador confirmou partida..."),
        ("<>", "Nome dos Canais das Partidas", "Altere os nomes dos canais criados."),
        ("📱", "QrCode [Mediadores]", "Personalize o QrCode de pagamento dos mediadores."),
        ("<>", "Textos Auxiliares", "Altere alguns textos fixos, ex: nenhum jogador na fila..."),
    ]
    for emoji, nome, desc in itens:
        embed.add_field(name=f"{emoji}  {nome}", value=desc, inline=False)
    return embed


def embed_jogos(data):
    config = data["config"]
    filas = data.get("filas", {})
    embed = discord.Embed(title="🎮 Jogos Geral", color=0x5865F2)
    embed.description = (
        "Nesta seção, você pode configurar taxa de mediação, quantidade de filas e partidas, delay e adicionar jogos.\n"
        "↳ Para configurar as modalidades, coins, filas, etc. Clique no jogo desejado."
    )
    embed.add_field(name="Quantidade de FILAS o jogador pode aguardar", value=f"`{config.get('max_filas_jogador', 1)}`", inline=False)
    embed.add_field(name="Quantidade de PARTIDAS o jogador pode jogar", value=f"`{config.get('max_partidas_jogador', 1)}`", inline=False)
    embed.add_field(name="Delay Entre Uma Aposta Para Outra", value=f"`{config.get('delay_apostas', 0)}s`", inline=False)
    jogos_txt = "\n".join([
        f"{j['nome']} | {' | '.join(j.get('modalidades', {}).keys())}"
        for j in filas.values()
    ]) or "Nenhum jogo configurado."
    embed.add_field(name="Jogo | Modalidade:", value=jogos_txt, inline=False)
    return embed


def embed_filas(data):
    tipo = data["config"].get("tipo_criacao_fila", "categoria")
    embed = discord.Embed(title="📋 Central de Filas", color=0x5865F2)
    embed.description = "Configure o comportamento das filas aqui!"
    embed.add_field(name="Tipo de Criação das Partidas", value=f"`{tipo.upper()}`", inline=False)
    embed.add_field(name="↳ Tópico", value="As partidas serão criadas em formato de tópico no canal configurado.", inline=False)
    embed.add_field(name="↳ Categoria", value="As partidas serão criadas em formato de canal de texto em uma categoria.", inline=False)
    embed.add_field(name="↳ Mista", value="Combina tópico e categoria conforme necessário.", inline=False)
    return embed


def embed_valores(data):
    filas = data.get("filas", {})
    embed = discord.Embed(title="💰 Valores Geral", color=0x5865F2)
    embed.description = "Configure tudo relacionado a valores das filas aqui!"
    todos = []
    for jogo in filas.values():
        for mod in jogo.get("modalidades", {}).values():
            for v_str, v_data in mod.get("valores", {}).items():
                tipo = v_data.get("tipo_taxa", "pct")
                taxa = f"R$ {v_data.get('taxa_fixo', 0):.2f}" if tipo == "fixo" else f"{v_data.get('taxa_pct', 10)}%"
                todos.append((float(v_str), taxa))
    todos.sort(reverse=True)
    if todos:
        embed.add_field(
            name="Lista de Valores",
            value="\n".join([f"R$ {v:.2f} — taxa: {t}" for v, t in todos[:20]]),
            inline=False
        )
    else:
        embed.add_field(name="Lista de Valores", value="Nenhum valor configurado.", inline=False)
    return embed


def embed_mediadores(data, guild):
    config = data["config"]
    canal_id = config.get("canal_fila_mediador")
    canal = guild.get_channel(canal_id) if canal_id else None
    cargo_id = config.get("cargo_mediador")
    cargo = guild.get_role(cargo_id) if cargo_id else None
    embed = discord.Embed(title="🛡️ Mediadores Geral", color=0x5865F2)
    embed.description = "Configure tudo relacionado aos Mediadores aqui!"
    embed.add_field(name="Mediador pode registrar PIX sozinho?", value="🔴 NÃO" if not config.get("mediador_pix_proprio") else "🟢 SIM", inline=True)
    embed.add_field(name="Mediador pode visualizar sua receita?", value="🔴 NÃO" if not config.get("mediador_ver_receita") else "🟢 SIM", inline=True)
    embed.add_field(
        name="Quantidade de Partidas Simultâneas",
        value=f"Quantidade Atual: **{config.get('max_partidas_mediador', 20)}**\n↳ Quantas filas cada mediador pode pegar simultaneamente",
        inline=False
    )
    embed.add_field(name="Painel Fila Mediadores", value=canal.mention if canal else "#fila-mediador (não configurado)", inline=False)
    embed.add_field(name="Cargo Mediador Geral", value=cargo.mention if cargo else "Não configurado", inline=False)
    embed.add_field(name="Tipo de DISTRIBUIÇÃO", value=config.get("distribuicao_mediador", "Equilibrado").title(), inline=False)
    return embed


# ══════════════════════════════════════════════════════════
#  MODAIS
# ══════════════════════════════════════════════════════════

class ModalJogosGeral(discord.ui.Modal, title="Configurar Jogos Geral"):
    qtd_filas = discord.ui.TextInput(label="Qtd. FILAS por jogador", default="1", max_length=2)
    qtd_partidas = discord.ui.TextInput(label="Qtd. PARTIDAS por jogador", default="1", max_length=2)
    delay = discord.ui.TextInput(label="Delay entre apostas (segundos)", default="0", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["max_filas_jogador"] = int(self.qtd_filas.value or 1)
        data["config"]["max_partidas_jogador"] = int(self.qtd_partidas.value or 1)
        data["config"]["delay_apostas"] = int(self.delay.value or 0)
        db.save(interaction.guild.id, data)
        embed = embed_jogos(data)
        await interaction.response.edit_message(embed=embed, view=ViewJogos(data.get("filas", {})))


class ModalAdicionarJogo(discord.ui.Modal, title="Adicionar Jogo"):
    nome = discord.ui.TextInput(label="Nome do Jogo", placeholder="ex: EFootball Mobile", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", placeholder="ex: Partidas 1x1 de EFootball", max_length=100, required=False)
    taxa = discord.ui.TextInput(label="Taxa de Mediação (%)", default="10", max_length=5)
    custo = discord.ui.TextInput(label="Custo Adicional (R$)", default="0.00", max_length=10)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        jogo_id = self.nome.value.lower().replace(" ", "_")
        data["filas"][jogo_id] = {
            "nome": self.nome.value,
            "descricao": self.descricao.value,
            "modalidades": {},
            "custo_adicional": float(self.custo.value or 0),
            "taxa_mediacao": float(self.taxa.value or 10),
            "moedas_por_partida": 1,
            "moedas_por_revanche": 1,
        }
        db.save(interaction.guild.id, data)
        embed = embed_jogos(data)
        await interaction.response.edit_message(embed=embed, view=ViewJogos(data.get("filas", {})))


class ModalEditarJogo(discord.ui.Modal, title="Editar Jogo"):
    nome = discord.ui.TextInput(label="Nome", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", max_length=100, required=False)
    taxa = discord.ui.TextInput(label="Taxa de Mediação (%)", default="10", max_length=5)
    custo = discord.ui.TextInput(label="Custo Adicional (R$)", default="0.00", max_length=10)
    moedas = discord.ui.TextInput(label="Moedas partida/revanche (ex: 1/1)", default="1/1", max_length=10)

    def __init__(self, jogo_id, jogo):
        super().__init__()
        self.jogo_id = jogo_id
        self.nome.default = jogo.get("nome", "")
        self.descricao.default = jogo.get("descricao", "")
        self.taxa.default = str(jogo.get("taxa_mediacao", 10))
        self.custo.default = str(jogo.get("custo_adicional", 0))
        self.moedas.default = f"{jogo.get('moedas_por_partida', 1)}/{jogo.get('moedas_por_revanche', 1)}"

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        try:
            s = self.moedas.value.split("/")
            mp, mr = int(s[0]), int(s[1]) if len(s) > 1 else int(s[0])
        except Exception:
            mp, mr = 1, 1
        data["filas"][self.jogo_id].update({
            "nome": self.nome.value,
            "descricao": self.descricao.value,
            "taxa_mediacao": float(self.taxa.value or 10),
            "custo_adicional": float(self.custo.value or 0),
            "moedas_por_partida": mp,
            "moedas_por_revanche": mr,
        })
        db.save(interaction.guild.id, data)
        jogo = data["filas"][self.jogo_id]
        await mostrar_jogo(interaction, self.jogo_id, jogo)


class ModalAdicionarModalidade(discord.ui.Modal, title="Adicionar Modalidade"):
    nome = discord.ui.TextInput(label="Nome (ex: 1x1, 2x2, 3x3)", max_length=10)
    valores = discord.ui.TextInput(
        label="Valores separados por vírgula",
        placeholder="ex: 1.00, 1.50, 2.50, 5.00, 10.00",
        max_length=200
    )

    def __init__(self, jogo_id):
        super().__init__()
        self.jogo_id = jogo_id

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        try:
            lista = [float(v.strip()) for v in self.valores.value.split(",")]
        except ValueError:
            await interaction.response.send_message("❌ Valores inválidos.", ephemeral=True)
            return
        mod_id = self.nome.value.lower().replace(" ", "")
        data["filas"][self.jogo_id]["modalidades"][mod_id] = {
            "nome": self.nome.value,
            "canal_id": None,
            "valores": {str(v): {"taxa_pct": 10.0, "taxa_fixo": 0.0, "tipo_taxa": "pct"} for v in lista},
        }
        db.save(interaction.guild.id, data)
        jogo = data["filas"][self.jogo_id]
        await mostrar_jogo(interaction, self.jogo_id, jogo)


class ModalAdicionarValor(discord.ui.Modal, title="Adicionar Valor à Fila"):
    valor = discord.ui.TextInput(label="Valor (R$)", placeholder="ex: 2.50", max_length=10)
    taxa_pct = discord.ui.TextInput(label="Taxa % de ambos os jogadores", default="10", max_length=5)
    taxa_fixo = discord.ui.TextInput(label="Taxa Fixa R$ (0 = usar %)", default="0", max_length=10)

    def __init__(self, jogo_id, mod_id):
        super().__init__()
        self.jogo_id = jogo_id
        self.mod_id = mod_id

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        try:
            v = float(self.valor.value)
            tp = float(self.taxa_pct.value or 10)
            tf = float(self.taxa_fixo.value or 0)
        except ValueError:
            await interaction.response.send_message("❌ Valor inválido.", ephemeral=True)
            return
        tipo = "fixo" if tf > 0 else "pct"
        data["filas"][self.jogo_id]["modalidades"][self.mod_id]["valores"][str(v)] = {
            "taxa_pct": tp, "taxa_fixo": tf, "tipo_taxa": tipo,
        }
        db.save(interaction.guild.id, data)
        mod = data["filas"][self.jogo_id]["modalidades"][self.mod_id]
        await mostrar_modalidade(interaction, self.jogo_id, self.mod_id, mod)


class ModalEditarTaxaValor(discord.ui.Modal, title="Editar Taxa do Valor"):
    taxa_pct = discord.ui.TextInput(label="Taxa % de ambos jogadores", max_length=5)
    taxa_fixo = discord.ui.TextInput(label="Taxa Fixa R$ (0 = usar %)", default="0", max_length=10)

    def __init__(self, jogo_id, mod_id, valor_str, valor_data):
        super().__init__()
        self.jogo_id = jogo_id
        self.mod_id = mod_id
        self.valor_str = valor_str
        self.taxa_pct.default = str(valor_data.get("taxa_pct", 10))
        self.taxa_fixo.default = str(valor_data.get("taxa_fixo", 0))

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        tf = float(self.taxa_fixo.value or 0)
        tp = float(self.taxa_pct.value or 10)
        tipo = "fixo" if tf > 0 else "pct"
        data["filas"][self.jogo_id]["modalidades"][self.mod_id]["valores"][self.valor_str].update({
            "taxa_pct": tp, "taxa_fixo": tf, "tipo_taxa": tipo,
        })
        db.save(interaction.guild.id, data)
        mod = data["filas"][self.jogo_id]["modalidades"][self.mod_id]
        await mostrar_modalidade(interaction, self.jogo_id, self.mod_id, mod)


class ModalConfigMediadores(discord.ui.Modal, title="Configurar Mediadores"):
    taxa = discord.ui.TextInput(label="Taxa de mediação (%)", default="10", max_length=5)
    qtd = discord.ui.TextInput(label="Partidas simultâneas por mediador", default="20", max_length=3)
    pix_org = discord.ui.TextInput(label="PIX da Org", placeholder="ex: contato@arena.com", max_length=100, required=False)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["taxa_mediador"] = float(self.taxa.value or 10)
        data["config"]["max_partidas_mediador"] = int(self.qtd.value or 20)
        if self.pix_org.value:
            data["config"]["pix_org"] = self.pix_org.value
        db.save(interaction.guild.id, data)
        embed = embed_mediadores(data, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewMediadores())


class ModalMoedaConfig(discord.ui.Modal, title="Configurar Moeda"):
    nome = discord.ui.TextInput(label="Nome da Moeda", default="Moedas", max_length=20)
    emoji = discord.ui.TextInput(label="Emoji", default="🪙", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["moeda_nome"] = self.nome.value
        data["config"]["moeda_emoji"] = self.emoji.value
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(f"✅ Moeda: {self.emoji.value} {self.nome.value}", ephemeral=True)


class ModalCriarCodiguin(discord.ui.Modal, title="Criar Codiguin"):
    codigo = discord.ui.TextInput(label="Código", placeholder="ex: ARENA2024", max_length=30)
    item = discord.ui.TextInput(label="Recompensa", placeholder="ex: 100 moedas", max_length=100)
    usos = discord.ui.TextInput(label="Usos máximos (0 = ilimitado)", default="1", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        if "codiguins" not in data:
            data["codiguins"] = {}
        data["codiguins"][self.codigo.value.upper()] = {
            "item": self.item.value,
            "usos_max": int(self.usos.value or 1),
            "usos_atual": 0, "ativo": True
        }
        db.save(interaction.guild.id, data)
        codiguins = data.get("codiguins", {})
        embed = discord.Embed(title="🎟️ Central - Codiguins", color=0x5865F2)
        embed.description = "\n".join([f"`{k}` → {v['item']} ({v['usos_atual']}/{v['usos_max']} usos)" for k, v in codiguins.items()])
        await interaction.response.edit_message(embed=embed, view=ViewCodiguin())


class ModalAdicionarItem(discord.ui.Modal, title="Adicionar Item"):
    nome = discord.ui.TextInput(label="Nome", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", max_length=100)
    preco = discord.ui.TextInput(label="Preço (moedas)", max_length=10)
    emoji = discord.ui.TextInput(label="Emoji", default="📦", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        item_id = self.nome.value.lower().replace(" ", "_")
        data["loja"][item_id] = {
            "nome": self.nome.value, "descricao": self.descricao.value,
            "preco": int(self.preco.value or 0), "emoji": self.emoji.value, "ativo": True
        }
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(f"✅ Item **{self.emoji.value} {self.nome.value}** adicionado!", ephemeral=True)


# ══════════════════════════════════════════════════════════
#  FUNÇÕES DE NAVEGAÇÃO
# ══════════════════════════════════════════════════════════

async def mostrar_jogo(interaction, jogo_id, jogo):
    modalidades = jogo.get("modalidades", {})
    embed = discord.Embed(title=f"🎮 Jogos — {jogo['nome'].upper()}", color=0x5865F2)
    embed.description = jogo.get("descricao", "")
    embed.add_field(name="Modalidades", value=" | ".join(modalidades.keys()) or "Nenhuma", inline=False)
    embed.add_field(name="Taxa Mediação", value=f"{jogo.get('taxa_mediacao', 10)}%", inline=True)
    embed.add_field(name="Custo Adicional", value=f"R$ {jogo.get('custo_adicional', 0):.2f}", inline=True)
    embed.add_field(name="Moedas Auto", value=f"• Por Partida: {jogo.get('moedas_por_partida', 1)}\n• Por Revanche: {jogo.get('moedas_por_revanche', 1)}", inline=False)
    await interaction.response.edit_message(embed=embed, view=ViewJogoDetalhe(jogo_id, jogo))


async def mostrar_modalidade(interaction, jogo_id, mod_id, mod):
    valores = mod.get("valores", {})
    canal_id = mod.get("canal_id")
    canal = interaction.guild.get_channel(canal_id) if canal_id else None
    vals_sorted = sorted(valores.keys(), key=lambda x: float(x), reverse=True)
    filas_txt = " | ".join([f"R${float(v):.2f}" for v in vals_sorted]) or "Nenhum"
    embed = discord.Embed(title=f"🎮 {jogo_id.upper()} › {mod['nome']}", color=0x5865F2)
    embed.add_field(name="Filas", value=filas_txt, inline=False)
    embed.add_field(name="Canal das Filas", value=canal.mention if canal else "**Não configurado — clique em 'Canal das Filas'**", inline=False)
    await interaction.response.edit_message(embed=embed, view=ViewModalidade(jogo_id, mod_id, mod))


# ══════════════════════════════════════════════════════════
#  VIEWS — CENTRAL PRINCIPAL
# ══════════════════════════════════════════════════════════

class ViewCentral(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Centrais Gerais do Bot  ›", style=discord.ButtonStyle.grey, row=0)
    async def central_geral(self, interaction, button):
        embed = embed_centrais_gerais()
        await interaction.response.edit_message(embed=embed, view=ViewCentralGeral())

    @discord.ui.button(label="Central de Personalizações  ›", style=discord.ButtonStyle.grey, row=1)
    async def central_pers(self, interaction, button):
        embed = embed_personalizacoes()
        await interaction.response.edit_message(embed=embed, view=ViewCentralPersonalizacoes())


class ViewCentralGeral(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectCentralGeral())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class ViewCentralPersonalizacoes(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectPersonalizacoes())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class ViewVoltar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey)
    async def voltar(self, interaction, button):
        embed = embed_centrais_gerais()
        await interaction.response.edit_message(embed=embed, view=ViewCentralGeral())


# ══════════════════════════════════════════════════════════
#  SELECT CENTRAL GERAL
# ══════════════════════════════════════════════════════════

class SelectCentralGeral(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione uma central...", options=[
            discord.SelectOption(label="Jogos", description="Configure taxa, modalidades, etc.", emoji="🎮", value="jogos"),
            discord.SelectOption(label="Filas", description="Configure tipo de criação.", emoji="📋", value="filas"),
            discord.SelectOption(label="Valores das Filas", description="Configure os valores das filas.", emoji="💰", value="valores"),
            discord.SelectOption(label="Mediador", description="Configure o pix, cargo, fila e distribuição.", emoji="🛡️", value="mediador"),
            discord.SelectOption(label="Eventos", description="Configure eventos de vitórias.", emoji="🎉", value="eventos"),
            discord.SelectOption(label="Streamers", description="Configure fila de influencer.", emoji="🎙️", value="streamers"),
            discord.SelectOption(label="Item", description="Configure os itens das lojas ou caixas.", emoji="📦", value="itens"),
            discord.SelectOption(label="Loja", description="Configure as Lojas e seus painéis.", emoji="🛒", value="loja"),
            discord.SelectOption(label="Caixas Misteriosas", description="Configure o sistema de caixas.", emoji="🎁", value="caixas"),
            discord.SelectOption(label="Roleta", description="Configure o sistema de roleta.", emoji="🎰", value="roleta"),
            discord.SelectOption(label="Codiguin", description="Configure os Codiguins.", emoji="🎟️", value="codiguin"),
            discord.SelectOption(label="Moeda/Coin", description="Configure e reset a Moeda/Coin.", emoji="🪙", value="moeda"),
            discord.SelectOption(label="Perfil e Ranking", description="Configure o painel de ranking.", emoji="🏆", value="ranking"),
            discord.SelectOption(label="Destaque Ranking Automático", description="Configure o destaque automático.", emoji="📊", value="destaque"),
            discord.SelectOption(label="Comandos Prefixo", description="Configure o prefixo do bot.", emoji="ℹ️", value="prefixo"),
            discord.SelectOption(label="SS/Analista", description="Configure o sistema de chamar SS.", emoji="🔊", value="ss"),
            discord.SelectOption(label="BlackList", description="Configure os cargos e o painel.", emoji="🚫", value="blacklist"),
            discord.SelectOption(label="Permissões", description="Configure quais cargos têm acesso.", emoji="🔑", value="permissoes"),
            discord.SelectOption(label="Logs", description="Configure os canais de logs.", emoji="📝", value="logs"),
            discord.SelectOption(label="Bot", description="Configure o Bot.", emoji="⚙️", value="bot"),
        ])

    async def callback(self, interaction):
        v = self.values[0]
        data = db.load(interaction.guild.id)

        if v == "jogos":
            await interaction.response.edit_message(embed=embed_jogos(data), view=ViewJogos(data.get("filas", {})))
        elif v == "filas":
            await interaction.response.edit_message(embed=embed_filas(data), view=ViewFilas())
        elif v == "valores":
            await interaction.response.edit_message(embed=embed_valores(data), view=ViewValores(data.get("filas", {})))
        elif v == "mediador":
            await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())
        elif v == "eventos":
            eventos = data.get("eventos", [])
            embed = discord.Embed(title="🎉 Evento Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos Eventos aqui!"
            embed.add_field(name="Quantidade de eventos", value=str(len(eventos)), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos(eventos))
        elif v == "streamers":
            config = data["config"]
            embed = discord.Embed(title="🎙️ Streamers Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos streamers aqui!"
            cargo_id = config.get("cargo_streamer")
            cargo = interaction.guild.get_role(cargo_id) if cargo_id else None
            embed.add_field(name="Streamer pode selecionar mediador(es) da org?", value="🔴 NÃO", inline=False)
            embed.add_field(name="Fila Separada Para Mediadores?", value="🔴 NÃO", inline=False)
            embed.add_field(name="Cargo Streamer", value=cargo.mention if cargo else "Não configurado", inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewStreamers())
        elif v == "moeda":
            config = data["config"]
            total = sum(j.get("moedas", 0) for j in data.get("jogadores", {}).values())
            embed = discord.Embed(title="🪙 Moedas", color=0x5865F2)
            embed.description = "Configure tudo relacionado a Moedas aqui!"
            embed.add_field(name="Nome da Moeda", value=f"{config.get('moeda_emoji', '🪙')} {config.get('moeda_nome', 'Moedas')}", inline=True)
            embed.add_field(name="Em Circulação", value=str(total), inline=True)
            await interaction.response.edit_message(embed=embed, view=ViewMoeda())
        elif v == "ranking":
            config = data["config"]
            embed = discord.Embed(title="🏆 Perfil e Ranking", color=0x5865F2)
            embed.description = "Configure tudo relacionado ao Perfil e Ranking aqui!"
            embed.add_field(name="Último Reset", value=config.get("ultimo_reset_rank", "Nunca resetado"), inline=False)
            embed.add_field(name="Tipo do Ranking", value="Vitórias/Derrotas", inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewRanking())
        elif v == "destaque":
            config = data["config"]
            embed = discord.Embed(title="📊 Destaque Automático", color=0x5865F2)
            embed.description = "Configure o envio automático de rankings.\nO bot enviará o **Top 10** no canal configurado."
            embed.add_field(name="Destaque Diário", value="🟢 Ativo" if config.get("destaque_diario_ativo") else "🔴 Desativado", inline=True)
            embed.add_field(name="Destaque Semanal", value="🟢 Ativo" if config.get("destaque_semanal_ativo") else "🔴 Desativado", inline=True)
            embed.add_field(name="Destaque Mensal", value="🟢 Ativo" if config.get("destaque_mensal_ativo") else "🔴 Desativado", inline=True)
            await interaction.response.edit_message(embed=embed, view=ViewDestaque())
        elif v == "codiguin":
            codiguins = data.get("codiguins", {})
            embed = discord.Embed(title="🎟️ Central - Codiguins", color=0x5865F2)
            embed.description = "\n".join([f"`{k}` → {v2['item']} ({v2['usos_atual']}/{v2['usos_max']} usos)" for k, v2 in codiguins.items()]) or "Nenhum codiguin criado ainda."
            await interaction.response.edit_message(embed=embed, view=ViewCodiguin())
        elif v == "itens":
            itens = data.get("loja", {})
            embed = discord.Embed(title="📦 Itens Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado a Itens aqui!"
            if itens:
                embed.add_field(name="Itens", value="\n".join([f"{i.get('emoji','📦')} **{i['nome']}** — {i.get('preco', 0)} moedas" for i in list(itens.values())[:10]]), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewItens())
        elif v == "permissoes":
            perms = data["config"].get("permissoes", {})
            embed = discord.Embed(title="🔑 Central de Permissões do Bot", color=0x5865F2)
            embed.description = "Configure tudo relacionado a permissões do Bot aqui!"
            perm_lista = [
                ("Visualizar Apostas (+apostas)", "perm_apostas"),
                ("Visualizar BOs", "perm_bos"),
                ("Visualizar Logs (+logs)", "perm_logs"),
                ("Gerenciar Apostas", "perm_gerenciar"),
                ("Gerenciar Vitória/Derrota", "perm_vitoria"),
                ("Gerenciar Mediadores", "perm_mediadores"),
                ("Gerenciar Moedas", "perm_moedas"),
                ("Usar Comandos em todos lugares", "perm_todos"),
                ("Usar o Comando GP", "perm_gp"),
                ("Gerenciar Items", "perm_itens"),
                ("Visualizar Eventos (+evento)", "perm_eventos"),
            ]
            for nome, chave in perm_lista:
                embed.add_field(name=nome, value=perms.get(chave, "*(Nenhum cargo configurado)*"), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewPermissoes())
        elif v == "logs":
            config = data["config"]
            embed = discord.Embed(title="📝 Central de Logs", color=0x5865F2)
            embed.description = "Configure tudo relacionado a Logs aqui!"
            logs_lista = [
                ("Partidas Criadas", "log_partidas_criadas"),
                ("Partidas Concluídas", "log_partidas_concluidas"),
                ("Partidas Canceladas", "log_partidas_canceladas"),
                ("Partidas Encerradas", "log_partidas_encerradas"),
                ("Partidas Logs TXT", "log_partidas_txt"),
                ("Mediador Fila Status", "log_mediador_fila"),
                ("Mediador Receita", "log_mediador_receita"),
                ("Mediador Receita Reset", "log_mediador_reset"),
                ("Moedas Transações", "log_moedas"),
                ("Loja Compras", "log_loja"),
                ("SS/Analista Logs", "log_ss"),
                ("BlackList", "log_blacklist"),
                ("Rate Limit Avisos", "log_ratelimit"),
                ("Campeonatos", "log_campeonato"),
            ]
            for nome, chave in logs_lista:
                canal_id = config.get(chave)
                canal = interaction.guild.get_channel(canal_id) if canal_id else None
                embed.add_field(name=nome, value=canal.mention if canal else "*(Nenhum canal configurado)*", inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewLogs())
        elif v == "blacklist":
            blist = data.get("blacklist", [])
            embed = discord.Embed(title="🚫 BlackList", color=0xFF0000)
            embed.description = "Configure tudo relacionado à BlackList aqui!"
            embed.add_field(name="Total na BlackList", value=str(len(blist)), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewVoltar())
        else:
            embed = discord.Embed(title=v.title(), color=0x5865F2)
            embed.description = "Em breve totalmente configurável!"
            await interaction.response.edit_message(embed=embed, view=ViewVoltar())


class SelectPersonalizacoes(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione uma personalização...", options=[
            discord.SelectOption(label="Componentes", description="Configure/personalize os botões e selects do bot.", emoji="🟢", value="componentes"),
            discord.SelectOption(label="Embeds Padrão", description="Altere embeds fixas do bot.", emoji="📋", value="embeds_padrao"),
            discord.SelectOption(label="Embeds Auxiliares", description="Configure embeds extras do bot.", emoji="📋", value="embeds_aux"),
            discord.SelectOption(label="Mensagens Auxiliares", description="Altere mensagens enviadas pelo bot.", emoji="📋", value="msgs_aux"),
            discord.SelectOption(label="Nome dos Canais das Partidas", description="Altere os nomes dos canais criados.", emoji="📋", value="nome_canais"),
            discord.SelectOption(label="QrCode [Mediadores]", description="Personalize o QrCode de pagamento.", emoji="📱", value="qrcode"),
            discord.SelectOption(label="Textos Auxiliares", description="Altere textos fixos do bot.", emoji="📋", value="textos"),
        ])

    async def callback(self, interaction):
        embed = discord.Embed(title=self.values[0].title(), color=0x5865F2)
        embed.description = "Em breve totalmente configurável pelo Discord!"
        await interaction.response.edit_message(embed=embed, view=ViewCentralPersonalizacoes())


# ══════════════════════════════════════════════════════════
#  VIEWS — JOGOS
# ══════════════════════════════════════════════════════════

class ViewJogos(discord.ui.View):
    def __init__(self, filas):
        super().__init__(timeout=300)
        if filas:
            opcoes = [discord.SelectOption(label="Selecione para configurar", value="none")]
            for jogo_id, jogo in filas.items():
                opcoes.append(discord.SelectOption(
                    label=jogo["nome"],
                    description=f"{len(jogo.get('modalidades', {}))} modalidades",
                    value=f"j_{jogo_id}"
                ))
            sel = discord.ui.Select(placeholder="Selecione um jogo para configurar", options=opcoes[:25], row=0)
            sel.callback = self._jogo_sel
            self.add_item(sel)

    async def _jogo_sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        jogo_id = v[2:]
        data = db.load(interaction.guild.id)
        jogo = data["filas"].get(jogo_id, {})
        await mostrar_jogo(interaction, jogo_id, jogo)

    @discord.ui.button(label="⚙️ Configurar Geral", style=discord.ButtonStyle.blurple, row=1)
    async def config_geral(self, interaction, button):
        await interaction.response.send_modal(ModalJogosGeral())

    @discord.ui.button(label="➕ Adicionar Jogo", style=discord.ButtonStyle.green, row=1)
    async def add_jogo(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarJogo())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewJogoDetalhe(discord.ui.View):
    def __init__(self, jogo_id, jogo):
        super().__init__(timeout=300)
        self.jogo_id = jogo_id
        self.jogo = jogo
        modalidades = jogo.get("modalidades", {})
        if modalidades:
            opcoes = [discord.SelectOption(label="Configurar Modalidade Individual", value="none")]
            for mod_id, mod in modalidades.items():
                opcoes.append(discord.SelectOption(
                    label=f"{mod['nome']} ({len(mod.get('valores', {}))} valores)",
                    value=f"m_{mod_id}"
                ))
            sel = discord.ui.Select(placeholder="Configurar Modalidade Individual", options=opcoes[:25], row=0)
            sel.callback = self._mod_sel
            self.add_item(sel)

    async def _mod_sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        mod_id = v[2:]
        data = db.load(interaction.guild.id)
        mod = data["filas"][self.jogo_id]["modalidades"].get(mod_id, {})
        await mostrar_modalidade(interaction, self.jogo_id, mod_id, mod)

    @discord.ui.button(label="✏️ Editar Jogo", style=discord.ButtonStyle.blurple, row=1)
    async def editar(self, interaction, button):
        await interaction.response.send_modal(ModalEditarJogo(self.jogo_id, self.jogo))

    @discord.ui.button(label="➕ Adicionar Modalidade", style=discord.ButtonStyle.green, row=1)
    async def add_mod(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarModalidade(self.jogo_id))

    @discord.ui.button(label="🗑️ Excluir Jogo", style=discord.ButtonStyle.red, row=1)
    async def excluir(self, interaction, button):
        data = db.load(interaction.guild.id)
        del data["filas"][self.jogo_id]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_jogos(data), view=ViewJogos(data.get("filas", {})))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        await interaction.response.edit_message(embed=embed_jogos(data), view=ViewJogos(data.get("filas", {})))


class ViewModalidade(discord.ui.View):
    def __init__(self, jogo_id, mod_id, mod):
        super().__init__(timeout=300)
        self.jogo_id = jogo_id
        self.mod_id = mod_id
        self.mod = mod
        valores = mod.get("valores", {})
        if valores:
            opcoes = [discord.SelectOption(label="Selecione a Fila Para Personalizar", value="none")]
            for v_str, v_data in sorted(valores.items(), key=lambda x: float(x[0]), reverse=True):
                tipo = v_data.get("tipo_taxa", "pct")
                taxa = f"R${v_data.get('taxa_fixo', 0):.2f}" if tipo == "fixo" else f"{v_data.get('taxa_pct', 10)}%"
                opcoes.append(discord.SelectOption(label=f"R$ {float(v_str):.2f} — taxa: {taxa}", value=f"v_{v_str}"))
            sel = discord.ui.Select(placeholder="Selecione a Fila Para Personalizar", options=opcoes[:25], row=0)
            sel.callback = self._valor_sel
            self.add_item(sel)
        sel_canal = discord.ui.ChannelSelect(placeholder="Canal das Filas — Clique para selecionar", channel_types=[discord.ChannelType.text], row=1)
        sel_canal.callback = self._canal_sel
        self.add_item(sel_canal)

    async def _valor_sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        v_str = v[2:]
        data = db.load(interaction.guild.id)
        v_data = data["filas"][self.jogo_id]["modalidades"][self.mod_id]["valores"].get(v_str, {})
        tipo = v_data.get("tipo_taxa", "pct")
        taxa = f"R$ {v_data.get('taxa_fixo', 0):.2f} fixo" if tipo == "fixo" else f"{v_data.get('taxa_pct', 10)}%"
        embed = discord.Embed(title=f"💰 Valores › R$ {float(v_str):.2f}", color=0x5865F2)
        embed.description = "↳ A Variações de Valores é quando você deseja adicionar mais de um valor para a mesma fila."
        embed.add_field(name="Valor", value=f"R$ {float(v_str):.2f}", inline=True)
        embed.add_field(name="Taxa Mediação Individual", value=taxa, inline=True)
        await interaction.response.edit_message(embed=embed, view=ViewGerenciarValor(self.jogo_id, self.mod_id, v_str, v_data))

    async def _canal_sel(self, interaction):
        canal = interaction.data["values"][0]
        canal_id = int(canal) if isinstance(canal, str) else canal.id
        canal_obj = interaction.guild.get_channel(canal_id)
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["modalidades"][self.mod_id]["canal_id"] = canal_id
        db.save(interaction.guild.id, data)
        self.mod["canal_id"] = canal_id
        await interaction.response.edit_message(
            content=f"✅ Canal das filas: {canal_obj.mention if canal_obj else canal_id}",
            embed=None, view=ViewModalidade(self.jogo_id, self.mod_id, self.mod)
        )

    @discord.ui.button(label="➕ Adicionar Valor", style=discord.ButtonStyle.green, row=2)
    async def add_valor(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarValor(self.jogo_id, self.mod_id))

    @discord.ui.button(label="🗑️ Excluir Modalidade", style=discord.ButtonStyle.red, row=2)
    async def excluir(self, interaction, button):
        data = db.load(interaction.guild.id)
        del data["filas"][self.jogo_id]["modalidades"][self.mod_id]
        db.save(interaction.guild.id, data)
        jogo = data["filas"][self.jogo_id]
        await mostrar_jogo(interaction, self.jogo_id, jogo)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=3)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        jogo = data["filas"][self.jogo_id]
        await mostrar_jogo(interaction, self.jogo_id, jogo)


class ViewGerenciarValor(discord.ui.View):
    def __init__(self, jogo_id, mod_id, valor_str, valor_data):
        super().__init__(timeout=300)
        self.jogo_id = jogo_id
        self.mod_id = mod_id
        self.valor_str = valor_str
        self.valor_data = valor_data
        sel = discord.ui.Select(placeholder="Selecione para configurar", options=[
            discord.SelectOption(label="Variações de Valores: DESLIGADO", description="Clique aqui para LIGAR.", emoji="⚫", value="variacoes"),
            discord.SelectOption(label="Taxa Individual: LIGADO", description="Clique aqui para DESLIGAR.", emoji="🟢", value="taxa_toggle"),
            discord.SelectOption(label="Editar Taxa Mediação Individual", description="Editar a taxa deste valor.", emoji="⚙️", value="editar_taxa"),
            discord.SelectOption(label="Excluir FilaValor", description="Clique aqui para excluir este valor.", emoji="🗑️", value="excluir"),
        ], row=0)
        sel.callback = self._opcao
        self.add_item(sel)

    async def _opcao(self, interaction):
        v = interaction.data["values"][0]
        if v == "editar_taxa":
            await interaction.response.send_modal(ModalEditarTaxaValor(self.jogo_id, self.mod_id, self.valor_str, self.valor_data))
        elif v == "excluir":
            data = db.load(interaction.guild.id)
            del data["filas"][self.jogo_id]["modalidades"][self.mod_id]["valores"][self.valor_str]
            db.save(interaction.guild.id, data)
            mod = data["filas"][self.jogo_id]["modalidades"][self.mod_id]
            await mostrar_modalidade(interaction, self.jogo_id, self.mod_id, mod)
        else:
            await interaction.response.send_message("Em breve!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        mod = data["filas"][self.jogo_id]["modalidades"][self.mod_id]
        await mostrar_modalidade(interaction, self.jogo_id, self.mod_id, mod)


# ══════════════════════════════════════════════════════════
#  VIEWS — FILAS / VALORES
# ══════════════════════════════════════════════════════════

class ViewFilas(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel = discord.ui.Select(placeholder="Selecione o tipo de CRIAÇÃO das partidas.", options=[
            discord.SelectOption(label="Categoria", description="Canal de texto em categoria por mediador", value="categoria"),
            discord.SelectOption(label="Tópico", description="Tópico no canal de tópicos configurado", value="topico"),
            discord.SelectOption(label="Mista", description="Combina tópico e categoria", value="mista"),
        ], row=0)
        sel.callback = self._tipo_sel
        self.add_item(sel)

    async def _tipo_sel(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["tipo_criacao_fila"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_filas(data), view=ViewFilas())

    @discord.ui.button(label="Excluir Categorias Mediadores", style=discord.ButtonStyle.blurple, row=1)
    async def excluir_cats(self, interaction, button):
        await interaction.response.send_message("✅ Categorias serão excluídas na próxima regeneração.", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewValores(discord.ui.View):
    def __init__(self, filas):
        super().__init__(timeout=300)
        opcoes = [discord.SelectOption(label="Configurar Valor Individual", value="none")]
        for jogo_id, jogo in filas.items():
            for mod_id, mod in jogo.get("modalidades", {}).items():
                opcoes.append(discord.SelectOption(
                    label=f"{jogo['nome']} › {mod['nome']}",
                    value=f"{jogo_id}|{mod_id}"
                ))
        if len(opcoes) > 1:
            sel = discord.ui.Select(placeholder="Configurar Valor Individual", options=opcoes[:25], row=0)
            sel.callback = self._sel
            self.add_item(sel)

    async def _sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        jogo_id, mod_id = v.split("|")
        data = db.load(interaction.guild.id)
        mod = data["filas"][jogo_id]["modalidades"][mod_id]
        await mostrar_modalidade(interaction, jogo_id, mod_id, mod)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


# ══════════════════════════════════════════════════════════
#  VIEWS — MEDIADORES
# ══════════════════════════════════════════════════════════

class ViewMediadores(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_canal = discord.ui.ChannelSelect(placeholder="Painel Fila Mediadores — Selecione o canal", channel_types=[discord.ChannelType.text], row=0)
        sel_canal.callback = self._canal_sel
        self.add_item(sel_canal)
        sel_cargo = discord.ui.RoleSelect(placeholder="Cargo Mediador Geral — Selecione o cargo", row=1)
        sel_cargo.callback = self._cargo_sel
        self.add_item(sel_cargo)
        sel_dist = discord.ui.Select(placeholder="Selecione o tipo de DISTRIBUIÇÃO de filas.", options=[
            discord.SelectOption(label="Equilibrado", description="Foca em mediadores com menos partidas abertas", value="equilibrado"),
            discord.SelectOption(label="1por1", description="Distribui uma fila por vez para cada mediador", value="1por1"),
        ], row=2)
        sel_dist.callback = self._dist_sel
        self.add_item(sel_dist)

    async def _canal_sel(self, interaction):
        canal = interaction.data["values"][0]
        canal_id = int(canal) if isinstance(canal, str) else canal.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_fila_mediador"] = canal_id
        db.save(interaction.guild.id, data)
        canal_obj = interaction.guild.get_channel(canal_id)
        await interaction.response.edit_message(
            content=f"✅ Canal fila mediador: {canal_obj.mention if canal_obj else canal_id}",
            embed=embed_mediadores(data, interaction.guild),
            view=ViewMediadores()
        )

    async def _cargo_sel(self, interaction):
        cargo = interaction.data["values"][0]
        cargo_id = int(cargo) if isinstance(cargo, str) else cargo.id
        data = db.load(interaction.guild.id)
        data["config"]["cargo_mediador"] = cargo_id
        db.save(interaction.guild.id, data)
        cargo_obj = interaction.guild.get_role(cargo_id)
        await interaction.response.edit_message(
            content=f"✅ Cargo mediador: {cargo_obj.mention if cargo_obj else cargo_id}",
            embed=embed_mediadores(data, interaction.guild),
            view=ViewMediadores()
        )

    async def _dist_sel(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["distribuicao_mediador"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())

    @discord.ui.button(label="⚙️ Configurar Geral", style=discord.ButtonStyle.blurple, row=3)
    async def config(self, interaction, button):
        await interaction.response.send_modal(ModalConfigMediadores())

    @discord.ui.button(label="💰 Ver Receita", style=discord.ButtonStyle.grey, row=3)
    async def receita(self, interaction, button):
        data = db.load(interaction.guild.id)
        linhas = []
        for uid, j in data.get("jogadores", {}).items():
            if j.get("partidas_mediadas", 0) > 0:
                m = interaction.guild.get_member(int(uid))
                nome = m.display_name if m else uid
                linhas.append(f"**{nome}** — R$ {j.get('receita_total', 0):.2f} ({j['partidas_mediadas']} partidas)")
        await interaction.response.send_message(
            "**💰 Receita dos Mediadores:**\n" + ("\n".join(linhas) if linhas else "Nenhuma receita."),
            ephemeral=True
        )

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


# ══════════════════════════════════════════════════════════
#  VIEWS — OUTROS MÓDULOS
# ══════════════════════════════════════════════════════════

class ViewEventos(discord.ui.View):
    def __init__(self, eventos=None):
        super().__init__(timeout=300)
        self.eventos = eventos or []
        if self.eventos:
            opcoes = [discord.SelectOption(label=ev["nome"][:50], description=("Ativo" if ev.get("ativo") else "Inativo"), value=str(i)) for i, ev in enumerate(self.eventos[:25])]
            sel = discord.ui.Select(placeholder="Selecione um evento para configurar", options=opcoes, row=0)
            sel.callback = self._sel_evento
            self.add_item(sel)

    async def _sel_evento(self, interaction):
        idx = int(interaction.data["values"][0])
        data = db.load(interaction.guild.id)
        evento = data["eventos"][idx]
        embed = discord.Embed(title=f"Configurar Evento: {evento['nome']}", color=0x5865F2)
        embed.add_field(name="Status", value="Ativo" if evento.get("ativo") else "Inativo", inline=True)
        embed.add_field(name="Condição", value=f"{evento.get('condicao', 'vitorias').title()} → {evento.get('quantidade', 1)}", inline=True)
        await interaction.response.edit_message(embed=embed, view=ViewEventoConfig(idx, evento))

    @discord.ui.button(label="Criar Evento", style=discord.ButtonStyle.green, row=1)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalEventoInfoBasicas())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ModalEventoInfoBasicas(discord.ui.Modal, title="Criar Evento - Informações Básicas"):
    nome = discord.ui.TextInput(label="Nome do Evento *", placeholder="Digite o nome do evento.", max_length=50)
    descricao = discord.ui.TextInput(label="Descrição do Evento *", placeholder="Digite a descrição.", max_length=100, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["evento_wip"] = {"nome": self.nome.value, "descricao": self.descricao.value}
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="Configuração do Evento", description="Selecione a condição do evento.", color=0x5865F2)
        embed.set_footer(text="Etapa 2/3")
        await interaction.response.send_message(embed=embed, view=ViewEventoEtapa2(), ephemeral=True)


class ViewEventoEtapa2(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.Select(placeholder="Selecione a condição do evento.", options=[
            discord.SelectOption(label="Vitórias", value="vitorias"),
            discord.SelectOption(label="Derrotas", value="derrotas"),
        ], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        data = db.load(interaction.guild.id)
        data["evento_wip"]["condicao"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.send_modal(ModalEventoQuantidade())


class ModalEventoQuantidade(discord.ui.Modal, title="Definir Quantidade"):
    quantidade = discord.ui.TextInput(label="Quantidade *", placeholder="Digite um número.", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        wip = data.get("evento_wip", {})
        if "eventos" not in data:
            data["eventos"] = []
        novo = {
            "id": len(data["eventos"]),
            "nome": wip.get("nome", "Evento"),
            "descricao": wip.get("descricao", ""),
            "condicao": wip.get("condicao", "vitorias"),
            "quantidade": int(self.quantidade.value or 1),
            "ativo": True, "consecutivo": False, "revanche": False,
            "data_inicio": None, "data_fim": None,
            "criado_em": datetime.now().isoformat()
        }
        data["eventos"].append(novo)
        data.pop("evento_wip", None)
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title=f"Configurar Evento: {novo['nome']}", color=0x5865F2)
        embed.add_field(name="Status", value="Ativo", inline=True)
        embed.add_field(name="Condição", value=f"{novo['condicao'].title()} → {novo['quantidade']}", inline=True)
        await interaction.response.send_message(embed=embed, view=ViewEventoConfig(len(data["eventos"]) - 1, novo), ephemeral=True)


class ViewEventoConfig(discord.ui.View):
    def __init__(self, idx, evento):
        super().__init__(timeout=300)
        self.idx = idx
        self.evento = evento
        sel = discord.ui.Select(placeholder="Selecione para configurar", options=[
            discord.SelectOption(label="Excluir Evento", emoji="🗑️", value="excluir"),
        ], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        v = interaction.data["values"][0]
        data = db.load(interaction.guild.id)
        if v == "excluir":
            data["eventos"].pop(self.idx)
            db.save(interaction.guild.id, data)
            embed = discord.Embed(title="🎉 Evento Geral", color=0x5865F2)
            embed.add_field(name="Quantidade de eventos:", value=str(len(data["eventos"])), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos(data.get("eventos", [])))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        embed = discord.Embed(title="🎉 Evento Geral", color=0x5865F2)
        embed.add_field(name="Quantidade de eventos:", value=str(len(data.get("eventos", []))), inline=False)
        await interaction.response.edit_message(embed=embed, view=ViewEventos(data.get("eventos", [])))


class ViewStreamers(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_cat = discord.ui.ChannelSelect(placeholder="Selecione a Categoria", channel_types=[discord.ChannelType.category], row=0)
        sel_cat.callback = self._cat
        self.add_item(sel_cat)
        sel_cargo = discord.ui.RoleSelect(placeholder="Selecione o Cargo Streamer", row=1)
        sel_cargo.callback = self._cargo
        self.add_item(sel_cargo)
        sel_painel = discord.ui.ChannelSelect(placeholder="Selecione o Canal do Painel", channel_types=[discord.ChannelType.text], row=2)
        sel_painel.callback = self._painel
        self.add_item(sel_painel)
        sel_liveon = discord.ui.ChannelSelect(placeholder="Selecione o Canal de LiveOn", channel_types=[discord.ChannelType.text], row=3)
        sel_liveon.callback = self._liveon
        self.add_item(sel_liveon)

    async def _cat(self, interaction):
        cid = interaction.data["values"][0]
        canal_id = int(cid) if isinstance(cid, str) else cid.id
        data = db.load(interaction.guild.id)
        data["config"]["streamer_categoria_id"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Categoria configurada!", ephemeral=True)

    async def _cargo(self, interaction):
        cid = interaction.data["values"][0]
        cargo_id = int(cid) if isinstance(cid, str) else cid.id
        data = db.load(interaction.guild.id)
        data["config"]["cargo_streamer"] = cargo_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Cargo streamer configurado!", ephemeral=True)

    async def _painel(self, interaction):
        cid = interaction.data["values"][0]
        canal_id = int(cid) if isinstance(cid, str) else cid.id
        canal = interaction.guild.get_channel(canal_id)
        data = db.load(interaction.guild.id)
        data["config"]["canal_streamer_painel"] = canal_id
        db.save(interaction.guild.id, data)
        if canal:
            embed = discord.Embed(title="Painel do Streamer", description="Bem-vindo(a) ao painel do Streamer.\nClique em **Configurar** para gerenciar sua fila.", color=0x5865F2)
            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="Configurar", style=discord.ButtonStyle.grey, custom_id="STREAMER|configurar"))
            await canal.send(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Painel postado em {canal.mention}!", ephemeral=True)
        else:
            await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

    async def _liveon(self, interaction):
        cid = interaction.data["values"][0]
        canal_id = int(cid) if isinstance(cid, str) else cid.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_streamer_liveon"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal Live On configurado!", ephemeral=True)

    @discord.ui.button(label="Desligada", style=discord.ButtonStyle.red, row=4)
    async def toggle_med(self, interaction, button):
        data = db.load(interaction.guild.id)
        atual = data["config"].get("streamer_med_solo", False)
        data["config"]["streamer_med_solo"] = not atual
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Streamer selecionar mediador: " + ("SIM" if not atual else "NÃO"), ephemeral=True)

    @discord.ui.button(label="Desligada", style=discord.ButtonStyle.red, row=4)
    async def toggle_fila(self, interaction, button):
        data = db.load(interaction.guild.id)
        atual = data["config"].get("streamer_fila_sep", False)
        data["config"]["streamer_fila_sep"] = not atual
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Fila separada: " + ("SIM" if not atual else "NÃO"), ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewMoeda(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Configurar Geral", style=discord.ButtonStyle.blurple)
    async def config(self, interaction, button):
        await interaction.response.send_modal(ModalMoedaConfig())

    @discord.ui.button(label="Resetar Moedas Geral", style=discord.ButtonStyle.red)
    async def reset(self, interaction, button):
        data = db.load(interaction.guild.id)
        for uid in data["jogadores"]:
            data["jogadores"][uid]["moedas"] = 0
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Moedas resetadas!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewRanking(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_canal = discord.ui.ChannelSelect(placeholder="Canal do Painel de Ranking", channel_types=[discord.ChannelType.text], row=0)
        sel_canal.callback = self._canal_sel
        self.add_item(sel_canal)

    async def _canal_sel(self, interaction):
        cid = interaction.data["values"][0]
        canal_id = int(cid) if isinstance(cid, str) else cid.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_ranking"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal do ranking configurado!", ephemeral=True)

    @discord.ui.button(label="Resetar Rank", style=discord.ButtonStyle.red, row=1)
    async def reset(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["ranking"] = {"geral": {}, "diario": {}, "semanal": {}, "mensal": {}}
        data["config"]["ultimo_reset_rank"] = datetime.now().strftime("%d/%m/%Y às %H:%M")
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Ranking resetado!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewDestaque(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_d = discord.ui.ChannelSelect(placeholder="Canal do Destaque Diário", channel_types=[discord.ChannelType.text], row=0)
        sel_d.callback = lambda i: self._canal_sel(i, "diario")
        self.add_item(sel_d)
        sel_s = discord.ui.ChannelSelect(placeholder="Canal do Destaque Semanal", channel_types=[discord.ChannelType.text], row=1)
        sel_s.callback = lambda i: self._canal_sel(i, "semanal")
        self.add_item(sel_s)
        sel_m = discord.ui.ChannelSelect(placeholder="Canal do Destaque Mensal", channel_types=[discord.ChannelType.text], row=2)
        sel_m.callback = lambda i: self._canal_sel(i, "mensal")
        self.add_item(sel_m)

    async def _canal_sel(self, interaction, periodo):
        cid = interaction.data["values"][0]
        canal_id = int(cid) if isinstance(cid, str) else cid.id
        data = db.load(interaction.guild.id)
        data["config"][f"canal_destaque_{periodo}"] = canal_id
        data["config"][f"destaque_{periodo}_ativo"] = True
        db.save(interaction.guild.id, data)
        canal = interaction.guild.get_channel(canal_id)
        await interaction.response.send_message(f"✅ Destaque {periodo}: {canal.mention if canal else canal_id}", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=3)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewCodiguin(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Criar Novo Codiguin", style=discord.ButtonStyle.blurple)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalCriarCodiguin())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewItens(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Adicionar Item", style=discord.ButtonStyle.green)
    async def add(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarItem())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewPermissoes(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel = discord.ui.Select(placeholder="Selecione a Permissão que deseja alterar.", options=[
            discord.SelectOption(label="Visualizar Apostas (+apostas)", value="perm_apostas"),
            discord.SelectOption(label="Gerenciar Vitória/Derrota", value="perm_vitoria"),
            discord.SelectOption(label="Gerenciar Mediadores", value="perm_mediadores"),
            discord.SelectOption(label="Gerenciar Moedas", value="perm_moedas"),
            discord.SelectOption(label="Usar Comandos em todos lugares", value="perm_todos"),
            discord.SelectOption(label="Gerenciar Items", value="perm_itens"),
            discord.SelectOption(label="Usar o Comando GP", value="perm_gp"),
            discord.SelectOption(label="Visualizar Eventos (+evento)", value="perm_eventos"),
            discord.SelectOption(label="Visualizar BOs", value="perm_bos"),
            discord.SelectOption(label="Visualizar Logs (+logs)", value="perm_logs"),
            discord.SelectOption(label="Gerenciar Apostas", value="perm_gerenciar"),
        ], row=0)
        sel.callback = self._perm_sel
        self.add_item(sel)

    async def _perm_sel(self, interaction):
        perm_key = interaction.data["values"][0]
        view = discord.ui.View(timeout=60)
        sel = discord.ui.RoleSelect(placeholder=f"Selecione o cargo para: {perm_key}")
        async def role_cb(i):
            cargo = i.data["values"][0]
            cargo_id = int(cargo) if isinstance(cargo, str) else cargo.id
            cargo_obj = i.guild.get_role(cargo_id)
            data = db.load(i.guild.id)
            if "permissoes" not in data["config"]:
                data["config"]["permissoes"] = {}
            data["config"]["permissoes"][perm_key] = cargo_obj.mention if cargo_obj else str(cargo_id)
            db.save(i.guild.id, data)
            await i.response.send_message(f"✅ {perm_key} → {cargo_obj.mention if cargo_obj else cargo_id}", ephemeral=True)
        sel.callback = role_cb
        view.add_item(sel)
        await interaction.response.send_message(f"Selecione o cargo para **{perm_key}**:", view=view, ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


class ViewLogs(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel = discord.ui.Select(placeholder="Selecione a log que deseja alterar.", options=[
            discord.SelectOption(label="Partidas Criadas", value="log_partidas_criadas"),
            discord.SelectOption(label="Partidas Concluídas", value="log_partidas_concluidas"),
            discord.SelectOption(label="Partidas Canceladas", value="log_partidas_canceladas"),
            discord.SelectOption(label="Partidas Encerradas", value="log_partidas_encerradas"),
            discord.SelectOption(label="Mediador Receita", value="log_mediador_receita"),
            discord.SelectOption(label="Moedas Transações", value="log_moedas"),
            discord.SelectOption(label="Loja Compras", value="log_loja"),
            discord.SelectOption(label="SS/Analista Logs", value="log_ss"),
            discord.SelectOption(label="BlackList", value="log_blacklist"),
            discord.SelectOption(label="Campeonatos", value="log_campeonato"),
            discord.SelectOption(label="Rate Limit Avisos", value="log_ratelimit"),
        ], row=0)
        sel.callback = self._log_sel
        self.add_item(sel)

    async def _log_sel(self, interaction):
        log_key = interaction.data["values"][0]
        view = discord.ui.View(timeout=60)
        sel = discord.ui.ChannelSelect(placeholder=f"Canal para: {log_key}", channel_types=[discord.ChannelType.text])
        async def canal_cb(i):
            canal = i.data["values"][0]
            canal_id = int(canal) if isinstance(canal, str) else canal.id
            canal_obj = i.guild.get_channel(canal_id)
            data = db.load(i.guild.id)
            data["config"][log_key] = canal_id
            db.save(i.guild.id, data)
            await i.response.send_message(f"✅ {log_key} → {canal_obj.mention if canal_obj else canal_id}", ephemeral=True)
        sel.callback = canal_cb
        view.add_item(sel)
        await interaction.response.send_message(f"Selecione o canal para **{log_key}**:", view=view, ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        await interaction.response.edit_message(embed=embed_centrais_gerais(), view=ViewCentralGeral())


# ══════════════════════════════════════════════════════════
#  STREAMER CONFIG (on_interaction handler)
# ══════════════════════════════════════════════════════════

class ModalStreamerRegras(discord.ui.Modal, title="Editar Regras"):
    regras = discord.ui.TextInput(label="Descrição/Regras", style=discord.TextStyle.paragraph, max_length=500, required=False)
    def __init__(self, uid):
        super().__init__()
        self.uid = uid
    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})["regras"] = self.regras.value
        db.save(interaction.guild.id, data)
        await _atualizar_streamer(interaction, self.uid, data)


class ModalStreamerNome(discord.ui.Modal, title="Editar Nome do Canal"):
    nome = discord.ui.TextInput(label="Nome do Canal", placeholder="ex: contra - [[nome_streamer]]", max_length=50, required=False)
    def __init__(self, uid):
        super().__init__()
        self.uid = uid
    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})["nome_canal"] = self.nome.value
        db.save(interaction.guild.id, data)
        await _atualizar_streamer(interaction, self.uid, data)


class ModalStreamerLink(discord.ui.Modal, title="Editar Link da Live"):
    link = discord.ui.TextInput(label="Link da Live", placeholder="ex: twitch.tv/seucanal", max_length=100, required=False)
    def __init__(self, uid):
        super().__init__()
        self.uid = uid
    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})["link"] = self.link.value
        db.save(interaction.guild.id, data)
        await _atualizar_streamer(interaction, self.uid, data)


class ModalStreamerValor(discord.ui.Modal, title="Editar Valor da Fila"):
    valor = discord.ui.TextInput(label="Valor da partida (R$)", placeholder="ex: 5.00", max_length=10)
    def __init__(self, uid):
        super().__init__()
        self.uid = uid
    async def on_submit(self, interaction):
        try:
            v = float(self.valor.value.replace(",", "."))
        except ValueError:
            await interaction.response.send_message("Valor inválido!", ephemeral=True)
            return
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})["valor"] = v
        db.save(interaction.guild.id, data)
        await _atualizar_streamer(interaction, self.uid, data)


async def _atualizar_streamer(interaction, uid, data=None):
    if data is None:
        data = db.load(interaction.guild.id)
    streamer = data.get("streamers", {}).get(uid, {})
    membro = interaction.guild.get_member(int(uid))
    nome = membro.display_name if membro else uid
    embed = discord.Embed(title=f"Streamer — {nome}", color=0x5865F2)
    embed.description = "Status: " + ("Pronto" if streamer.get("jogo") else "⚠️ Faltam configurações")
    embed.add_field(name="Sua Descrição/Regras", value=streamer.get("regras", "Não definido."), inline=False)
    embed.add_field(name="Nome do Canal", value=streamer.get("nome_canal", "#contra - [[nome_streamer]]"), inline=False)
    embed.add_field(name="Link da Live", value=streamer.get("link", "Nenhum"), inline=False)
    embed.add_field(name="Valor da Fila", value="R$ " + str(round(streamer.get("valor", 0.0), 2)), inline=True)
    embed.add_field(name="Jogo Selecionado", value=streamer.get("jogo", "Nenhum"), inline=True)
    view = ViewStreamerConfig(uid, data)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ViewStreamerConfig(discord.ui.View):
    def __init__(self, uid, data=None):
        super().__init__(timeout=300)
        self.uid = uid
        if data:
            filas = data.get("filas", {})
            if filas:
                opcoes = [discord.SelectOption(label=j["nome"], value=jid) for jid, j in list(filas.items())[:25]]
                sel = discord.ui.Select(placeholder="Selecione UM Jogo.", options=opcoes, row=0)
                sel.callback = self._sel_jogo
                self.add_item(sel)

    async def _sel_jogo(self, interaction):
        jogo_id = interaction.data["values"][0]
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})["jogo"] = jogo_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Jogo selecionado!", ephemeral=True)

    @discord.ui.button(label="Editar Regras", style=discord.ButtonStyle.grey, row=1)
    async def regras(self, interaction, button):
        await interaction.response.send_modal(ModalStreamerRegras(self.uid))

    @discord.ui.button(label="Editar Nome", style=discord.ButtonStyle.grey, row=1)
    async def nome(self, interaction, button):
        await interaction.response.send_modal(ModalStreamerNome(self.uid))

    @discord.ui.button(label="Editar Link", style=discord.ButtonStyle.grey, row=2)
    async def link(self, interaction, button):
        await interaction.response.send_modal(ModalStreamerLink(self.uid))

    @discord.ui.button(label="Editar Valor", style=discord.ButtonStyle.grey, row=2)
    async def valor_btn(self, interaction, button):
        await interaction.response.send_modal(ModalStreamerValor(self.uid))

    @discord.ui.button(label="Filas: Desligadas", style=discord.ButtonStyle.grey, row=3)
    async def filas(self, interaction, button):
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})
        atual = data["streamers"][self.uid].get("ativo", False)
        data["streamers"][self.uid]["ativo"] = not atual
        nova_situacao = not atual
        db.save(interaction.guild.id, data)
        if nova_situacao:
            streamer = data["streamers"][self.uid]
            if not streamer.get("jogo"):
                data["streamers"][self.uid]["ativo"] = False
                db.save(interaction.guild.id, data)
                await interaction.response.send_message("Selecione um jogo primeiro!", ephemeral=True)
                return
            membro = interaction.guild.get_member(int(self.uid))
            nome_exibir = membro.display_name if membro else "streamer"
            regras = streamer.get("regras", "Sem regras definidas.")
            valor = streamer.get("valor", 0.0)
            canal_id = streamer.get("canal_fila_id")
            canal = interaction.guild.get_channel(canal_id) if canal_id else None
            if canal:
                embed = discord.Embed(title="Contra " + nome_exibir, description=regras, color=0x00FF00)
                embed.add_field(name="Valor da Partida", value="R$ " + str(round(valor, 2)), inline=True)
                embed.add_field(name="Jogadores na fila:", value="Nenhum jogador na fila.", inline=False)
                async for msg in canal.history(limit=10):
                    if msg.author == interaction.guild.me and msg.embeds:
                        vf = discord.ui.View(timeout=None)
                        vf.add_item(discord.ui.Button(label="Entrar Na Fila", style=discord.ButtonStyle.green, custom_id="SFILA|entrar|" + self.uid))
                        vf.add_item(discord.ui.Button(label="Sair da Fila", style=discord.ButtonStyle.grey, custom_id="SFILA|sair|" + self.uid))
                        vf.add_item(discord.ui.Button(label="Chamar Próximo", style=discord.ButtonStyle.blurple, custom_id="SFILA|chamar|" + self.uid, row=1))
                        await msg.edit(embed=embed, view=vf)
                        break
                await interaction.response.send_message("Filas LIGADAS!", ephemeral=True)
            else:
                cat_id = data["config"].get("streamer_categoria_id")
                cat = interaction.guild.get_channel(cat_id) if cat_id else None
                nome_canal = streamer.get("nome_canal", "contra-streamer").replace("[[nome_streamer]]", nome_exibir)
                try:
                    canal_fila = await interaction.guild.create_text_channel(nome_canal, category=cat)
                    data["streamers"][self.uid]["canal_fila_id"] = canal_fila.id
                    db.save(interaction.guild.id, data)
                    embed = discord.Embed(title="Contra " + nome_exibir, description=regras, color=0x00FF00)
                    embed.add_field(name="Valor da Partida", value="R$ " + str(round(valor, 2)), inline=True)
                    embed.add_field(name="Jogadores na fila:", value="Nenhum jogador na fila.", inline=False)
                    vf = discord.ui.View(timeout=None)
                    vf.add_item(discord.ui.Button(label="Entrar Na Fila", style=discord.ButtonStyle.green, custom_id="SFILA|entrar|" + self.uid))
                    vf.add_item(discord.ui.Button(label="Sair da Fila", style=discord.ButtonStyle.grey, custom_id="SFILA|sair|" + self.uid))
                    vf.add_item(discord.ui.Button(label="Chamar Próximo", style=discord.ButtonStyle.blurple, custom_id="SFILA|chamar|" + self.uid, row=1))
                    await canal_fila.send(embed=embed, view=vf)
                    await interaction.response.send_message("Filas LIGADAS! Canal: " + canal_fila.mention, ephemeral=True)
                except Exception as e:
                    await interaction.response.send_message("Erro: " + str(e), ephemeral=True)
        else:
            await interaction.response.send_message("Filas DESLIGADAS!", ephemeral=True)

    @discord.ui.button(label="Modo Stream: Basico", style=discord.ButtonStyle.grey, row=4)
    async def modo(self, interaction, button):
        data = db.load(interaction.guild.id)
        data.setdefault("streamers", {}).setdefault(self.uid, {})
        modos = ["Basico", "Avancado"]
        atual = data["streamers"][self.uid].get("modo", "Basico")
        novo = modos[(modos.index(atual) + 1) % len(modos)] if atual in modos else "Basico"
        data["streamers"][self.uid]["modo"] = novo
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Modo Stream: " + novo, ephemeral=True)


# ══════════════════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════════════════

class Central(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        cid = interaction.data.get("custom_id", "")
        if interaction.response.is_done():
            return

        # STREAMER handlers
        if cid == "STREAMER|configurar":
            data = db.load(interaction.guild.id)
            uid = str(interaction.user.id)
            await _atualizar_streamer(interaction, uid, data)
            return

        if not cid.startswith("STREAMER|") and not cid.startswith("SFILA|"):
            return

        data = db.load(interaction.guild.id)

        if cid.startswith("SFILA|"):
            partes = cid.split("|")
            acao = partes[1] if len(partes) > 1 else ""
            uid_str = partes[2] if len(partes) > 2 else None
            if not uid_str:
                await interaction.response.send_message("Erro.", ephemeral=True)
                return
            data.setdefault("filas_streamer", {})
            fila_key = "sfila_" + uid_str
            fila = data["filas_streamer"].get(fila_key, [])
            uid_jogador = interaction.user.id

            if acao == "entrar":
                if uid_jogador in fila:
                    await interaction.response.send_message("Você já está na fila!", ephemeral=True)
                    return
                fila.append(uid_jogador)
                data["filas_streamer"][fila_key] = fila
                db.save(interaction.guild.id, data)
                embed = discord.Embed(title=interaction.channel.name, color=0x00FF00)
                embed.add_field(name="Jogadores na fila:", value="\n".join(["<@" + str(u) + ">" for u in fila]) if fila else "Nenhum jogador na fila.", inline=False)
                await interaction.response.send_message("✅ Você entrou na fila! Posição: " + str(len(fila)), ephemeral=True)
                await interaction.message.edit(embed=embed)
            elif acao == "sair":
                if uid_jogador not in fila:
                    await interaction.response.send_message("Você não está na fila!", ephemeral=True)
                    return
                fila.remove(uid_jogador)
                data["filas_streamer"][fila_key] = fila
                db.save(interaction.guild.id, data)
                embed = discord.Embed(title=interaction.channel.name, color=0x00FF00)
                embed.add_field(name="Jogadores na fila:", value="\n".join(["<@" + str(u) + ">" for u in fila]) if fila else "Nenhum jogador na fila.", inline=False)
                await interaction.response.send_message("✅ Você saiu da fila!", ephemeral=True)
                await interaction.message.edit(embed=embed)
            elif acao == "chamar":
                if str(uid_jogador) != uid_str:
                    await interaction.response.send_message("Apenas o streamer pode chamar!", ephemeral=True)
                    return
                if not fila:
                    await interaction.response.send_message("Fila vazia!", ephemeral=True)
                    return
                proximo = fila.pop(0)
                data["filas_streamer"][fila_key] = fila
                db.save(interaction.guild.id, data)
                embed = discord.Embed(title=interaction.channel.name, color=0x00FF00)
                embed.add_field(name="Jogadores na fila:", value="\n".join(["<@" + str(u) + ">" for u in fila]) if fila else "Nenhum jogador na fila.", inline=False)
                await interaction.response.send_message("<@" + str(proximo) + "> é o próximo! Prepare-se para jogar!", ephemeral=False)
                await interaction.message.edit(embed=embed)
            return

        # STREAMER outros
        acao = cid.split("|")[1]
        uid = str(interaction.user.id)
        data.setdefault("streamers", {}).setdefault(uid, {})
        if acao == "regras":
            await interaction.response.send_modal(ModalStreamerRegras(uid))
        elif acao == "nome":
            await interaction.response.send_modal(ModalStreamerNome(uid))
        elif acao == "link":
            await interaction.response.send_modal(ModalStreamerLink(uid))
        elif acao == "filas":
            atual = data["streamers"][uid].get("ativo", False)
            data["streamers"][uid]["ativo"] = not atual
            db.save(interaction.guild.id, data)
            await interaction.response.send_message("Filas: " + ("LIGADAS" if not atual else "DESLIGADAS"), ephemeral=True)
        elif acao == "modo":
            modos = ["Basico", "Avancado"]
            atual = data["streamers"][uid].get("modo", "Basico")
            novo = modos[(modos.index(atual) + 1) % len(modos)] if atual in modos else "Basico"
            data["streamers"][uid]["modo"] = novo
            db.save(interaction.guild.id, data)
            await interaction.response.send_message("Modo: " + novo, ephemeral=True)

    @app_commands.command(name="central", description="[ADMIN] Central de controle do bot")
    async def central(self, interaction: discord.Interaction):
        embed = embed_central(interaction.guild)
        await interaction.response.send_message(embed=embed, view=ViewCentral(), ephemeral=True)

    @app_commands.command(name="codiguin", description="Resgata um codiguin")
    async def resgatar_codiguin(self, interaction: discord.Interaction, codigo: str):
        data = db.load(interaction.guild.id)
        cod = data.get("codiguins", {}).get(codigo.upper())
        if not cod or not cod.get("ativo"):
            await interaction.response.send_message("❌ Código inválido.", ephemeral=True)
            return
        if cod["usos_max"] > 0 and cod["usos_atual"] >= cod["usos_max"]:
            await interaction.response.send_message("❌ Código esgotado.", ephemeral=True)
            return
        cod["usos_atual"] += 1
        db.save(interaction.guild.id, data)
        await interaction.response.send_message(f"✅ Resgatado! Recompensa: **{cod['item']}**", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Central(bot))
