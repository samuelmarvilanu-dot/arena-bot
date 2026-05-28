"""
cogs/central.py — Central completa baseada na documentação oficial ARENA X1
"""
import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db
from datetime import datetime


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
        await interaction.response.send_message("✅ Configurações gerais salvas!", ephemeral=True)


class ModalAdicionarJogo(discord.ui.Modal, title="Adicionar Jogo"):
    nome = discord.ui.TextInput(label="Nome do Jogo", placeholder="ex: EFootball Mobile", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", placeholder="ex: Partidas de efootball mobile", max_length=100)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        jogo_id = self.nome.value.lower().replace(" ", "_")
        data["filas"][jogo_id] = {
            "nome": self.nome.value, "descricao": self.descricao.value,
            "modalidades": {}, "custo_adicional": 0.0, "taxa_mediacao": 10.0,
            "moedas_por_partida": 1, "moedas_por_revanche": 1,
            "cargo_adicional": None, "thread_canal_id": None,
        }
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Jogo **" + self.nome.value + "** criado!", ephemeral=True)


class ModalEditarJogo(discord.ui.Modal, title="Editar Jogo"):
    nome = discord.ui.TextInput(label="Nome", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", max_length=100)
    custo = discord.ui.TextInput(label="Custo Adicional (R$)", default="0.00", max_length=10)
    taxa = discord.ui.TextInput(label="Taxa Mediação (%)", default="10", max_length=5)
    moedas = discord.ui.TextInput(label="Moedas partida/revanche (ex: 1/1)", default="1/1", max_length=10)

    def __init__(self, jogo_id, jogo):
        super().__init__()
        self.jogo_id = jogo_id
        self.nome.default = jogo.get("nome", "")
        self.descricao.default = jogo.get("descricao", "")
        self.custo.default = str(jogo.get("custo_adicional", 0.0))
        self.taxa.default = str(jogo.get("taxa_mediacao", 10))
        self.moedas.default = str(jogo.get("moedas_por_partida", 1)) + "/" + str(jogo.get("moedas_por_revanche", 1))

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        try:
            s = self.moedas.value.split("/")
            mp, mr = int(s[0]), int(s[1]) if len(s) > 1 else int(s[0])
        except Exception:
            mp, mr = 1, 1
        data["filas"][self.jogo_id].update({
            "nome": self.nome.value, "descricao": self.descricao.value,
            "custo_adicional": float(self.custo.value or 0),
            "taxa_mediacao": float(self.taxa.value or 10),
            "moedas_por_partida": mp, "moedas_por_revanche": mr,
        })
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Jogo atualizado!", ephemeral=True)


class ModalEditarCusto(discord.ui.Modal, title="Editar Custo Adicional"):
    custo = discord.ui.TextInput(label="Custo Adicional (R$)", placeholder="ex: 0.50", max_length=10)

    def __init__(self, jogo_id):
        super().__init__()
        self.jogo_id = jogo_id

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["custo_adicional"] = float(self.custo.value or 0)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Custo adicional: R$ " + self.custo.value, ephemeral=True)


class ModalEditarTaxa(discord.ui.Modal, title="Editar Taxa de Mediação"):
    taxa = discord.ui.TextInput(label="Taxa (%)", placeholder="ex: 10", max_length=5)

    def __init__(self, jogo_id):
        super().__init__()
        self.jogo_id = jogo_id

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["taxa_mediacao"] = float(self.taxa.value or 10)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Taxa: " + self.taxa.value + "%", ephemeral=True)


class ModalEditarMoedas(discord.ui.Modal, title="Editar Moedas Auto"):
    moedas = discord.ui.TextInput(label="Moedas partida/revanche (ex: 1/1)", default="1/1", max_length=10)

    def __init__(self, jogo_id):
        super().__init__()
        self.jogo_id = jogo_id

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        try:
            s = self.moedas.value.split("/")
            mp, mr = int(s[0]), int(s[1]) if len(s) > 1 else int(s[0])
        except Exception:
            mp, mr = 1, 1
        data["filas"][self.jogo_id]["moedas_por_partida"] = mp
        data["filas"][self.jogo_id]["moedas_por_revanche"] = mr
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Moedas: " + str(mp) + "/partida | " + str(mr) + "/revanche", ephemeral=True)


class ModalAdicionarModalidade(discord.ui.Modal, title="Adicionar Modalidade"):
    nome = discord.ui.TextInput(label="Nome (ex: 1x1, 2x2, 3x3)", max_length=10)
    valores = discord.ui.TextInput(label="Valores (separados por vírgula)", placeholder="ex: 1.00, 1.50, 2.50, 5.00", max_length=200)

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
            "nome": self.nome.value, "canal_id": None,
            "valores": {str(v): {"taxa_pct": 10.0, "taxa_fixo": 0.0, "tipo_taxa": "pct"} for v in lista},
        }
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Modalidade **" + self.nome.value + "** criada!", ephemeral=True)


class ModalAdicionarValor(discord.ui.Modal, title="Adicionar Valor à Fila"):
    valor = discord.ui.TextInput(label="Valor (R$)", placeholder="ex: 2.50", max_length=10)
    taxa_pct = discord.ui.TextInput(label="Taxa % (cobrada de AMBOS)", default="10", max_length=5)
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
        taxa_txt = "R$ " + str(tf) + " fixo" if tipo == "fixo" else str(tp) + "%"
        await interaction.response.send_message("✅ R$ " + str(v) + " adicionado (taxa: " + taxa_txt + ")", ephemeral=True)


class ModalEditarTaxaValor(discord.ui.Modal, title="Editar Taxa do Valor"):
    taxa_pct = discord.ui.TextInput(label="Taxa % (cobrada de AMBOS)", max_length=5)
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
        taxa_txt = "R$ " + str(tf) + " fixo" if tipo == "fixo" else str(tp) + "%"
        await interaction.response.send_message("✅ Taxa de R$ " + self.valor_str + " → " + taxa_txt, ephemeral=True)


class ModalMediadorPIX(discord.ui.Modal, title="Registrar PIX de Mediador"):
    usuario_id = discord.ui.TextInput(label="ID ou @ do Discord do Mediador", placeholder="ex: 123456789", max_length=50)
    pix = discord.ui.TextInput(label="Chave PIX", placeholder="ex: email@exemplo.com", max_length=100)

    async def on_submit(self, interaction):
        guild = interaction.guild
        data = db.load(guild.id)
        uid_str = self.usuario_id.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        membro = None
        try:
            membro = guild.get_member(int(uid_str))
        except ValueError:
            for m in guild.members:
                if m.name.lower() == uid_str.lower() or m.display_name.lower() == uid_str.lower():
                    membro = m
                    break
        if not membro:
            await interaction.response.send_message("❌ Usuário não encontrado.", ephemeral=True)
            return
        uid = str(membro.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["pix"] = self.pix.value
        db.save(guild.id, data)
        await interaction.response.send_message("✅ PIX de " + membro.mention + ": `" + self.pix.value + "`", ephemeral=True)


class ModalConfigMediadores(discord.ui.Modal, title="Configurar Mediadores"):
    qtd = discord.ui.TextInput(label="Partidas simultâneas por mediador", default="20", max_length=3)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["max_partidas_mediador"] = int(self.qtd.value or 20)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Simultâneas: " + self.qtd.value, ephemeral=True)


class ModalMoedaConfig(discord.ui.Modal, title="Configurar Moeda"):
    nome = discord.ui.TextInput(label="Nome da Moeda", default="Moedas", max_length=20)
    emoji = discord.ui.TextInput(label="Emoji", default="🪙", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["moeda_nome"] = self.nome.value
        data["config"]["moeda_emoji"] = self.emoji.value
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Moeda: " + self.emoji.value + " " + self.nome.value, ephemeral=True)


class ModalCriarCodiguin(discord.ui.Modal, title="Criar Codiguin"):
    codigo = discord.ui.TextInput(label="Código", placeholder="ex: ARENA2024", max_length=30)
    item = discord.ui.TextInput(label="Recompensa", placeholder="ex: 100 moedas", max_length=100)
    usos = discord.ui.TextInput(label="Usos máximos (0 = ilimitado)", default="1", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        if "codiguins" not in data:
            data["codiguins"] = {}
        data["codiguins"][self.codigo.value.upper()] = {
            "item": self.item.value, "usos_max": int(self.usos.value or 1), "usos_atual": 0, "ativo": True
        }
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Codiguin `" + self.codigo.value.upper() + "` criado!", ephemeral=True)


class ModalAdicionarItem(discord.ui.Modal, title="Adicionar Item"):
    nome = discord.ui.TextInput(label="Nome", max_length=40)
    descricao = discord.ui.TextInput(label="Descrição", max_length=100)
    preco = discord.ui.TextInput(label="Preço (moedas)", max_length=10)
    emoji = discord.ui.TextInput(label="Emoji", default="⚙️", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        item_id = self.nome.value.lower().replace(" ", "_")
        data["loja"][item_id] = {
            "nome": self.nome.value, "descricao": self.descricao.value,
            "preco": int(self.preco.value or 0), "emoji": self.emoji.value,
            "ativo": True, "tipo": "indefinido"
        }
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Item **" + self.emoji.value + " " + self.nome.value + "** adicionado!", ephemeral=True)


class ModalAlterarPrefixo(discord.ui.Modal, title="Alterar Prefixo"):
    prefixo = discord.ui.TextInput(label="Novo prefixo", default="!", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["prefixo"] = self.prefixo.value
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Prefixo: `" + self.prefixo.value + "`", ephemeral=True)


# ══════════════════════════════════════════════════════════
#  EMBEDS
# ══════════════════════════════════════════════════════════

def embed_central(guild):
    embed = discord.Embed(title="Central de Controle do Bot", color=0x5865F2)
    embed.description = "Configure tudo do seu bot aqui!\nSelecione, abaixo, qual central deseja acessar."
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed


def embed_jogos(data):
    config = data["config"]
    filas = data.get("filas", {})
    embed = discord.Embed(title="Jogos Geral", color=0x5865F2)
    embed.description = "Nesta seção, você pode taxa de mediação, quantidade de filas e partidas, delay e adicionar jogos.\n↳ Para configurar as modalidades, coins, filas, etc. Clique no jogo desejado."
    embed.add_field(name="Quantidade de FILAS o jogador pode aguardar", value="`" + str(config.get("max_filas_jogador", 1)) + "`", inline=False)
    embed.add_field(name="Quantidade de PARTIDAS o jogador pode jogar", value="`" + str(config.get("max_partidas_jogador", 1)) + "`", inline=False)
    embed.add_field(name="Delay Entre Uma Aposta Para Outra", value="`" + str(config.get("delay_apostas", 0)) + "`", inline=False)
    jm = " | ".join([j["nome"] + " > " + " | ".join(j.get("modalidades", {}).keys()) for j in filas.values()]) or "Nenhum"
    embed.add_field(name="Jogo | Modalidade:", value=jm, inline=False)
    return embed


def embed_filas(data):
    config = data["config"]
    tipo = config.get("tipo_criacao_fila", "categoria")
    embed = discord.Embed(title="Central de Filas", color=0x5865F2)
    embed.description = "Configure o comportamento das filas aqui!"
    embed.add_field(name="Tipo de Criação das Partidas", value="`" + tipo + "`", inline=False)
    embed.add_field(name="↳ Tópico", value="Partidas criadas em formato de thread no canal definido.", inline=False)
    embed.add_field(name="↳ Categoria", value="Partidas criadas como canais de texto em uma categoria com o nome do mediador.", inline=False)
    embed.add_field(name="↳ Mista", value="Combina tópicos e categorias.", inline=False)
    embed.add_field(name="⚠️ Importante", value="Filas já criadas não são afetadas por mudanças retroativas.", inline=False)
    return embed


def embed_valores(data):
    filas = data.get("filas", {})
    embed = discord.Embed(title="Valores Geral", color=0x5865F2)
    embed.description = "Configure tudo relacionado a valores das filas aqui!"
    todos = []
    for jogo in filas.values():
        for mod in jogo.get("modalidades", {}).values():
            for v_str in sorted(mod.get("valores", {}).keys(), key=lambda x: float(x), reverse=True):
                todos.append(v_str)
    if todos:
        embed.add_field(name="Lista de Valores Normais", value="\n".join(["R$ " + str(round(float(v), 2)) for v in sorted(set(todos), key=lambda x: float(x), reverse=True)]), inline=False)
    else:
        embed.add_field(name="Lista de Valores Normais", value="Nenhum valor configurado.", inline=False)
    return embed


def embed_mediadores(data, guild):
    config = data["config"]
    canal_id = config.get("canal_fila_mediador")
    canal = guild.get_channel(canal_id) if canal_id else None
    cargo_id = config.get("cargo_mediador")
    cargo = guild.get_role(cargo_id) if cargo_id else None
    embed = discord.Embed(title="Mediadores Geral", color=0x5865F2)
    embed.description = "Configure tudo relacionado aos Mediadores aqui!"
    pix_solo = "🟢 SIM" if config.get("mediador_pix_solo") else "🔴 NÃO"
    receita_solo = "🟢 SIM" if config.get("mediador_receita_solo") else "🔴 NÃO"
    embed.add_field(name="Mediador pode registrar pix sozinho?", value=pix_solo, inline=True)
    embed.add_field(name="Mediador pode visualizar sua própria receita?", value=receita_solo, inline=True)
    embed.add_field(name="Quantidade de Partidas Simultâneas", value="Quantidade Atual: **" + str(config.get("max_partidas_mediador", 20)) + "**\n↳ Representa quantas filas cada mediador vai conseguir pegar simultâneas\n↳ Ao setar uma nova quantidade, vai atualizar para TODOS os mediadores.", inline=False)
    embed.add_field(name="Painel Fila Mediadores", value=canal.mention if canal else "#fila-mediador (não configurado)", inline=False)
    embed.add_field(name="Cargo Mediador Geral", value=cargo.mention if cargo else "Não configurado", inline=False)
    embed.add_field(name="Tipo de DISTRIBUIÇÃO das partidas para os mentores", value=config.get("distribuicao_mediador", "Equilibrado").title() + "\n\n↳ O modo **Equilibrado** foca em mediadores com menos partidas ABERTAS até que todos tenham a mesma quantidade.\n↳ O modo **1por1** distribui as filas UMA por vez para cada mediador na fila.", inline=False)
    return embed


def embed_moedas(data):
    config = data["config"]
    total = sum(j.get("moedas", 0) for j in data.get("jogadores", {}).values())
    embed = discord.Embed(title="Moedas", color=0x5865F2)
    embed.description = "Configure tudo relacionado a Moedas aqui!"
    embed.add_field(name="Nome da Moeda", value=config.get("moeda_nome", "Moedas"), inline=True)
    embed.add_field(name="Quantidade de Moedas em Circulação", value=str(total), inline=True)
    return embed


def embed_ranking(data, guild):
    config = data["config"]
    canal_id = config.get("canal_ranking")
    canal = guild.get_channel(canal_id) if canal_id else None
    embed = discord.Embed(title="Perfil e Ranking", color=0x5865F2)
    embed.description = "Configure tudo relacionado ao Perfil e Ranking aqui!"
    embed.add_field(name="Data do Último Reset", value=config.get("ultimo_reset_rank", "Nunca resetado"), inline=False)
    embed.add_field(name="Tipo do Ranking", value=config.get("tipo_ranking", "Vitórias/Derrotas"), inline=False)
    embed.add_field(name="Painel de Perfil e Ranking", value=canal.mention if canal else "Não configurado\n↳ Use /ranking-painel no canal desejado", inline=False)
    embed.add_field(name="Períodos do Ranking", value=config.get("periodo_ranking", "Nenhum"), inline=False)
    return embed


def embed_destaque(data):
    config = data["config"]
    embed = discord.Embed(title="Destaque Automático", color=0x5865F2)
    embed.description = "Configure o envio automático de rankings. O bot enviará o **Top 10** jogadores com mais vitórias no canal configurado."
    diario = "🟢 Ativado" if config.get("destaque_diario_ativo") else "🔴 Desativado"
    semanal = "🟢 Ativado" if config.get("destaque_semanal_ativo") else "🔴 Desativado"
    mensal = "🟢 Ativado" if config.get("destaque_mensal_ativo") else "🔴 Desativado"
    canal_d = config.get("canal_destaque_diario")
    canal_s = config.get("canal_destaque_semanal")
    canal_m = config.get("canal_destaque_mensal")
    embed.add_field(name="Destaque Diário", value=diario, inline=True)
    embed.add_field(name="Canal Diário", value="Não configurado." if not canal_d else "<#" + str(canal_d) + ">", inline=True)
    embed.add_field(name="Destaque Semanal", value=semanal, inline=True)
    embed.add_field(name="Canal Semanal", value="Não configurado." if not canal_s else "<#" + str(canal_s) + ">", inline=True)
    embed.add_field(name="Destaque Mensal", value=mensal, inline=True)
    embed.add_field(name="Canal Mensal", value="Não configurado." if not canal_m else "<#" + str(canal_m) + ">", inline=True)
    return embed


def embed_prefixo(data):
    config = data["config"]
    embed = discord.Embed(title="Central Comandos Prefixos", color=0x5865F2)
    embed.description = "Configure tudo relacionado aos Comandos por Prefixos aqui!\n\n↳ Por padrão, o prefixo é \"+\".\n↳ Se não houver canais selecionados, os comandos serão liberados em qualquer lugar.\n↳ Administradores podem usar em qualquer lugar independente."
    embed.add_field(name="Prefixo", value="`" + config.get("prefixo", "!") + "`", inline=True)
    embed.add_field(name="Jogadores podem usar o comando +p", value="🟢 SIM" if config.get("cmd_p_jogadores", True) else "🔴 NÃO", inline=True)
    return embed


def embed_blacklist(data, guild):
    config = data["config"]
    blist = data.get("blacklist", [])
    embed = discord.Embed(title="Black List", color=0x5865F2)
    embed.description = "Configure tudo relacionado a BlackList aqui!"
    pode_entrar = "🟢 SIM" if config.get("blacklist_pode_entrar_fila", False) else "🔴 NÃO"
    embed.add_field(name="Jogador na BlackList pode entrar na fila?", value=pode_entrar, inline=False)
    canal_id = config.get("canal_blacklist")
    canal = guild.get_channel(canal_id) if canal_id else None
    embed.add_field(name="Canal no qual os jogadores vão consultar", value=canal.mention if canal else "Não setado.", inline=False)
    embed.add_field(name="Cargo(s) que vão poder remover/adicionar BlackList", value=str(len(blist)) + " na blacklist", inline=False)
    return embed


def embed_permissoes(data):
    config = data["config"]
    perms = config.get("permissoes", {})
    embed = discord.Embed(title="Central de Permissões do Bot", color=0x5865F2)
    embed.description = "Configure tudo relacionado a permissões do Bot aqui!"
    lista = [
        ("Visualizar Apostas (+apostas)", "perm_apostas"),
        ("Visualizar BOs", "perm_bos"),
        ("Visualizar Eventos (+evento)", "perm_eventos"),
        ("Visualizar Logs (+logs)", "perm_logs"),
        ("Gerenciar Apostas", "perm_gerenciar"),
        ("Gerenciar Vitória/Derrota", "perm_vitoria"),
        ("Gerenciar Mediadores", "perm_mediadores"),
        ("Gerenciar Moedas", "perm_moedas"),
        ("Usar Comandos em todos lugares", "perm_todos"),
        ("Usar o Comando GP", "perm_gp"),
        ("Gerenciar Items", "perm_itens"),
    ]
    for nome, chave in lista:
        embed.add_field(name=nome, value=perms.get(chave, "*(Nenhum cargo configurado)*"), inline=False)
    return embed


def embed_logs(data, guild):
    config = data["config"]
    embed = discord.Embed(title="Central de Logs", color=0x5865F2)
    embed.description = "Configure tudo relacionado a Logs aqui!"
    logs = [
        ("Partidas Criadas", "log_partidas_criadas"),
        ("Partidas Concluídas", "log_partidas_concluidas"),
        ("Partidas Canceladas", "log_partidas_canceladas"),
        ("Partidas Encerradas", "log_partidas_encerradas"),
        ("Partidas Logs TXT", "log_partidas_txt"),
        ("Partidas Logs Transcript", "log_partidas_transcript"),
        ("Mediador Fila Status", "log_mediador_fila"),
        ("Mediador Receita", "log_mediador_receita"),
        ("Mediador Receita Reset", "log_mediador_receita_reset"),
        ("Moedas Transações", "log_moedas"),
        ("Loja Compras", "log_loja_compras"),
        ("Loja Resgates", "log_loja_resgates"),
        ("SS/Analista Logs", "log_ss"),
        ("Rate Limit Avisos", "log_rate_limit"),
    ]
    for nome, chave in logs:
        canal_id = config.get(chave)
        canal = guild.get_channel(canal_id) if canal_id else None
        embed.add_field(name=nome, value=canal.mention if canal else "*(Nenhum canal configurado)*", inline=False)
    return embed


# ══════════════════════════════════════════════════════════
#  VIEWS
# ══════════════════════════════════════════════════════════

class ViewCentral(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectCentralGeral())
        self.add_item(SelectPersonalizacoes())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectCentralGeral(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Centrais Gerais do Bot", options=[
            discord.SelectOption(label="Jogos", description="Configure taxa, modalidades, etc.", emoji="🎮", value="jogos"),
            discord.SelectOption(label="Filas", description="Configure tipo de criação para tópico ou categoria.", emoji="📋", value="filas"),
            discord.SelectOption(label="Valores das Filas", description="Configure os valores das filas.", emoji="💰", value="valores"),
            discord.SelectOption(label="Mediador", description="Configure o pix, cargo, fila e modo de distribuição.", emoji="🛡️", value="mediador"),
            discord.SelectOption(label="Eventos", description="Configure eventos de vitórias.", emoji="🎉", value="eventos"),
            discord.SelectOption(label="Streamers", description="Configure fila de influencer.", emoji="🎙️", value="streamers"),
            discord.SelectOption(label="Item", description="Configure os itens das lojas ou caixas.", emoji="📦", value="itens"),
            discord.SelectOption(label="Loja", description="Configure as Lojas e seus painéis.", emoji="🛒", value="loja"),
            discord.SelectOption(label="Caixas Misteriosas", description="Configure o sistema de caixas.", emoji="🎁", value="caixas"),
            discord.SelectOption(label="Roleta", description="Configure o sistema de roleta.", emoji="🎰", value="roleta"),
            discord.SelectOption(label="Codiguin", description="Configure os Condiguins com itens para serem resgatados.", emoji="🎟️", value="codiguin"),
            discord.SelectOption(label="Moeda/Coin", description="Configure e reset a Moeda/Coin do bot.", emoji="🪙", value="moeda"),
            discord.SelectOption(label="Perfil e Ranking", description="Adicione o painel para consultar o perfil ou ranking dos jogadores.", emoji="🏆", value="ranking"),
            discord.SelectOption(label="Destaque Ranking Automático", description="Configure o destaque automático de ranking diário, semanal e mensal.", emoji="📊", value="destaque"),
            discord.SelectOption(label="Comandos Prefixo", description="Configure o prefixo do bot e/ou canais permitidos.", emoji="ℹ️", value="prefixo"),
            discord.SelectOption(label="SS/Analista", description="Configure o sistema de chamar SS/Analista para as partidas.", emoji="🔊", value="ss"),
            discord.SelectOption(label="BlackList", description="Configure os cargos e o painel de consulta.", emoji="🚫", value="blacklist"),
            discord.SelectOption(label="Permissões", description="Configure quais cargos tem acesso.", emoji="🔑", value="permissoes"),
            discord.SelectOption(label="Logs", description="Sete os canais de logs.", emoji="📝", value="logs"),
            discord.SelectOption(label="Bot", description="Configure o Bot.", emoji="⚙️", value="bot"),
        ], row=0)

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
        elif v == "moeda":
            await interaction.response.edit_message(embed=embed_moedas(data), view=ViewMoeda())
        elif v == "ranking":
            await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())
        elif v == "destaque":
            await interaction.response.edit_message(embed=embed_destaque(data), view=ViewDestaque())
        elif v == "prefixo":
            await interaction.response.edit_message(embed=embed_prefixo(data), view=ViewPrefixo())
        elif v == "blacklist":
            await interaction.response.edit_message(embed=embed_blacklist(data, interaction.guild), view=ViewBlacklist())
        elif v == "permissoes":
            await interaction.response.edit_message(embed=embed_permissoes(data), view=ViewPermissoes())
        elif v == "logs":
            await interaction.response.edit_message(embed=embed_logs(data, interaction.guild), view=ViewLogs())
        elif v == "codiguin":
            codiguins = data.get("codiguins", {})
            embed = discord.Embed(title="Central - Codiguins", color=0x5865F2)
            embed.description = "\n".join(["`" + k + "` → " + val["item"] + " (" + str(val["usos_atual"]) + "/" + str(val["usos_max"]) + " usos)" for k, val in codiguins.items()]) if codiguins else "Nenhum codiguin criado ainda. Clique em **Criar Novo Codiguin** para começar."
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            await interaction.response.edit_message(embed=embed, view=ViewCodiguin(codiguins))
        elif v == "itens":
            itens = data.get("loja", {})
            embed = discord.Embed(title="Itens Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado a Itens aqui!"
            if itens:
                embed.add_field(name="Itens (mais recentes primeiro)", value="\n".join([i.get("emoji","⚙️") + " " + i["nome"] + " (" + i.get("tipo","indefinido") + ") | " + str(i.get("preco",0)) for i in itens.values()]), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewItens(itens))
        elif v == "loja":
            embed = discord.Embed(title="Loja Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado à Loja aqui!"
            config = data["config"]
            embed.add_field(name="Delay Entre Uma Compra Para Outra", value=str(config.get("delay_loja", 0)) + " minuto(s)", inline=False)
            canal_id = config.get("canal_aviso_compra")
            canal = interaction.guild.get_channel(canal_id) if canal_id else None
            embed.add_field(name="Canal Aviso de Compra", value=(canal.mention if canal else "#desconhecido") + "\n\n↳ O canal \"aviso de compra\" é onde o bot avisará quando um usuário resgatar um item da loja. Você pode personalizar na Central de Embeds.", inline=False)
            lojas = data.get("lojas", {})
            if lojas:
                loja_txt = "\n".join([l.get("nome","Loja") + " | " + str(len(l.get("itens",[]))) + " itens" for l in lojas.values()])
            else:
                loja_txt = "LOJINHA DA ARENA | Nenhum item."
            embed.add_field(name="Loja | Item", value=loja_txt, inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewLoja(lojas))
        elif v == "ss":
            embed = discord.Embed(title="Central de SS/Analista", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos SS/Analistas."
            config = data["config"]
            embed.add_field(name="Limite SS por Analista", value=str(config.get("limite_ss", 1)), inline=True)
            embed.add_field(name="Calls Privadas", value="🟢 SIM" if config.get("calls_privadas") else "🔴 NÃO", inline=True)
            await interaction.response.edit_message(embed=embed, view=ViewSS())
        elif v == "eventos":
            data2 = db.load(interaction.guild.id)
            config2 = data2["config"]
            embed = discord.Embed(title="Evento Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos Eventos aqui!"
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="Quantidade de eventos:", value=str(len(data2.get("eventos", []))), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))

        elif v == "streamers":
            data2 = db.load(interaction.guild.id)
            config2 = data2["config"]
            embed = discord.Embed(title="Streamers Geral", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos streamers aqui!"
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            pix_med = "✅" if config2.get("streamer_med_solo") else "❌"
            fila_sep = "✅" if config2.get("streamer_fila_sep") else "❌"
            embed.add_field(name="Streamer pode selecionar mediador(es) da org?", value=pix_med + "\n\n\u21b3 O streamer pode escolher mediador(es) exclusivo(s) da org para mediar somente para ele.", inline=False)

            embed.add_field(name="Fila Separada Para Mediadores?", value=fila_sep, inline=False)
            cat_id = config2.get("streamer_categoria_id")
            cat = interaction.guild.get_channel(cat_id) if cat_id else None
            embed.add_field(name="Categoria", value=cat.mention if cat else "#🔴 LIVE ON\n\n↳ Categoria em que os canais de texto das filas contra influencers vão ser criados.", inline=False)
            cargo_str_id = config2.get("cargo_streamer")
            cargo_str = interaction.guild.get_role(cargo_str_id) if cargo_str_id else None
            embed.add_field(name="Cargo Streamer", value=cargo_str.mention if cargo_str else "Não configurado", inline=False)
            canal_painel_id = config2.get("canal_streamer_painel")
            canal_liveon_id = config2.get("canal_streamer_liveon")
            canal_painel = interaction.guild.get_channel(canal_painel_id) if canal_painel_id else None
            canal_liveon = interaction.guild.get_channel(canal_liveon_id) if canal_liveon_id else None
            embed.add_field(name="Canal Painel", value=(canal_painel.mention if canal_painel else "#desconhecido") + "\n\n\u21b3 Canal de texto onde o painel do streamer sera enviado.", inline=False)
            embed.add_field(name="Canal Live On", value=(canal_liveon.mention if canal_liveon else "#desconhecido") + "\n\n\u21b3 Canal de texto onde os alertas de LiveON serao enviados.", inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewStreamers())

        elif v == "caixas":
            data2 = db.load(interaction.guild.id)
            config2 = data2["config"]
            embed = discord.Embed(title="Caixas", color=0x5865F2)
            embed.description = "Configure tudo relacionado às Caixas aqui! Para configurar/criar as caixas, volte e selecione a central de **Item**."
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            canal_caixa_id = config2.get("canal_caixa")
            canal_aviso_caixa_id = config2.get("canal_aviso_caixa")
            canal_caixa = interaction.guild.get_channel(canal_caixa_id) if canal_caixa_id else None
            canal_aviso_caixa = interaction.guild.get_channel(canal_aviso_caixa_id) if canal_aviso_caixa_id else None
            embed.add_field(name="Canais", value="Canal de Texto: " + (canal_caixa.mention if canal_caixa else "#desconhecido") + "\nCanal de Aviso: " + (canal_aviso_caixa.mention if canal_aviso_caixa else "#desconhecido"), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewCaixas())

        elif v == "roleta":
            data2 = db.load(interaction.guild.id)
            config2 = data2["config"]
            embed = discord.Embed(title="Roletas", color=0x5865F2)
            embed.description = "Configure tudo relacionado às Roletas aqui! Para configurar/criar as roletas, volte e selecione a central de **Item**."
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            canal_rol_id = config2.get("canal_roleta")
            canal_aviso_rol_id = config2.get("canal_aviso_roleta")
            canal_rol = interaction.guild.get_channel(canal_rol_id) if canal_rol_id else None
            canal_aviso_rol = interaction.guild.get_channel(canal_aviso_rol_id) if canal_aviso_rol_id else None
            embed.add_field(name="Canais", value="Canal de Texto: " + (canal_rol.mention if canal_rol else "Nenhum canal selecionado") + "\nCanal de Aviso: " + (canal_aviso_rol.mention if canal_aviso_rol else "Nenhum canal selecionado"), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewRoleta())

        elif v == "bot":
            data2 = db.load(interaction.guild.id)
            config2 = data2["config"]
            embed = discord.Embed(title="Configurações do Bot", color=0x5865F2)
            embed.description = "Selecione abaixo o que deseja configurar no bot."
            nome_org = config2.get("nome_org", "ARENA X1")
            embed.add_field(name=nome_org, value="\u200b", inline=False)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            await interaction.response.edit_message(embed=embed, view=ViewBot())


class SelectPersonalizacoes(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Central de Personalizações", options=[
            discord.SelectOption(label="Componentes", description="Configure/personalize os botões e selects do bot.", emoji="🟢", value="componentes"),
            discord.SelectOption(label="Embeds Padrão", description="Altere embeds fixas do bot.", emoji="📋", value="embeds"),
            discord.SelectOption(label="Embeds Auxiliares", description="Configure embeds extras do bot.", emoji="📋", value="embeds_aux"),
            discord.SelectOption(label="Mensagens Auxiliares", description="Altere mensagens enviadas.", emoji="📋", value="msgs"),
            discord.SelectOption(label="Nome dos Canais das Partidas", description="Altere os nomes dos canais criados.", emoji="📋", value="canais"),
            discord.SelectOption(label="QrCode [Mediadores]", description="Personalize o QrCode de pagamento dos mediadores.", emoji="📱", value="qrcode"),
            discord.SelectOption(label="Textos Auxiliares", description="Altere alguns textos fixos.", emoji="📋", value="textos"),
        ], row=1)

    async def callback(self, interaction):
        embed = discord.Embed(title=self.values[0].title(), color=0x5865F2)
        embed.description = "Em breve totalmente configurável pelo Discord!"
        await interaction.response.edit_message(embed=embed, view=ViewVoltar())


# ══════════════════════════════════════════════════════════
#  VIEWS DOS MÓDULOS
# ══════════════════════════════════════════════════════════

class ViewVoltar(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── JOGOS ─────────────────────────────────────────────────

class ViewJogos(discord.ui.View):
    def __init__(self, filas):
        super().__init__(timeout=300)
        opcoes = [discord.SelectOption(label="Selecione para configurar", value="none")]
        for jogo_id, jogo in filas.items():
            opcoes.append(discord.SelectOption(label=jogo["nome"], description=str(len(jogo.get("modalidades",{}))) + " modalidades", value="j_" + jogo_id))
        sel = discord.ui.Select(placeholder="Selecione para configurar", options=opcoes[:25], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        jogo_id = v[2:]
        data = db.load(interaction.guild.id)
        jogo = data["filas"].get(jogo_id, {})
        await mostrar_jogo(interaction, jogo_id, jogo)

    @discord.ui.button(label="Configurar", style=discord.ButtonStyle.blurple, row=1)
    async def config(self, interaction, button):
        await interaction.response.send_modal(ModalJogosGeral())

    @discord.ui.button(label="Adicionar Jogo", style=discord.ButtonStyle.green, row=1)
    async def add(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarJogo())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


async def mostrar_jogo(interaction, jogo_id, jogo):
    modalidades = jogo.get("modalidades", {})
    embed = discord.Embed(title="Jogos - " + jogo.get("nome", "").upper(), color=0x5865F2)
    embed.description = jogo.get("descricao", "")
    embed.add_field(name="Modalidades", value=" | ".join(modalidades.keys()) or "Nenhuma", inline=False)
    embed.add_field(name="Custo Adicional", value="R$ " + str(round(jogo.get("custo_adicional", 0), 2)), inline=True)
    embed.add_field(name="Taxa Mediação", value=str(jogo.get("taxa_mediacao", 0)) + "%", inline=True)
    embed.add_field(name="Moedas Auto", value="Por Partida: " + str(jogo.get("moedas_por_partida", 1)) + "\nPor Revanche: " + str(jogo.get("moedas_por_revanche", 1)), inline=False)
    canal_thread_id = jogo.get("thread_canal_id")
    canal_thread = interaction.guild.get_channel(canal_thread_id) if canal_thread_id else None
    embed.add_field(name="Thread das Partidas", value=canal_thread.mention if canal_thread else "Não configurado", inline=False)
    cargo_id = jogo.get("cargo_adicional")
    cargo = interaction.guild.get_role(cargo_id) if cargo_id else None
    embed.add_field(name="Cargo Adicional", value=cargo.mention if cargo else "Nenhum", inline=False)
    await interaction.response.edit_message(embed=embed, view=ViewJogoDetalhe(jogo_id, jogo))


class ViewJogoDetalhe(discord.ui.View):
    def __init__(self, jogo_id, jogo):
        super().__init__(timeout=300)
        self.jogo_id = jogo_id
        self.jogo = jogo
        modalidades = jogo.get("modalidades", {})
        if modalidades:
            opcoes = [discord.SelectOption(label="Configurar Modalidade Individual.", value="none")]
            for mod_id, mod in modalidades.items():
                opcoes.append(discord.SelectOption(label=mod["nome"] + " (" + str(len(mod.get("valores", {}))) + " valores)", value="m_" + mod_id))
            sel = discord.ui.Select(placeholder="Configurar Modalidade Individual.", options=opcoes[:25], row=0)
            sel.callback = self._sel_mod
            self.add_item(sel)
        # Thread select
        tsel = discord.ui.ChannelSelect(placeholder="suas-partidas-aq", channel_types=[discord.ChannelType.text], row=1)
        tsel.callback = self._set_thread
        self.add_item(tsel)
        # Cargo select
        rsel = discord.ui.RoleSelect(placeholder="Cargo Adicional", row=2)
        rsel.callback = self._set_cargo
        self.add_item(rsel)

    async def _sel_mod(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        mod_id = v[2:]
        data = db.load(interaction.guild.id)
        mod = data["filas"][self.jogo_id]["modalidades"].get(mod_id, {})
        await mostrar_modalidade(interaction, self.jogo_id, mod_id, mod)

    async def _set_thread(self, interaction):
        canal = interaction.data["values"][0]
        canal_id = int(canal) if isinstance(canal, str) else canal.id
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["thread_canal_id"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Thread das partidas configurada!", ephemeral=True)

    async def _set_cargo(self, interaction):
        cargo = interaction.data["values"][0]
        cargo_id = int(cargo) if isinstance(cargo, str) else cargo.id
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["cargo_adicional"] = cargo_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Cargo adicional configurado!", ephemeral=True)

    @discord.ui.button(label="⚙️ Custo", style=discord.ButtonStyle.grey, row=3)
    async def custo(self, interaction, button):
        await interaction.response.send_modal(ModalEditarCusto(self.jogo_id))

    @discord.ui.button(label="⚙️ Taxa", style=discord.ButtonStyle.grey, row=3)
    async def taxa(self, interaction, button):
        await interaction.response.send_modal(ModalEditarTaxa(self.jogo_id))

    @discord.ui.button(label="⚙️ Moedas", style=discord.ButtonStyle.grey, row=3)
    async def moedas(self, interaction, button):
        await interaction.response.send_modal(ModalEditarMoedas(self.jogo_id))

    @discord.ui.button(label="➕ Modalidade", style=discord.ButtonStyle.green, row=4)
    async def add_mod(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarModalidade(self.jogo_id))

    @discord.ui.button(label="✏️ Editar", style=discord.ButtonStyle.blurple, row=4)
    async def editar(self, interaction, button):
        await interaction.response.send_modal(ModalEditarJogo(self.jogo_id, self.jogo))

    @discord.ui.button(label="🗑️ Excluir", style=discord.ButtonStyle.red, row=4)
    async def excluir(self, interaction, button):
        data = db.load(interaction.guild.id)
        del data["filas"][self.jogo_id]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_jogos(data), view=ViewJogos(data.get("filas", {})))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        await interaction.response.edit_message(embed=embed_jogos(data), view=ViewJogos(data.get("filas", {})))


async def mostrar_modalidade(interaction, jogo_id, mod_id, mod):
    valores = mod.get("valores", {})
    canal_id = mod.get("canal_id")
    canal = interaction.guild.get_channel(canal_id) if canal_id else None
    vals = " | ".join([str(int(float(v)) if float(v).is_integer() else float(v)) for v in sorted(valores.keys(), key=lambda x: float(x), reverse=True)]) or "Nenhum"
    embed = discord.Embed(title="Jogos > " + jogo_id.upper() + " > " + mod["nome"], description="Partidas " + mod["nome"], color=0x5865F2)
    embed.add_field(name="Filas", value=vals, inline=False)
    embed.add_field(name="Canal das Filas", value=canal.mention if canal else "**Não configurado**", inline=False)
    await interaction.response.edit_message(embed=embed, view=ViewModalidade(jogo_id, mod_id, mod))


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
                taxa = "R$" + str(v_data.get("taxa_fixo", 0)) if tipo == "fixo" else str(v_data.get("taxa_pct", 10)) + "%"
                opcoes.append(discord.SelectOption(label="R$ " + str(round(float(v_str), 2)) + " — taxa: " + taxa, value="v_" + v_str))
            sel = discord.ui.Select(placeholder="Selecione a Fila Para Personalizar", options=opcoes[:25], row=0)
            sel.callback = self._sel_valor
            self.add_item(sel)
        # Canal das filas
        csel = discord.ui.ChannelSelect(placeholder="Canal das Filas", channel_types=[discord.ChannelType.text], row=1)
        csel.callback = self._set_canal
        self.add_item(csel)

    async def _sel_valor(self, interaction):
        v = interaction.data["values"][0]
        if v == "none":
            await interaction.response.defer()
            return
        v_str = v[2:]
        data = db.load(interaction.guild.id)
        v_data = data["filas"][self.jogo_id]["modalidades"][self.mod_id]["valores"].get(v_str, {})
        tipo = v_data.get("tipo_taxa", "pct")
        taxa = "R$ " + str(v_data.get("taxa_fixo", 0)) + " fixo" if tipo == "fixo" else str(v_data.get("taxa_pct", 10)) + "%"
        embed = discord.Embed(title="Valores Geral > R$ " + str(round(float(v_str), 2)), color=0x5865F2)
        embed.description = "↳ A Variações de Valores é quando você deseja adicionar mais de um valor para a mesma fila.\n↳ Quando os jogadores confirmarem a partida, eles poderão escolher entre os valores disponíveis."
        embed.add_field(name="Valor", value="R$ " + str(round(float(v_str), 2)), inline=True)
        embed.add_field(name="Taxa Mediação Individual", value=taxa, inline=True)
        await interaction.response.edit_message(embed=embed, view=ViewGerenciarValor(self.jogo_id, self.mod_id, v_str, v_data))

    async def _set_canal(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        canal_real = interaction.guild.get_channel(canal_id)
        data = db.load(interaction.guild.id)
        data["filas"][self.jogo_id]["modalidades"][self.mod_id]["canal_id"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal das filas: " + (canal_real.mention if canal_real else str(canal_id)), ephemeral=True)
        # Gera filas automaticamente
        if canal_real:
            from cogs.filas import regenerar_filas_canal
            valores = data["filas"][self.jogo_id]["modalidades"][self.mod_id].get("valores", {})
            if valores:
                await regenerar_filas_canal(interaction.guild, canal_real, self.jogo_id, self.mod_id, valores)

    @discord.ui.button(label="➕ Adicionar Valor", style=discord.ButtonStyle.green, row=2)
    async def add_val(self, interaction, button):
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
            discord.SelectOption(label="Editar Taxa Mediação Individual", description="Clique aqui para editar a taxa de mediação individual deste valor.", emoji="⚙️", value="editar_taxa"),
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


# ── FILAS ─────────────────────────────────────────────────

class ViewFilas(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectTipoCriacao())

    @discord.ui.button(label="Excluir Categorias Mediadores", style=discord.ButtonStyle.blurple, row=1)
    async def excluir(self, interaction, button):
        await interaction.response.send_message("✅ Categorias excluídas na próxima regeneração.", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectTipoCriacao(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o tipo de CRIAÇÃO das partidas.", options=[
            discord.SelectOption(label="Categoria", description="Canal de texto em categoria por mediador", value="categoria"),
            discord.SelectOption(label="Tópico", description="Tópico no canal de tópicos configurado", value="topico"),
            discord.SelectOption(label="Mista", description="Combina tópico e categoria", value="mista"),
        ], row=0)

    async def callback(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["tipo_criacao_fila"] = self.values[0]
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_filas(data), view=ViewFilas())


# ── VALORES ───────────────────────────────────────────────

class ViewValores(discord.ui.View):
    def __init__(self, filas):
        super().__init__(timeout=300)
        opcoes = [discord.SelectOption(label="Configurar Valor Individual", value="none")]
        for jogo_id, jogo in filas.items():
            for mod_id, mod in jogo.get("modalidades", {}).items():
                opcoes.append(discord.SelectOption(label=jogo["nome"] + " > " + mod["nome"], value=jogo_id + "|" + mod_id))
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
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── MEDIADORES ────────────────────────────────────────────

class ViewMediadores(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectAcoesMediador())

    @discord.ui.button(label="Registrar Pix", style=discord.ButtonStyle.red, row=1)
    async def reg_pix(self, interaction, button):
        await interaction.response.send_modal(ModalMediadorPIX())

    @discord.ui.button(label="Alterar Quantidade", style=discord.ButtonStyle.grey, row=1)
    async def alt_qtd(self, interaction, button):
        await interaction.response.send_modal(ModalConfigMediadores())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectAcoesMediador(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o que deseja configurar...", options=[
            discord.SelectOption(label="Canal Painel Fila Mediadores", description="Selecione o canal da fila de mediadores", value="canal"),
            discord.SelectOption(label="Cargo Mediador Geral", description="Selecione o cargo de mediador", value="cargo"),
            discord.SelectOption(label="Distribuição: Equilibrado", description="Mediador com menos partidas recebe primeiro", value="dist_equilibrado"),
            discord.SelectOption(label="Distribuição: 1por1", description="Distribui uma fila por vez em ordem", value="dist_1por1"),
            discord.SelectOption(label="PIX Solo: LIGAR/DESLIGAR", description="Mediador pode registrar próprio PIX", value="pix_toggle"),
            discord.SelectOption(label="Receita Solo: LIGAR/DESLIGAR", description="Mediador pode ver própria receita", value="receita_toggle"),
            discord.SelectOption(label="Ver Lista da Fila", description="Ver mediadores na fila agora", value="lista"),
        ], row=0)

    async def callback(self, interaction):
        v = self.values[0]
        data = db.load(interaction.guild.id)

        if v == "canal":
            await interaction.response.edit_message(
                embed=discord.Embed(title="Selecione o Canal da Fila de Mediadores", color=0x5865F2),
                view=ViewSelecionarCanalMed()
            )
        elif v == "cargo":
            await interaction.response.edit_message(
                embed=discord.Embed(title="Selecione o Cargo de Mediador", color=0x5865F2),
                view=ViewSelecionarCargoMed()
            )
        elif v.startswith("dist_"):
            tipo = v[5:]
            data["config"]["distribuicao_mediador"] = tipo
            db.save(interaction.guild.id, data)
            await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())
        elif v == "pix_toggle":
            atual = data["config"].get("mediador_pix_solo", False)
            data["config"]["mediador_pix_solo"] = not atual
            db.save(interaction.guild.id, data)
            await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())
        elif v == "receita_toggle":
            atual = data["config"].get("mediador_receita_solo", False)
            data["config"]["mediador_receita_solo"] = not atual
            db.save(interaction.guild.id, data)
            await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())
        elif v == "lista":
            fila = data.get("fila_mediadores", [])
            linhas = []
            for i, uid in enumerate(fila, 1):
                m = interaction.guild.get_member(uid)
                pix = data["jogadores"].get(str(uid), {}).get("pix", "Sem PIX")
                linhas.append("`" + str(i) + ".` " + (m.mention if m else str(uid)) + " — PIX: `" + pix + "`")
            await interaction.response.send_message("**🛡️ Fila de Mediadores:**\n" + ("\n".join(linhas) if linhas else "Nenhum na fila."), ephemeral=True)


class ViewSelecionarCanalMed(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.ChannelSelect(placeholder="Selecione o canal da fila de mediadores", channel_types=[discord.ChannelType.text], row=0)
        sel.callback = self._set
        self.add_item(sel)

    async def _set(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        canal_real = interaction.guild.get_channel(canal_id)
        data = db.load(interaction.guild.id)
        data["config"]["canal_fila_mediador"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())
        # Posta painel automaticamente
        if canal_real:
            from cogs.mediadores import postar_painel_mediador
            await postar_painel_mediador(canal_real, interaction.guild, data)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())


class ViewSelecionarCargoMed(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.RoleSelect(placeholder="Selecione o cargo de mediador", row=0)
        sel.callback = self._set
        self.add_item(sel)

    async def _set(self, interaction):
        cargo_obj = interaction.data["values"][0]
        cargo_id = int(cargo_obj) if isinstance(cargo_obj, str) else cargo_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["cargo_mediador"] = cargo_id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        await interaction.response.edit_message(embed=embed_mediadores(data, interaction.guild), view=ViewMediadores())


# ── MOEDA ─────────────────────────────────────────────────

class ViewMoeda(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Configurar Geral", style=discord.ButtonStyle.blurple, row=0)
    async def config(self, interaction, button):
        await interaction.response.send_modal(ModalMoedaConfig())

    @discord.ui.button(label="Resetar Moedas Geral", style=discord.ButtonStyle.red, row=0)
    async def reset(self, interaction, button):
        data = db.load(interaction.guild.id)
        for uid in data["jogadores"]:
            data["jogadores"][uid]["moedas"] = 0
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_moedas(data), view=ViewMoeda())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=0)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── RANKING ───────────────────────────────────────────────

class ViewRanking(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectAcoesRanking())

    @discord.ui.button(label="Resetar Rank", style=discord.ButtonStyle.red, row=1)
    async def reset(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["ranking"] = {"geral": {}, "diario": {}, "semanal": {}, "mensal": {}}
        data["config"]["ultimo_reset_rank"] = datetime.now().strftime("%d de %B de %Y às %H:%M")
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())

    @discord.ui.button(label="Tipo: Vitórias/Derrotas", style=discord.ButtonStyle.blurple, row=1)
    async def tipo_btn(self, interaction, button):
        data = db.load(interaction.guild.id)
        tipos = ["Vitórias/Derrotas", "Vitórias", "Derrotas"]
        atual = data["config"].get("tipo_ranking", "Vitórias/Derrotas")
        idx = tipos.index(atual) if atual in tipos else 0
        novo = tipos[(idx + 1) % len(tipos)]
        data["config"]["tipo_ranking"] = novo
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectAcoesRanking(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione o canal para enviar o painel", options=[
            discord.SelectOption(label="Definir Canal do Painel", description="Selecione onde o ranking ficará fixo", value="canal"),
            discord.SelectOption(label="Período: Hoje", value="per_hoje", emoji="📅"),
            discord.SelectOption(label="Período: Esta Semana", value="per_semana", emoji="📅"),
            discord.SelectOption(label="Período: Este Mês", value="per_mes", emoji="📅"),
            discord.SelectOption(label="Período: Geral", value="per_geral", emoji="🏆"),
        ], row=0)

    async def callback(self, interaction):
        v = self.values[0]
        data = db.load(interaction.guild.id)
        if v == "canal":
            await interaction.response.edit_message(
                embed=discord.Embed(title="Selecione o Canal do Painel de Ranking", color=0x5865F2),
                view=ViewSelecionarCanalRanking()
            )
        elif v.startswith("per_"):
            mapa = {"per_hoje": "hoje", "per_semana": "semana", "per_mes": "mes", "per_geral": "geral"}
            data["config"]["periodo_ranking"] = mapa[v]
            db.save(interaction.guild.id, data)
            await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())


class ViewSelecionarCanalRanking(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.ChannelSelect(placeholder="Selecione o canal para enviar o painel", channel_types=[discord.ChannelType.text], row=0)
        sel.callback = self._set
        self.add_item(sel)

    async def _set(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_ranking"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        await interaction.response.edit_message(embed=embed_ranking(data, interaction.guild), view=ViewRanking())


# ── DESTAQUE ──────────────────────────────────────────────

class ViewDestaque(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectCanalDestaque("diario", "Canal do Destaque Diário", 0))
        self.add_item(SelectCanalDestaque("semanal", "Canal do Destaque Semanal", 1))
        self.add_item(SelectCanalDestaque("mensal", "Canal do Destaque Mensal", 2))

    @discord.ui.button(label="Diário: Desativado", style=discord.ButtonStyle.grey, row=3)
    async def toggle_diario(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["config"]["destaque_diario_ativo"] = not data["config"].get("destaque_diario_ativo", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_destaque(data), view=ViewDestaque())

    @discord.ui.button(label="Semanal: Desativado", style=discord.ButtonStyle.grey, row=3)
    async def toggle_semanal(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["config"]["destaque_semanal_ativo"] = not data["config"].get("destaque_semanal_ativo", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_destaque(data), view=ViewDestaque())

    @discord.ui.button(label="Mensal: Desativado", style=discord.ButtonStyle.grey, row=4)
    async def toggle_mensal(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["config"]["destaque_mensal_ativo"] = not data["config"].get("destaque_mensal_ativo", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_destaque(data), view=ViewDestaque())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectCanalDestaque(discord.ui.ChannelSelect):
    def __init__(self, periodo, placeholder, row):
        super().__init__(placeholder=placeholder, channel_types=[discord.ChannelType.text], row=row)
        self.periodo = periodo

    async def callback(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_destaque_" + self.periodo] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_destaque(data), view=ViewDestaque())


# ── PREFIXO ───────────────────────────────────────────────

class ViewPrefixo(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Alterar Prefixo", style=discord.ButtonStyle.grey, row=0)
    async def alterar(self, interaction, button):
        await interaction.response.send_modal(ModalAlterarPrefixo())

    @discord.ui.button(label="Comando +p", style=discord.ButtonStyle.green, row=0)
    async def toggle_p(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["config"]["cmd_p_jogadores"] = not data["config"].get("cmd_p_jogadores", True)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_prefixo(data), view=ViewPrefixo())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── BLACKLIST ─────────────────────────────────────────────

class ViewBlacklist(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_canal = discord.ui.ChannelSelect(placeholder="Selecione o Canal da BlackList", channel_types=[discord.ChannelType.text], row=0)
        sel_cargo = discord.ui.RoleSelect(placeholder="Selecione os Cargos de Controle", row=1)
        sel_canal.callback = self._set_canal
        sel_cargo.callback = self._set_cargo
        self.add_item(sel_canal)
        self.add_item(sel_cargo)

    async def _set_canal(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_blacklist"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal da blacklist configurado!", ephemeral=True)

    async def _set_cargo(self, interaction):
        cargo_obj = interaction.data["values"][0]
        cargo_id = int(cargo_obj) if isinstance(cargo_obj, str) else cargo_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["cargo_blacklist"] = cargo_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Cargo de controle configurado!", ephemeral=True)

    @discord.ui.button(label="SIM", style=discord.ButtonStyle.green, row=2)
    async def toggle(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["config"]["blacklist_pode_entrar_fila"] = not data["config"].get("blacklist_pode_entrar_fila", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=embed_blacklist(data, interaction.guild), view=ViewBlacklist())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── PERMISSÕES ────────────────────────────────────────────

class ViewPermissoes(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectPermissaoAlvo())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectPermissaoAlvo(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione a Permissão que deseja alterar.", options=[
            discord.SelectOption(label="Visualizar Apostas (+apostas)", value="perm_apostas"),
            discord.SelectOption(label="Visualizar BOs", value="perm_bos"),
            discord.SelectOption(label="Visualizar Eventos (+evento)", value="perm_eventos"),
            discord.SelectOption(label="Visualizar Logs (+logs)", value="perm_logs"),
            discord.SelectOption(label="Gerenciar Apostas", value="perm_gerenciar"),
            discord.SelectOption(label="Gerenciar Vitória/Derrota", value="perm_vitoria"),
            discord.SelectOption(label="Gerenciar Mediadores", value="perm_mediadores"),
            discord.SelectOption(label="Gerenciar Moedas", value="perm_moedas"),
            discord.SelectOption(label="Usar Comandos em todos lugares", value="perm_todos"),
            discord.SelectOption(label="Usar o Comando GP", value="perm_gp"),
            discord.SelectOption(label="Gerenciar Items", value="perm_itens"),
        ], row=0)

    async def callback(self, interaction):
        perm_key = self.values[0]
        view = discord.ui.View(timeout=60)
        sel = discord.ui.RoleSelect(placeholder="Selecione o cargo para: " + perm_key)
        async def role_cb(i):
            cargo_obj = i.data["values"][0]
            cargo_id = int(cargo_obj) if isinstance(cargo_obj, str) else cargo_obj.id
            cargo = i.guild.get_role(cargo_id)
            data = db.load(i.guild.id)
            if "permissoes" not in data["config"]:
                data["config"]["permissoes"] = {}
            atual = data["config"]["permissoes"].get(perm_key, "")
            if cargo.mention not in atual:
                data["config"]["permissoes"][perm_key] = (atual + " " + cargo.mention).strip()
            db.save(i.guild.id, data)
            await i.response.send_message("✅ " + perm_key + " → " + cargo.mention, ephemeral=True)
        sel.callback = role_cb
        view.add_item(sel)
        await interaction.response.send_message("Selecione o cargo para **" + perm_key + "**:", view=view, ephemeral=True)


# ── LOGS ──────────────────────────────────────────────────

class ViewLogs(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(SelectLogAlvo())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class SelectLogAlvo(discord.ui.Select):
    def __init__(self):
        super().__init__(placeholder="Selecione a log que deseja alterar.", options=[
            discord.SelectOption(label="Partidas Criadas", value="log_partidas_criadas"),
            discord.SelectOption(label="Partidas Concluídas", value="log_partidas_concluidas"),
            discord.SelectOption(label="Partidas Canceladas", value="log_partidas_canceladas"),
            discord.SelectOption(label="Partidas Encerradas", value="log_partidas_encerradas"),
            discord.SelectOption(label="Partidas Logs TXT", value="log_partidas_txt"),
            discord.SelectOption(label="Partidas Logs Transcript", value="log_partidas_transcript"),
            discord.SelectOption(label="Mediador Fila Status", value="log_mediador_fila"),
            discord.SelectOption(label="Mediador Receita", value="log_mediador_receita"),
            discord.SelectOption(label="Mediador Receita Reset", value="log_mediador_receita_reset"),
            discord.SelectOption(label="Moedas Transações", value="log_moedas"),
            discord.SelectOption(label="Loja Compras", value="log_loja_compras"),
            discord.SelectOption(label="Loja Resgates", value="log_loja_resgates"),
            discord.SelectOption(label="SS/Analista Logs", value="log_ss"),
            discord.SelectOption(label="Rate Limit Avisos", value="log_rate_limit"),
        ], row=0)

    async def callback(self, interaction):
        log_key = self.values[0]
        view = discord.ui.View(timeout=60)
        sel = discord.ui.ChannelSelect(placeholder="Canal para: " + log_key, channel_types=[discord.ChannelType.text])
        async def canal_cb(i):
            canal_obj = i.data["values"][0]
            canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
            canal = i.guild.get_channel(canal_id)
            data = db.load(i.guild.id)
            data["config"][log_key] = canal_id
            db.save(i.guild.id, data)
            await i.response.send_message("✅ " + log_key + " → " + (canal.mention if canal else str(canal_id)), ephemeral=True)
        sel.callback = canal_cb
        view.add_item(sel)
        await interaction.response.send_message("Selecione o canal para **" + log_key + "**:", view=view, ephemeral=True)


# ── CODIGUIN ──────────────────────────────────────────────

class ViewCodiguin(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Criar Novo Codiguin", style=discord.ButtonStyle.blurple, row=0)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalCriarCodiguin())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=0)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── ITENS ─────────────────────────────────────────────────

class ViewItens(discord.ui.View):
    def __init__(self, itens):
        super().__init__(timeout=300)
        if itens:
            opcoes = [discord.SelectOption(label="Configurar Item Individual", value="none")]
            for item_id, item in itens.items():
                opcoes.append(discord.SelectOption(label=item["nome"], value="i_" + item_id))
            sel = discord.ui.Select(placeholder="Configurar Item Individual", options=opcoes[:25], row=0)
            sel.callback = self._sel
            self.add_item(sel)

    async def _sel(self, interaction):
        await interaction.response.send_message("Em breve: configuração individual de itens!", ephemeral=True)

    @discord.ui.button(label="Adicionar Item", style=discord.ButtonStyle.green, row=1)
    async def add(self, interaction, button):
        await interaction.response.send_modal(ModalAdicionarItem())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── LOJA ──────────────────────────────────────────────────

class ViewLoja(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_canal = discord.ui.ChannelSelect(placeholder="Selecione o Canal Aviso de Compra", channel_types=[discord.ChannelType.text], row=0)
        sel_canal.callback = self._set_canal
        self.add_item(sel_canal)

    async def _set_canal(self, interaction):
        canal_obj = interaction.data["values"][0]
        canal_id = int(canal_obj) if isinstance(canal_obj, str) else canal_obj.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_aviso_compra"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal de aviso configurado!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── SS ────────────────────────────────────────────────────

class ViewSS(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=0)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())




# ── EVENTOS ───────────────────────────────────────────────

class ModalEventoInfoBasicas(discord.ui.Modal, title="Criar Evento - Informacoes Basicas"):
    nome = discord.ui.TextInput(label="Nome do Evento *", placeholder="Digite o nome do evento.", max_length=50)
    descricao = discord.ui.TextInput(label="Descricao do Evento *", placeholder="Digite a descricao do evento.", max_length=100, style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["evento_wip"] = {"nome": self.nome.value, "descricao": self.descricao.value}
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="Configuracao do Evento", description="Selecione a entidade que sera afetada pelo evento.", color=0x5865F2)
        embed.set_footer(text="Etapa 2/4")
        view = ViewEventoEtapa2()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ViewEventoEtapa2(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.Select(placeholder="Selecione a entidade do evento.", options=[
            discord.SelectOption(label="Jogador", value="jogador"),
        ], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        data = db.load(interaction.guild.id)
        data["evento_wip"]["entidade"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="Condicao para jogador", description="Selecione a condicao que determinara o sucesso do evento.", color=0x5865F2)
        embed.set_footer(text="Etapa 3/4")
        await interaction.response.edit_message(embed=embed, view=ViewEventoEtapa3())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        data.pop("evento_wip", None)
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
        embed.add_field(name="Quantidade de eventos:", value=str(len(data.get("eventos", []))), inline=False)
        await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))


class ViewEventoEtapa3(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        sel = discord.ui.Select(placeholder="Selecione a condicao do evento.", options=[
            discord.SelectOption(label="Vitorias", value="vitorias"),
            discord.SelectOption(label="Derrotas", value="derrotas"),
        ], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        data = db.load(interaction.guild.id)
        data["evento_wip"]["condicao"] = interaction.data["values"][0]
        db.save(interaction.guild.id, data)
        await interaction.response.send_modal(ModalEventoValorCondicao())

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.grey, row=1)
    async def cancelar(self, interaction, button):
        data = db.load(interaction.guild.id)
        data.pop("evento_wip", None)
        db.save(interaction.guild.id, data)
        embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
        embed.add_field(name="Quantidade de eventos:", value=str(len(data.get("eventos", []))), inline=False)
        await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))


class ModalEventoValorCondicao(discord.ui.Modal, title="Definir Valor da Condicao"):
    quantidade = discord.ui.TextInput(label="Quantidade: *", placeholder="Digite um numero.", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        wip = data.get("evento_wip", {})
        if "eventos" not in data:
            data["eventos"] = []
        novo = {
            "id": len(data["eventos"]),
            "nome": wip.get("nome", "Evento"),
            "descricao": wip.get("descricao", ""),
            "entidade": wip.get("entidade", "jogador"),
            "condicao": wip.get("condicao", "vitorias"),
            "quantidade": int(self.quantidade.value or 1),
            "ativo": True, "consecutivo": False, "revanche": False,
            "data_inicio": None, "data_fim": None,
            "criado_em": datetime.now().isoformat()
        }
        data["eventos"].append(novo)
        data.pop("evento_wip", None)
        db.save(interaction.guild.id, data)
        idx = len(data["eventos"]) - 1
        embed = _embed_evento(novo)
        await interaction.response.send_message(embed=embed, view=ViewEventoConfig(idx, novo), ephemeral=True)


class ModalEventoDatas(discord.ui.Modal, title="Configurar Datas do Evento"):
    inicio = discord.ui.TextInput(label="Data de Inicio (DD/MM/YYYY HH:mm) *", placeholder="Ex: 01/01/2025 17:30", max_length=20)
    fim = discord.ui.TextInput(label="Data de Termino (DD/MM/YYYY HH:mm) *", placeholder="Ex: 02/02/2025 02:45", max_length=20)

    def __init__(self, idx):
        super().__init__()
        self.idx = idx

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["eventos"][self.idx]["data_inicio"] = self.inicio.value
        data["eventos"][self.idx]["data_fim"] = self.fim.value
        db.save(interaction.guild.id, data)
        embed = _embed_evento(data["eventos"][self.idx])
        await interaction.response.send_message(embed=embed, view=ViewEventoConfig(self.idx, data["eventos"][self.idx]), ephemeral=True)


def _embed_evento(evento):
    embed = discord.Embed(title="Configurar Evento: " + evento["nome"], description=evento["descricao"], color=0x5865F2)
    embed.add_field(name="Status", value="Ativo" if evento.get("ativo") else "Inativo", inline=True)
    embed.add_field(name="Condicao", value=evento.get("condicao","vitorias").title() + " -> " + str(evento.get("quantidade",1)), inline=True)
    di = evento.get("data_inicio") or "Nao configurado"
    df = evento.get("data_fim") or "Nao configurado"
    embed.add_field(name="Datas", value="Ini.: " + di + "\nTer.: " + df, inline=False)
    embed.add_field(name="Condicoes Especiais", value="\u200b", inline=False)
    embed.add_field(name="Consecutivo", value="\U0001f7e2" if evento.get("consecutivo") else "\U0001f534", inline=True)
    embed.add_field(name="Revanche", value="\U0001f7e2" if evento.get("revanche") else "\U0001f534", inline=True)
    return embed


class ViewEventoConfig(discord.ui.View):
    def __init__(self, idx, evento):
        super().__init__(timeout=300)
        self.idx = idx
        self.evento = evento
        sel = discord.ui.Select(placeholder="Selecione para configurar", options=[
            discord.SelectOption(label="Configurar Datas", description="Configure as datas de inicio e termino do evento.", emoji="\u2699\ufe0f", value="datas"),
            discord.SelectOption(label="Alterar Condicao", description="Altere a condicao do evento.", emoji="\u2699\ufe0f", value="condicao"),
            discord.SelectOption(label="Excluir Evento", description="Clique aqui para excluir o evento.", emoji="\U0001f5d1\ufe0f", value="excluir"),
        ], row=0)
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        v = interaction.data["values"][0]
        data = db.load(interaction.guild.id)
        if v == "datas":
            await interaction.response.send_modal(ModalEventoDatas(self.idx))
        elif v == "condicao":
            await interaction.response.edit_message(embed=discord.Embed(title="Alterar Condicao", color=0x5865F2), view=ViewEventoEtapa3())
        elif v == "excluir":
            data["eventos"].pop(self.idx)
            db.save(interaction.guild.id, data)
            embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
            embed.add_field(name="Quantidade de eventos:", value=str(len(data["eventos"])), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))

    @discord.ui.button(label="Evento: LIGADO", style=discord.ButtonStyle.green, row=1)
    async def toggle_ativo(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["eventos"][self.idx]["ativo"] = not data["eventos"][self.idx].get("ativo", True)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=_embed_evento(data["eventos"][self.idx]), view=ViewEventoConfig(self.idx, data["eventos"][self.idx]))

    @discord.ui.button(label="Consecutivo", style=discord.ButtonStyle.red, row=2)
    async def toggle_consec(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["eventos"][self.idx]["consecutivo"] = not data["eventos"][self.idx].get("consecutivo", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=_embed_evento(data["eventos"][self.idx]), view=ViewEventoConfig(self.idx, data["eventos"][self.idx]))

    @discord.ui.button(label="Revanche", style=discord.ButtonStyle.red, row=3)
    async def toggle_rev(self, interaction, button):
        data = db.load(interaction.guild.id)
        data["eventos"][self.idx]["revanche"] = not data["eventos"][self.idx].get("revanche", False)
        db.save(interaction.guild.id, data)
        await interaction.response.edit_message(embed=_embed_evento(data["eventos"][self.idx]), view=ViewEventoConfig(self.idx, data["eventos"][self.idx]))

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        data = db.load(interaction.guild.id)
        embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
        embed.add_field(name="Quantidade de eventos:", value=str(len(data.get("eventos", []))), inline=False)
        await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))


class ViewEventos(discord.ui.View):
    def __init__(self, eventos=None):
        super().__init__(timeout=300)
        self.eventos = eventos or []
        if self.eventos:
            opcoes = [discord.SelectOption(label=ev["nome"][:50], description=("Ativo" if ev.get("ativo") else "Inativo"), value=str(i)) for i, ev in enumerate(self.eventos[:25])]
            sel = discord.ui.Select(placeholder="Selecione um evento para configurar", options=opcoes, row=0)
            sel.callback = self._sel
            self.add_item(sel)

    async def _sel(self, interaction):
        idx = int(interaction.data["values"][0])
        data = db.load(interaction.guild.id)
        evento = data["eventos"][idx]
        await interaction.response.edit_message(embed=_embed_evento(evento), view=ViewEventoConfig(idx, evento))

    @discord.ui.button(label="Criar Evento", style=discord.ButtonStyle.green, row=1)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalEventoInfoBasicas())

    @discord.ui.button(label="Configurar Geral", style=discord.ButtonStyle.blurple, row=1)
    async def config_geral(self, interaction, button):
        await interaction.response.send_message("Em breve!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())




# ── STREAMERS ─────────────────────────────────────────────

class ViewStreamers(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_cat = discord.ui.ChannelSelect(placeholder="Selecione a Categoria", channel_types=[discord.ChannelType.category], row=0)
        sel_cargo = discord.ui.RoleSelect(placeholder="Selecione o Cargo Streamer", row=1)
        sel_painel = discord.ui.ChannelSelect(placeholder="Selecione o Canal do Painel", channel_types=[discord.ChannelType.text], row=2)
        sel_liveon = discord.ui.ChannelSelect(placeholder="Selecione o Canal de LiveOn", channel_types=[discord.ChannelType.text], row=3)
        sel_cat.callback = self._set_cat
        sel_cargo.callback = self._set_cargo
        sel_painel.callback = self._set_painel
        sel_liveon.callback = self._set_liveon
        self.add_item(sel_cat)
        self.add_item(sel_cargo)
        self.add_item(sel_painel)
        self.add_item(sel_liveon)

    async def _set_cat(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["streamer_categoria_id"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Categoria de streamers configurada!", ephemeral=True)

    async def _set_cargo(self, interaction):
        v = interaction.data["values"][0]
        cargo_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["cargo_streamer"] = cargo_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Cargo streamer configurado!", ephemeral=True)

    async def _set_painel(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_streamer_painel"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal do painel streamer configurado!", ephemeral=True)

    async def _set_liveon(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_streamer_liveon"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Canal Live On configurado!", ephemeral=True)

    @discord.ui.button(label="Desligada", style=discord.ButtonStyle.red, row=4)
    async def toggle_med(self, interaction, button):
        data = db.load(interaction.guild.id)
        atual = data["config"].get("streamer_med_solo", False)
        data["config"]["streamer_med_solo"] = not atual
        db.save(interaction.guild.id, data)
        status = "SIM" if not atual else "NAO"
        await interaction.response.send_message("Streamer pode selecionar mediador: " + status, ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=4)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── CAIXAS ────────────────────────────────────────────────

class ViewCaixas(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_acao = discord.ui.Select(placeholder="Personalização de Embeds da Caixa", options=[
            discord.SelectOption(label="Personalização de Embeds da Caixa", description="Altera cores/textos da abertura pública.", value="embeds_caixa"),
            discord.SelectOption(label="Personalizar a Caixa", description="Altera chances percentuais e drops.", value="config_caixa"),
        ], row=0)
        sel_acao.callback = self._acao
        self.add_item(sel_acao)
        sel_canal = discord.ui.ChannelSelect(placeholder="Selecione o canal para enviar o painel", channel_types=[discord.ChannelType.text], row=1)
        sel_aviso = discord.ui.ChannelSelect(placeholder="Selecione o canal de avisos de ganhos", channel_types=[discord.ChannelType.text], row=2)
        sel_canal.callback = self._set_canal
        sel_aviso.callback = self._set_aviso
        self.add_item(sel_canal)
        self.add_item(sel_aviso)

    async def _acao(self, interaction):
        await interaction.response.send_message("Em breve: " + self.values[0] if hasattr(self, 'values') else "Em breve!", ephemeral=True)

    async def _set_canal(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_caixa"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal de caixas configurado!", ephemeral=True)

    async def _set_aviso(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_aviso_caixa"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal de avisos de caixas configurado!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=3)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── ROLETA ────────────────────────────────────────────────

class ViewRoleta(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel_acao = discord.ui.Select(placeholder="Personalização de Embeds da Roleta", options=[
            discord.SelectOption(label="Personalização de Embeds da Roleta", description="Altera cores/textos da roleta pública.", value="embeds_roleta"),
            discord.SelectOption(label="Personalizar a Roleta", description="Altera chances percentuais e prêmios.", value="config_roleta"),
        ], row=0)
        sel_acao.callback = self._acao
        self.add_item(sel_acao)
        sel_canal = discord.ui.ChannelSelect(placeholder="Selecione o canal para enviar o painel", channel_types=[discord.ChannelType.text], row=1)
        sel_aviso = discord.ui.ChannelSelect(placeholder="Selecione o canal de avisos de ganhos", channel_types=[discord.ChannelType.text], row=2)
        sel_canal.callback = self._set_canal
        sel_aviso.callback = self._set_aviso
        self.add_item(sel_canal)
        self.add_item(sel_aviso)

    async def _acao(self, interaction):
        await interaction.response.send_message("Em breve!", ephemeral=True)

    async def _set_canal(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_roleta"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal da roleta configurado!", ephemeral=True)

    async def _set_aviso(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_aviso_roleta"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal de avisos da roleta configurado!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=3)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── CODIGUIN (com paginação) ──────────────────────────────

class ViewCodiguin(discord.ui.View):
    def __init__(self, codiguins=None, pagina=1):
        super().__init__(timeout=300)
        self.codiguins = codiguins or {}
        self.pagina = pagina
        self.total = max(1, (len(self.codiguins) + 9) // 10)

    @discord.ui.button(label="Criar Novo Codiguin", style=discord.ButtonStyle.blurple, row=0)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalCriarCodiguin())

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.grey, row=0)
    async def anterior(self, interaction, button):
        if self.pagina > 1:
            self.pagina -= 1
        await self._atualizar(interaction)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.grey, row=0)
    async def proximo(self, interaction, button):
        if self.pagina < self.total:
            self.pagina += 1
        await self._atualizar(interaction)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())

    async def _atualizar(self, interaction):
        data = db.load(interaction.guild.id)
        codiguins = data.get("codiguins", {})
        items = list(codiguins.items())
        inicio = (self.pagina - 1) * 10
        fim = inicio + 10
        pagina_items = items[inicio:fim]
        embed = discord.Embed(title="Central - Codiguins", color=0x5865F2)
        embed.description = "\n".join(["`" + k + "` → " + v["item"] + " (" + str(v["usos_atual"]) + "/" + str(v["usos_max"]) + " usos)" for k, v in pagina_items]) if pagina_items else "Nenhum codiguin criado ainda. Clique em **Criar Novo Codiguin** para começar."
        embed.set_footer(text="Página " + str(self.pagina) + " de " + str(max(1, (len(codiguins) + 9) // 10)))
        await interaction.response.edit_message(embed=embed, view=ViewCodiguin(codiguins, self.pagina))


# ── LOJA (com Adicionar Loja) ─────────────────────────────

class ModalCriarLoja(discord.ui.Modal, title="Criar Loja"):
    nome = discord.ui.TextInput(label="Nome da Loja", placeholder="ex: LOJINHA DA ARENA", max_length=40)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        if "lojas" not in data:
            data["lojas"] = {}
        loja_id = self.nome.value.lower().replace(" ", "_")
        data["lojas"][loja_id] = {"nome": self.nome.value, "itens": [], "ativo": True}
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Loja **" + self.nome.value + "** criada!", ephemeral=True)


class ModalConfigDelay(discord.ui.Modal, title="Configurar Delay da Loja"):
    delay = discord.ui.TextInput(label="Delay entre compras (minutos)", default="0", max_length=5)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["delay_loja"] = int(self.delay.value or 0)
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Delay: " + self.delay.value + " minuto(s)", ephemeral=True)


class ViewLoja(discord.ui.View):
    def __init__(self, lojas=None):
        super().__init__(timeout=300)
        self.lojas = lojas or {}
        sel_canal = discord.ui.ChannelSelect(placeholder="Selecione o Canal Aviso de Compra", channel_types=[discord.ChannelType.text], row=0)
        sel_canal.callback = self._set_canal
        self.add_item(sel_canal)
        if self.lojas:
            opcoes = [discord.SelectOption(label="Configurar Loja Individual.", value="none")]
            for loja_id, loja in self.lojas.items():
                opcoes.append(discord.SelectOption(label=loja["nome"], value="l_" + loja_id))
            sel_loja = discord.ui.Select(placeholder="Configurar Loja Individual.", options=opcoes[:25], row=1)
            sel_loja.callback = self._sel_loja
            self.add_item(sel_loja)

    async def _set_canal(self, interaction):
        v = interaction.data["values"][0]
        canal_id = int(v) if isinstance(v, str) else v.id
        data = db.load(interaction.guild.id)
        data["config"]["canal_aviso_compra"] = canal_id
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Canal de aviso configurado!", ephemeral=True)

    async def _sel_loja(self, interaction):
        await interaction.response.send_message("Em breve: configuração individual de loja!", ephemeral=True)

    @discord.ui.button(label="Configurar", style=discord.ButtonStyle.blurple, row=2)
    async def config_delay(self, interaction, button):
        await interaction.response.send_modal(ModalConfigDelay())

    @discord.ui.button(label="Adicionar Loja", style=discord.ButtonStyle.green, row=2)
    async def add_loja(self, interaction, button):
        await interaction.response.send_modal(ModalCriarLoja())

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=3)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# ── BOT ───────────────────────────────────────────────────

class ModalConfigBot(discord.ui.Modal, title="Configurar Bot"):
    nome = discord.ui.TextInput(label="Nome da Org", placeholder="ex: ARENA X1", max_length=30)

    async def on_submit(self, interaction):
        data = db.load(interaction.guild.id)
        data["config"]["nome_org"] = self.nome.value
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("✅ Nome da org: **" + self.nome.value + "**", ephemeral=True)


class ViewBot(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        sel = discord.ui.Select(
            placeholder="Selecione uma opcao para configurar o bot.",
            options=[
                discord.SelectOption(label="Resetar Bot", description="Veja como resetar o bot.", value="resetar"),
                discord.SelectOption(label="Configurar Nome da Org", description="Altere o nome da organizacao.", value="nome"),
            ],
            row=0
        )
        sel.callback = self._sel
        self.add_item(sel)

    async def _sel(self, interaction):
        v = interaction.data["values"][0]
        if v == "resetar":
            embed = discord.Embed(title="Resetar Bot", color=discord.Color.red())
            embed.description = "ATENCAO: Isso vai apagar TODOS os dados do servidor. Essa acao e irreversivel!"
            view = ViewConfirmarReset()
            await interaction.response.edit_message(embed=embed, view=view)
        elif v == "nome":
            await interaction.response.send_modal(ModalConfigBot())
        else:
            await interaction.response.defer()


    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


class ViewConfirmarReset(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Confirmar Reset", style=discord.ButtonStyle.red, row=0)
    async def confirmar(self, interaction, button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Apenas administradores podem resetar.", ephemeral=True)
            return
        import os
        path = "data/" + str(interaction.guild.id) + ".json"
        if os.path.exists(path):
            os.remove(path)
        await interaction.response.send_message("Bot resetado!", ephemeral=True)

    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.grey, row=0)
    async def cancelar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())


# COG
class Central(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="central", description="[ADMIN] Central de controle do bot")
    async def central(self, interaction: discord.Interaction):
        embed = embed_central(interaction.guild)
        await interaction.response.send_message(embed=embed, view=ViewCentral(), ephemeral=True)

    @app_commands.command(name="codiguin", description="Resgata um codiguin")
    async def resgatar_codiguin(self, interaction: discord.Interaction, codigo: str):
        data = db.load(interaction.guild.id)
        cod = data.get("codiguins", {}).get(codigo.upper())
        if not cod or not cod.get("ativo"):
            await interaction.response.send_message("Codigo invalido.", ephemeral=True)
            return
        if cod["usos_max"] > 0 and cod["usos_atual"] >= cod["usos_max"]:
            await interaction.response.send_message("Codigo esgotado.", ephemeral=True)
            return
        cod["usos_atual"] += 1
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Resgatado! Recompensa: " + cod["item"], ephemeral=True)


async def setup(bot):
    await bot.add_cog(Central(bot))
