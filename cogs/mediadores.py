"""
cogs/mediadores.py — Fila de mediadores com painel interativo
"""
import discord
from discord.ext import commands
from discord import app_commands
from utils import database as db




class ModalRegistrarPIX(discord.ui.Modal, title="Registrar PIX de Mediador"):
    nome = discord.ui.TextInput(
        label="Nome do Mediador",
        placeholder="ex: João Silva",
        max_length=50
    )
    pix = discord.ui.TextInput(
        label="Chave PIX",
        placeholder="ex: 11999999999 ou email@exemplo.com",
        max_length=100
    )
    usuario = discord.ui.TextInput(
        label="@ do Discord (ID ou username)",
        placeholder="ex: 123456789 ou joaosilva",
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        data = db.load(guild.id)

        # Tenta encontrar o usuário pelo ID ou username
        uid_str = self.usuario.value.strip().replace("<@", "").replace(">", "").replace("!", "")
        membro = None

        # Tenta por ID
        try:
            membro = guild.get_member(int(uid_str))
        except ValueError:
            # Tenta por username
            for m in guild.members:
                if m.name.lower() == uid_str.lower() or m.display_name.lower() == uid_str.lower():
                    membro = m
                    break

        if not membro:
            await interaction.response.send_message(
                f"❌ Usuário `{self.usuario.value}` não encontrado no servidor.",
                ephemeral=True
            )
            return

        uid = str(membro.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()

        data["jogadores"][uid]["pix"] = self.pix.value
        data["jogadores"][uid]["nome_display"] = self.nome.value
        db.save(guild.id, data)

        await interaction.response.send_message(
            f"✅ PIX registrado!\n**Mediador:** {membro.mention} ({self.nome.value})\n**Chave PIX:** `{self.pix.value}`",
            ephemeral=True
        )

class PainelMediadores(discord.ui.View):
    """Painel fixo no canal #fila-mediador."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar na fila", style=discord.ButtonStyle.green,
                       custom_id="MED|entrar")
    async def entrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        data = db.load(guild.id)
        config = data["config"]
        uid = interaction.user.id

        # Verifica cargo de mediador
        cargo_id = config.get("cargo_mediador")
        if cargo_id:
            cargo = guild.get_role(cargo_id)
            if cargo and cargo not in interaction.user.roles:
                await interaction.response.send_message(
                    "❌ Você não tem o cargo de mediador.", ephemeral=True
                )
                return

        fila = data.get("fila_mediadores", [])
        if uid in fila:
            await interaction.response.send_message("⏳ Você já está na fila!", ephemeral=True)
            return

        fila.append(uid)
        data["fila_mediadores"] = fila
        db.save(guild.id, data)

        await atualizar_painel_mediador(interaction, data)
        await interaction.response.send_message(
            "✅ Você entrou na fila de mediadores!", ephemeral=True
        )

    @discord.ui.button(label="Sair da fila", style=discord.ButtonStyle.red,
                       custom_id="MED|sair")
    async def sair(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        data = db.load(guild.id)
        uid = interaction.user.id
        fila = data.get("fila_mediadores", [])

        if uid not in fila:
            await interaction.response.send_message("❌ Você não está na fila.", ephemeral=True)
            return

        fila.remove(uid)
        data["fila_mediadores"] = fila
        db.save(guild.id, data)

        await atualizar_painel_mediador(interaction, data)
        await interaction.response.send_message("✅ Você saiu da fila.", ephemeral=True)

    @discord.ui.button(label="⚙️ Remover da Fila", style=discord.ButtonStyle.grey,
                       custom_id="MED|remover")
    async def remover(self, interaction: discord.Interaction, button: discord.ui.Button):
        """ADM remove qualquer mediador da fila."""
        data = db.load(interaction.guild.id)
        config = data["config"]

        # Verifica se tem cargo admin ou mediador superior
        cargo_admin_id = config.get("cargo_admin")
        cargo_med_id = config.get("cargo_mediador")
        tem_permissao = interaction.user.guild_permissions.administrator

        if not tem_permissao and cargo_admin_id:
            cargo = interaction.guild.get_role(cargo_admin_id)
            if cargo and cargo in interaction.user.roles:
                tem_permissao = True

        if not tem_permissao:
            await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
            return

        fila = data.get("fila_mediadores", [])
        if not fila:
            await interaction.response.send_message("❌ Fila vazia.", ephemeral=True)
            return

        # Mostra select com mediadores na fila pra remover
        view = ViewRemoverMediador(fila, interaction.guild)
        await interaction.response.send_message(
            "Selecione o mediador para remover da fila:",
            view=view, ephemeral=True
        )


class ViewRemoverMediador(discord.ui.View):
    def __init__(self, fila: list, guild: discord.Guild):
        super().__init__(timeout=60)
        opcoes = []
        for uid in fila:
            m = guild.get_member(uid)
            nome = m.display_name if m else str(uid)
            opcoes.append(discord.SelectOption(label=nome, value=str(uid)))
        sel = discord.ui.Select(placeholder="Selecione o mediador...", options=opcoes[:25])
        sel.callback = self._remover
        self.add_item(sel)

    async def _remover(self, interaction: discord.Interaction):
        uid_str = interaction.data["values"][0]
        uid = int(uid_str)
        data = db.load(interaction.guild.id)
        fila = data.get("fila_mediadores", [])
        if uid in fila:
            fila.remove(uid)
            data["fila_mediadores"] = fila
            db.save(interaction.guild.id, data)
            m = interaction.guild.get_member(uid)
            nome = m.display_name if m else uid_str
            await interaction.response.send_message(
                f"✅ {nome} removido da fila.", ephemeral=True
            )
            # Atualiza o painel no canal
            canal_id = data["config"].get("canal_fila_mediador")
            if canal_id:
                canal = interaction.guild.get_channel(canal_id)
                if canal:
                    async for msg in canal.history(limit=20):
                        if msg.author.id == interaction.guild.me.id and msg.components:
                            linhas = []
                            for i, u in enumerate(fila, 1):
                                mem = interaction.guild.get_member(u)
                                pix = data["jogadores"].get(str(u), {}).get("pix", "Sem PIX")
                                linhas.append(f"{i}. {mem.mention if mem else u} — PIX: `{pix}`")
                            embed = discord.Embed(title="Fila Mediadores", color=discord.Color.blurple())
                            embed.description = "\n".join(linhas) if linhas else "Nenhum mediador na fila."
                            try:
                                await msg.edit(embed=embed)
                            except Exception:
                                pass
                            break
        else:
            await interaction.response.send_message("❌ Mediador não está na fila.", ephemeral=True)


async def atualizar_painel_mediador(interaction: discord.Interaction, data: dict):
    """Atualiza a embed do painel de mediadores."""
    fila = data.get("fila_mediadores", [])
    guild = interaction.guild

    linhas = []
    for i, uid in enumerate(fila, 1):
        m = guild.get_member(uid)
        pix = data["jogadores"].get(str(uid), {}).get("pix", "Sem PIX")
        nome = m.display_name if m else f"ID:{uid}"
        linhas.append(f"{i}. {m.mention if m else nome} — PIX: `{pix}`")

    embed = discord.Embed(title="Fila Mediadores", color=discord.Color.blurple())
    embed.description = "\n".join(linhas) if linhas else "Nenhum mediador na fila."

    # Tenta editar a mensagem original
    try:
        await interaction.message.edit(embed=embed)
    except Exception:
        pass


async def postar_painel_mediador(canal: discord.TextChannel, guild: discord.Guild, data: dict):
    """Posta o painel de mediadores num canal."""
    fila = data.get("fila_mediadores", [])
    linhas = []
    for i, uid in enumerate(fila, 1):
        m = guild.get_member(uid)
        pix = data["jogadores"].get(str(uid), {}).get("pix", "Sem PIX")
        nome = m.display_name if m else f"ID:{uid}"
        linhas.append(f"{i}. {m.mention if m else nome} — PIX: `{pix}`")

    embed = discord.Embed(title="Fila Mediadores", color=discord.Color.blurple())
    embed.description = "\n".join(linhas) if linhas else "Nenhum mediador na fila."

    await canal.send(embed=embed, view=PainelMediadores())



async def _atualizar_embed_mediador(message, guild, data):
    """Atualiza a embed do painel de mediadores."""
    fila = data.get("fila_mediadores", [])
    linhas = []
    for i, uid in enumerate(fila, 1):
        m = guild.get_member(uid)
        pix = data["jogadores"].get(str(uid), {}).get("pix", "Sem PIX")
        linhas.append(f"{i}. {m.mention if m else uid} — PIX: `{pix}`")
    embed = discord.Embed(title="Fila Mediadores", color=discord.Color.blurple())
    embed.description = "\n".join(linhas) if linhas else "Nenhum mediador na fila."
    try:
        await message.edit(embed=embed)
    except Exception:
        pass


class Mediadores(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Intercepta botões do painel de mediadores."""
        if interaction.type != discord.InteractionType.component:
            return
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("MED|"):
            return

        guild = interaction.guild
        data = db.load(guild.id)
        config = data["config"]
        uid = interaction.user.id

        if custom_id == "MED|entrar":
            # Verifica cargo
            cargo_id = config.get("cargo_mediador")
            if cargo_id:
                cargo = guild.get_role(cargo_id)
                if cargo and cargo not in interaction.user.roles:
                    await interaction.response.send_message("❌ Você não tem o cargo de mediador.", ephemeral=True)
                    return

            fila = data.get("fila_mediadores", [])
            if uid in fila:
                await interaction.response.send_message("⏳ Você já está na fila!", ephemeral=True)
                return

            fila.append(uid)
            data["fila_mediadores"] = fila
            db.save(guild.id, data)

            # Atualiza embed
            await _atualizar_embed_mediador(interaction.message, guild, data)
            await interaction.response.send_message("✅ Você entrou na fila de mediadores!", ephemeral=True)

        elif custom_id == "MED|sair":
            fila = data.get("fila_mediadores", [])
            if uid not in fila:
                await interaction.response.send_message("❌ Você não está na fila.", ephemeral=True)
                return

            fila.remove(uid)
            data["fila_mediadores"] = fila
            db.save(guild.id, data)

            await _atualizar_embed_mediador(interaction.message, guild, data)
            await interaction.response.send_message("✅ Você saiu da fila.", ephemeral=True)

        elif custom_id == "MED|remover":
            # Verifica permissão admin
            tem_perm = interaction.user.guild_permissions.administrator
            cargo_admin_id = config.get("cargo_admin")
            if not tem_perm and cargo_admin_id:
                cargo = guild.get_role(cargo_admin_id)
                if cargo and cargo in interaction.user.roles:
                    tem_perm = True

            if not tem_perm:
                await interaction.response.send_message("❌ Sem permissão.", ephemeral=True)
                return

            fila = data.get("fila_mediadores", [])
            if not fila:
                await interaction.response.send_message("❌ Fila vazia.", ephemeral=True)
                return

            opcoes = []
            for u in fila:
                m = guild.get_member(u)
                nome = m.display_name if m else str(u)
                opcoes.append(discord.SelectOption(label=nome, value=str(u)))

            view = ViewRemoverMediador(fila, guild)
            await interaction.response.send_message(
                "Selecione o mediador para remover:", view=view, ephemeral=True
            )

    @app_commands.command(name="mediadores",
                          description="Lista os mediadores na fila")
    async def mediadores(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        fila = data.get("fila_mediadores", [])
        guild = interaction.guild

        embed = discord.Embed(title="🛡️ Fila de Mediadores", color=discord.Color.blurple())
        if not fila:
            embed.description = "Nenhum mediador na fila."
        else:
            linhas = []
            for i, uid in enumerate(fila, 1):
                m = guild.get_member(uid)
                pix = data["jogadores"].get(str(uid), {}).get("pix", "Sem PIX")
                linhas.append(f"`{i}.` {m.mention if m else uid} — PIX: `{pix}`")
            embed.description = "\n".join(linhas)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="mediador-info-usuario",
                          description="[ADM] Informações de um mediador")
    async def mediador_info(self, interaction: discord.Interaction,
                             usuario: discord.Member):
        data = db.load(interaction.guild.id)
        uid = str(usuario.id)
        j = data["jogadores"].get(uid, {})

        embed = discord.Embed(
            title=f"📊 Info — {usuario.display_name}",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=usuario.display_avatar.url)
        embed.add_field(name="Partidas mediadas", value=str(j.get("partidas_mediadas", 0)), inline=True)
        embed.add_field(name="Receita total", value=f"R$ {j.get('receita_total', 0.0):.2f}", inline=True)
        embed.add_field(name="PIX", value=j.get("pix", "Não cadastrado"), inline=False)

        fila = data.get("fila_mediadores", [])
        pos = fila.index(usuario.id) + 1 if usuario.id in fila else "Fora da fila"
        embed.add_field(name="Posição na fila", value=str(pos), inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @app_commands.command(name="pix",
                          description="Cadastre seu próprio PIX para receber pagamentos")
    async def pix_registrar(self, interaction: discord.Interaction, chave_pix: str):
        guild = interaction.guild
        data = db.load(guild.id)
        uid = str(interaction.user.id)
        if uid not in data["jogadores"]:
            data["jogadores"][uid] = db.DEFAULT_JOGADOR.copy()
        data["jogadores"][uid]["pix"] = chave_pix
        db.save(guild.id, data)
        await interaction.response.send_message(
            f"✅ PIX cadastrado: `{chave_pix}`", ephemeral=True
        )

    @app_commands.command(name="pix-registrar",
                          description="[ADM] Registra o PIX de um mediador via formulário")
    async def pix_registrar_adm(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ModalRegistrarPIX())

    @app_commands.command(name="vincular-contas-mediador",
                          description="[ADM] Posta o painel da fila de mediadores")
    async def vincular(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        data = db.load(interaction.guild.id)
        await postar_painel_mediador(interaction.channel, interaction.guild, data)
        await interaction.followup.send("✅ Painel de mediadores postado!", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Mediadores(bot))
