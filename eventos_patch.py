path = '/data/data/com.termux/files/home/arena-bot/cogs/central.py'
with open(path, 'r') as f:
    content = f.read()

# Replace ViewEventos with version that includes select for existing events
old = '''class ViewEventos(discord.ui.View):
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
        await interaction.response.edit_message(embed=embed, view=ViewCentral())'''

new = '''class ViewEventos(discord.ui.View):
    def __init__(self, eventos=None):
        super().__init__(timeout=300)
        self.eventos = eventos or []
        if self.eventos:
            opcoes = []
            for i, ev in enumerate(self.eventos[:25]):
                status = "Ativo" if ev.get("ativo") else "Inativo"
                opcoes.append(discord.SelectOption(
                    label=ev["nome"][:50],
                    description=status + " | " + ev.get("condicao","vitorias").title() + " -> " + str(ev.get("quantidade",1)),
                    value=str(i)
                ))
            sel = discord.ui.Select(placeholder="Selecione um evento para configurar", options=opcoes, row=0)
            sel.callback = self._sel_evento
            self.add_item(sel)

    async def _sel_evento(self, interaction):
        idx = int(interaction.data["values"][0])
        data = db.load(interaction.guild.id)
        evento = data["eventos"][idx]
        embed = _embed_evento(evento)
        await interaction.response.edit_message(embed=embed, view=ViewEventoConfig(idx, evento))

    @discord.ui.button(label="Criar Evento", style=discord.ButtonStyle.green, row=1)
    async def criar(self, interaction, button):
        await interaction.response.send_modal(ModalEventoInfoBasicas())

    @discord.ui.button(label="Configurar Geral", style=discord.ButtonStyle.blurple, row=1)
    async def config_geral(self, interaction, button):
        await interaction.response.send_message("Em breve!", ephemeral=True)

    @discord.ui.button(label="Voltar", style=discord.ButtonStyle.grey, row=2)
    async def voltar(self, interaction, button):
        embed = embed_central(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=ViewCentral())'''

if old in content:
    content = content.replace(old, new)
    print("ViewEventos substituida!")
else:
    print("Padrao nao encontrado, tentando busca parcial...")
    idx = content.find('class ViewEventos')
    print("ViewEventos encontrada na linha:", content[:idx].count(chr(10))+1)
    print("Conteudo atual:")
    print(content[idx:idx+300])

# Also fix the embed callback that shows eventos to pass eventos list
old_ev_callback = '''            embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
            embed.description = "Configure tudo relacionado aos Eventos aqui!"
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="Quantidade de eventos:", value=str(len(data2.get("eventos", []))), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos())'''

new_ev_callback = '''            eventos = data2.get("eventos", [])
            embed = discord.Embed(title="Evento Geral", description="Configure tudo relacionado aos Eventos aqui!", color=0x5865F2)
            if interaction.guild.icon:
                embed.set_thumbnail(url=interaction.guild.icon.url)
            embed.add_field(name="Quantidade de eventos:", value=str(len(eventos)), inline=False)
            await interaction.response.edit_message(embed=embed, view=ViewEventos(eventos))'''

if old_ev_callback in content:
    content = content.replace(old_ev_callback, new_ev_callback)
    print("Callback eventos corrigido!")

# Fix all places that create ViewEventos() without args after voltar
content = content.replace(
    'await interaction.response.edit_message(embed=embed, view=ViewEventos())',
    'await interaction.response.edit_message(embed=embed, view=ViewEventos(db.load(interaction.guild.id).get("eventos", [])))'
)

with open(path, 'w') as f:
    f.write(content)

import ast
try:
    ast.parse(content)
    print("OK:", len(content.split(chr(10))), "linhas")
except (SyntaxError, IndentationError) as e:
    print(f"ERRO linha {e.lineno}: {e.msg}")
    lines = content.split(chr(10))
    for i in range(max(0,e.lineno-2), min(len(lines), e.lineno+2)):
        print(f"{i+1}: {repr(lines[i])}")
