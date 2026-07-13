"""
cogs/cargos.py — Sistema de cargos temporários com renovação automática
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from utils import database as db


def dias_restantes(vencimento_str):
    try:
        venc = datetime.fromisoformat(vencimento_str)
        diff = venc - datetime.now()
        return diff.days
    except Exception:
        return -1


class Cargos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verificar_vencimentos.start()

    def cog_unload(self):
        self.verificar_vencimentos.cancel()

    @tasks.loop(hours=1)
    async def verificar_vencimentos(self):
        for guild in self.bot.guilds:
            data = db.load(guild.id)
            cargos = data.get("cargos_temp", {})
            config = data.get("config", {})
            canal_id = config.get("canal_cargos_aviso")
            canal = guild.get_channel(canal_id) if canal_id else None
            pix = config.get("pix_cargos", "Nao configurado")
            alterado = False

            for uid, info in list(cargos.items()):
                dias = dias_restantes(info["vencimento"])
                membro = guild.get_member(int(uid))
                cargo = guild.get_role(info["cargo_id"])

                if dias == 1 and not info.get("aviso_enviado"):
                    if canal and membro and cargo:
                        embed = discord.Embed(title="Cargo vencendo amanha!", color=discord.Color.yellow())
                        embed.description = membro.mention + ", seu cargo **" + cargo.name + "** vence amanha!"
                        embed.add_field(name="Para renovar, pague via PIX:", value="`" + pix + "`", inline=False)
                        embed.add_field(name="Valor", value="R$ " + str(info.get("valor", "?")), inline=True)
                        embed.add_field(name="Vencimento", value=info["vencimento"][:10], inline=True)
                        embed.set_footer(text="Apos o pagamento, aguarde a confirmacao do admin.")
                        await canal.send(embed=embed)
                    cargos[uid]["aviso_enviado"] = True
                    alterado = True

                elif dias < 0:
                    if membro and cargo and cargo in membro.roles:
                        try:
                            await membro.remove_roles(cargo, reason="Cargo temporario vencido")
                            if canal:
                                embed = discord.Embed(title="Cargo removido", color=discord.Color.red())
                                embed.description = membro.mention + ", seu cargo **" + cargo.name + "** foi removido por vencimento."
                                embed.add_field(name="Para renovar:", value="`" + pix + "`", inline=False)
                                await canal.send(embed=embed)
                        except Exception:
                            pass
                    del cargos[uid]
                    alterado = True

            if alterado:
                data["cargos_temp"] = cargos
                db.save(guild.id, data)

    @verificar_vencimentos.before_loop
    async def before_verificar(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="cargo-dar", description="[ADM] Da um cargo temporario a um usuario")
    async def cargo_dar(self, interaction: discord.Interaction,
                        usuario: discord.Member,
                        cargo: discord.Role,
                        dias: int,
                        valor: str = "0"):
        data = db.load(interaction.guild.id)
        if "cargos_temp" not in data:
            data["cargos_temp"] = {}

        vencimento = (datetime.now() + timedelta(days=dias)).isoformat()
        data["cargos_temp"][str(usuario.id)] = {
            "cargo_id": cargo.id,
            "cargo_nome": cargo.name,
            "vencimento": vencimento,
            "dias": dias,
            "valor": valor,
            "aviso_enviado": False,
            "dado_em": datetime.now().isoformat(),
            "dado_por": interaction.user.id,
        }
        db.save(interaction.guild.id, data)

        try:
            await usuario.add_roles(cargo, reason="Cargo temporario por " + str(dias) + " dias")
        except Exception as e:
            await interaction.response.send_message("Erro ao dar cargo: " + str(e), ephemeral=True)
            return

        embed = discord.Embed(title="Cargo Temporario Atribuido", color=discord.Color.green())
        embed.add_field(name="Usuario", value=usuario.mention, inline=True)
        embed.add_field(name="Cargo", value=cargo.mention, inline=True)
        embed.add_field(name="Dias", value=str(dias), inline=True)
        embed.add_field(name="Vencimento", value=vencimento[:10], inline=True)
        embed.add_field(name="Valor pago", value="R$ " + valor, inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cargo-renovar", description="[ADM] Renova o cargo temporario de um usuario")
    async def cargo_renovar(self, interaction: discord.Interaction,
                            usuario: discord.Member,
                            dias: int):
        data = db.load(interaction.guild.id)
        cargos = data.get("cargos_temp", {})
        uid = str(usuario.id)

        if uid not in cargos:
            await interaction.response.send_message("Usuario nao tem cargo temporario registrado.", ephemeral=True)
            return

        info = cargos[uid]
        venc_atual = datetime.fromisoformat(info["vencimento"])
        base = max(venc_atual, datetime.now())
        novo_vencimento = (base + timedelta(days=dias)).isoformat()
        cargos[uid]["vencimento"] = novo_vencimento
        cargos[uid]["aviso_enviado"] = False
        data["cargos_temp"] = cargos
        db.save(interaction.guild.id, data)

        cargo = interaction.guild.get_role(info["cargo_id"])
        if cargo and cargo not in usuario.roles:
            try:
                await usuario.add_roles(cargo, reason="Renovacao de cargo temporario")
            except Exception:
                pass

        embed = discord.Embed(title="Cargo Renovado!", color=discord.Color.blurple())
        embed.add_field(name="Usuario", value=usuario.mention, inline=True)
        embed.add_field(name="Cargo", value=cargo.mention if cargo else info["cargo_nome"], inline=True)
        embed.add_field(name="Dias adicionados", value=str(dias), inline=True)
        embed.add_field(name="Novo vencimento", value=novo_vencimento[:10], inline=True)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cargo-ver", description="Veja quando seu cargo vence")
    async def cargo_ver(self, interaction: discord.Interaction, usuario: discord.Member = None):
        alvo = usuario or interaction.user
        data = db.load(interaction.guild.id)
        cargos = data.get("cargos_temp", {})
        uid = str(alvo.id)

        if uid not in cargos:
            await interaction.response.send_message(alvo.mention + " nao tem cargo temporario registrado.", ephemeral=True)
            return

        info = cargos[uid]
        dias = dias_restantes(info["vencimento"])
        cargo = interaction.guild.get_role(info["cargo_id"])

        embed = discord.Embed(title="Cargo Temporario", color=discord.Color.blurple())
        embed.set_thumbnail(url=alvo.display_avatar.url)
        embed.add_field(name="Usuario", value=alvo.mention, inline=True)
        embed.add_field(name="Cargo", value=cargo.mention if cargo else info["cargo_nome"], inline=True)
        embed.add_field(name="Vencimento", value=info["vencimento"][:10], inline=True)

        if dias < 0:
            status = "Vencido"
        elif dias == 0:
            status = "Vence hoje!"
        elif dias == 1:
            status = "Vence amanha!"
        else:
            status = str(dias) + " dias restantes"

        embed.add_field(name="Status", value=status, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cargo-listar", description="[ADM] Lista todos os cargos temporarios ativos")
    async def cargo_listar(self, interaction: discord.Interaction):
        data = db.load(interaction.guild.id)
        cargos = data.get("cargos_temp", {})

        if not cargos:
            await interaction.response.send_message("Nenhum cargo temporario ativo.", ephemeral=True)
            return

        embed = discord.Embed(title="Cargos Temporarios Ativos", color=discord.Color.blurple())
        linhas = []
        for uid, info in sorted(cargos.items(), key=lambda x: x[1]["vencimento"]):
            membro = interaction.guild.get_member(int(uid))
            nome = membro.mention if membro else "ID:" + uid
            dias = dias_restantes(info["vencimento"])
            cargo = interaction.guild.get_role(info["cargo_id"])
            cargo_nome = cargo.name if cargo else info["cargo_nome"]
            if dias < 0:
                status = "Vencido"
            elif dias <= 3:
                status = str(dias) + "d (urgente)"
            else:
                status = str(dias) + "d"
            linhas.append(nome + " -> **" + cargo_nome + "** — " + status)

        embed.description = "\n".join(linhas[:20])
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="cargo-remover", description="[ADM] Remove cargo temporario de um usuario")
    async def cargo_remover(self, interaction: discord.Interaction, usuario: discord.Member):
        data = db.load(interaction.guild.id)
        cargos = data.get("cargos_temp", {})
        uid = str(usuario.id)

        if uid not in cargos:
            await interaction.response.send_message("Sem cargo temporario registrado.", ephemeral=True)
            return

        info = cargos[uid]
        cargo = interaction.guild.get_role(info["cargo_id"])
        if cargo and cargo in usuario.roles:
            try:
                await usuario.remove_roles(cargo, reason="Remocao manual de cargo temporario")
            except Exception:
                pass

        del cargos[uid]
        data["cargos_temp"] = cargos
        db.save(interaction.guild.id, data)
        await interaction.response.send_message("Cargo temporario de " + usuario.mention + " removido.", ephemeral=True)

    @app_commands.command(name="cargo-config", description="[ADM] Configura canal de avisos e PIX")
    async def cargo_config(self, interaction: discord.Interaction,
                           canal: discord.TextChannel,
                           pix: str,
                           valor_padrao: str = "0"):
        data = db.load(interaction.guild.id)
        data["config"]["canal_cargos_aviso"] = canal.id
        data["config"]["pix_cargos"] = pix
        data["config"]["valor_padrao_cargo"] = valor_padrao
        db.save(interaction.guild.id, data)

        embed = discord.Embed(title="Configuracao de Cargos", color=discord.Color.green())
        embed.add_field(name="Canal de avisos", value=canal.mention, inline=True)
        embed.add_field(name="PIX", value="`" + pix + "`", inline=True)
        embed.add_field(name="Valor padrao", value="R$ " + valor_padrao, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Cargos(bot))
