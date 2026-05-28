import sys
path = '/data/data/com.termux/files/home/arena-bot/cogs/central.py'
with open(path, 'r') as f:
    content = f.read()

# Find start of ModalCriarEvento
start = content.find('class ModalCriarEvento')
# Find start of ViewEventos (after ModalCriarEvento)
mid = content.find('class ViewEventos', start)
# Find end of ViewEventos
end = content.find('\n\n\n', mid)
if end == -1:
    end = content.find('\n\n# ──', mid)

print(f"start={start}, mid={mid}, end={end}")
print("Substituindo linhas", content[:start].count('\n')+1, "a", content[:end].count('\n')+1)

NEW_CODE = '''class ModalEventoInfoBasicas(discord.ui.Modal, title="Criar Evento - Informacoes Basicas"):
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
        await interaction.response.edit_message(embed=embed, view=ViewEventos())


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
        await interaction.response.edit_message(embed=embed, view=ViewEventos())


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
    embed.add_field(name="Datas", value="Ini.: " + di + "\\nTer.: " + df, inline=False)
    embed.add_field(name="Condicoes Especiais", value="\\u200b", inline=False)
    embed.add_field(name="Consecutivo", value="\\U0001f7e2" if evento.get("consecutivo") else "\\U0001f534", inline=True)
    embed.add_field(name="Revanche", value="\\U0001f7e2" if evento.get("revanche") else "\\U0001f534", inline=True)
    return embed


class ViewEventoConfig(discord.ui.View):
    def __init__(self, idx, evento):
        super().__init__(timeout=300)
        self.idx = idx
        self.evento = evento
        sel = discord.ui.Select(placeholder="Selecione para configurar", options=[
            discord.SelectOption(label="Configurar Datas", description="Configure as datas de inicio e termino do evento.", emoji="\\u2699\\ufe0f", value="datas"),
            discord.SelectOption(label="Alterar Condicao", description="Altere a condicao do evento.", emoji="\\u2699\\ufe0f", value="condicao"),
            discord.SelectOption(label="Excluir Evento", description="Clique aqui para excluir o evento.", emoji="\\U0001f5d1\\ufe0f", value="excluir"),
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
            await interaction.response.edit_message(embed=embed, view=ViewEventos())

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
        await interaction.response.edit_message(embed=embed, view=ViewEventos())


class ViewEventos(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="Criar Evento", style=discord.ButtonStyle.green, row=0)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalEventoInfoBasicas())

    @discord.ui.button(label="Configurar Geral", style=discord.ButtonStyle.blurple, row=0)
    async def config_geral(self, interaction, button):
        await interaction.response.send_message("Em breve!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=1)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())

'''

content = content[:start] + NEW_CODE + content[end:]
with open(path, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("OK:", len(content.split(chr(10))), "linhas")
except SyntaxError as e:
    print(f"ERRO linha {e.lineno}: {e.msg}")
    lines = content.split(chr(10))
    for i in range(max(0,e.lineno-2), min(len(lines), e.lineno+2)):
        print(f"{i+1}: {repr(lines[i])}")
