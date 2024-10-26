import discord
from discord.ext import commands
from discord import app_commands
import os

class SessionVote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.vote_count = 0
        self.vote_message = None
        self.required_votes = 7
        self.ssu_permission_role_id = int(os.getenv('SSU_PERMISSION'))

    @app_commands.command(name="sessionvote", description="Request a session vote")
    async def sessionvote(self, interaction: discord.Interaction):
        member = interaction.guild.get_member(interaction.user.id)
        ssu_role = discord.utils.get(member.roles, id=self.ssu_permission_role_id)
        if not ssu_role:
            await interaction.response.send_message("You don't have the required role to run this command.", ephemeral=True)
            return
        embed = discord.Embed(
            title="Session Vote",
            description=f"A session has been requested by {interaction.user.mention}\n"
                        f"Number of votes needed: {self.required_votes}\n"
                        "If you vote during this time, you are required to join within 15 minutes of the server opening in-game.",
            color=discord.Color.blue()
        )
        self.vote_count = 0
        self.vote_message = await interaction.channel.send(
            content="@everyone",
            embed=embed,
            view=self.VoteView(self)
        )
        await interaction.response.send_message("Session vote has been initiated.", ephemeral=True)

    class VoteView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
            self.vote_button = discord.ui.Button(
                label=f"Votes: {self.cog.vote_count}",
                style=discord.ButtonStyle.green
            )
            self.vote_button.callback = self.vote_callback
            self.add_item(self.vote_button)

        async def vote_callback(self, interaction: discord.Interaction):
            self.cog.vote_count += 1
            self.vote_button.label = f"Votes: {self.cog.vote_count}"
            await interaction.message.edit(view=self)
            if self.cog.vote_count >= self.cog.required_votes:
                self.vote_button.disabled = True
                await interaction.message.edit(view=self)
                await interaction.user.send("The minimum votes needed for a session has been reached.")
            else:
                await interaction.response.defer()

async def setup(bot):
    cog = SessionVote(bot)
    await bot.add_cog(cog)
    if not bot.tree.get_command("sessionvote"):
        bot.tree.add_command(cog.sessionvote)
    guild = discord.Object(id=int(os.getenv('GUILD_ID')))
    await bot.tree.sync(guild=guild)
