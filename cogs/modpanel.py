import discord
from discord import app_commands, ui
from discord.ext import commands
import sqlite3
import os
from dotenv import load_dotenv
from datetime import timedelta  # Import only timedelta

# Load environment variables
load_dotenv()
GUILD_ID = int(os.getenv('GUILD_ID'))
STAFF_ROLE = int(os.getenv('STAFF_ROLE'))
LOGS_CHANNEL = int(os.getenv('LOGS_CHANNEL'))

# Initialize the SQLite DB (create table if it doesn't exist)
def init_db():
    conn = sqlite3.connect('dcpunishments.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS punishments (
                    user_id INTEGER,
                    staff_id INTEGER,
                    punishment_type TEXT,
                    reason TEXT,
                    time TEXT
                )''')
    conn.commit()
    conn.close()

# Function to log punishments to the database
def log_punishment(user_id, staff_id, punishment_type, reason, time):
    conn = sqlite3.connect('dcpunishments.db')
    c = conn.cursor()
    c.execute('INSERT INTO punishments VALUES (?, ?, ?, ?, ?)',
              (user_id, staff_id, punishment_type, reason, time))
    conn.commit()
    conn.close()

# Function to retrieve previous punishments for a user
def get_previous_punishments(user_id):
    conn = sqlite3.connect('dcpunishments.db')
    c = conn.cursor()
    c.execute('SELECT * FROM punishments WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

# Define a select menu for punishment types
class PunishmentSelect(ui.Select):
    def __init__(self, user, staff):
        self.user = user
        self.staff = staff
        options = [
            discord.SelectOption(label="Warn", description="Warn the user"),
            discord.SelectOption(label="Timeout", description="Put the user in timeout"),
            discord.SelectOption(label="Remove Timeout", description="Remove user's timeout"),
            discord.SelectOption(label="Kick", description="Kick the user from the server"),
            discord.SelectOption(label="Ban", description="Ban the user from the server")
        ]
        super().__init__(placeholder="Choose punishment", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Timeout":
            await interaction.response.send_modal(TimeoutModal(self.user, self.staff, self.values[0]))
        else:
            await interaction.response.send_modal(PunishmentModal(self.user, self.staff, self.values[0]))

# Define a modal for entering the punishment reason
class PunishmentModal(ui.Modal, title="Punishment Panel"):
    reason = ui.TextInput(label="Reason for punishment", style=discord.TextStyle.paragraph)

    def __init__(self, user, staff, punishment_type):
        super().__init__()
        self.user = user
        self.staff = staff
        self.punishment_type = punishment_type

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason.value
        if self.punishment_type == "Kick":
            await self.user.kick(reason=reason)
        elif self.punishment_type == "Ban":
            await self.user.ban(reason=reason)
        elif self.punishment_type == "Warn":
            pass  # Add warning logic if needed
        elif self.punishment_type == "Remove Timeout":
            await self.user.timeout(None)
        
        log_punishment(self.user.id, self.staff.id, self.punishment_type, reason, "-")
        
        try:
            await self.user.send(f"You have been {self.punishment_type.lower()}ed. Reason: {reason}")
        except:
            pass

        logs_channel = interaction.guild.get_channel(LOGS_CHANNEL)
        embed = discord.Embed(title=self.punishment_type, color=discord.Color.red())
        embed.add_field(name="User", value=f"<@{self.user.id}>", inline=True)
        embed.add_field(name="Staff", value=f"<@{self.staff.id}>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        await logs_channel.send(embed=embed)
        await interaction.response.send_message(f"Punishment `{self.punishment_type}` applied to {self.user}.", ephemeral=True)

# Define a modal for timeouts
class TimeoutModal(ui.Modal, title="Punishment Panel"):
    reason = ui.TextInput(label="Reason for punishment", style=discord.TextStyle.paragraph)
    timeout_duration = ui.TextInput(label="Time for the timeout (In minutes)", style=discord.TextStyle.short)

    def __init__(self, user, staff, punishment_type):
        super().__init__()
        self.user = user
        self.staff = staff
        self.punishment_type = punishment_type

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason.value
        
        try:
            timeout_duration = int(self.timeout_duration.value)  # Ensuring the input is a valid integer
        except ValueError:
            await interaction.response.send_message("Please enter a valid number of minutes.", ephemeral=True)
            return
        
        # Calculate the timeout duration
        timeout_time = timedelta(minutes=timeout_duration)
        
        # Apply timeout using aware datetime (discord.utils.utcnow())
        await self.user.timeout(discord.utils.utcnow() + timeout_time)  # Apply timeout
        
        log_punishment(self.user.id, self.staff.id, self.punishment_type, reason, str(timeout_duration))
        
        try:
            await self.user.send(f"You have been timed out for {timeout_duration} minutes. Reason: {reason}")
        except:
            pass

        logs_channel = interaction.guild.get_channel(LOGS_CHANNEL)
        embed = discord.Embed(title="Timeout", color=discord.Color.red())
        embed.add_field(name="User", value=f"<@{self.user.id}>", inline=True)
        embed.add_field(name="Staff", value=f"<@{self.staff.id}>", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Time", value=f"{timeout_duration} minutes", inline=False)
        await logs_channel.send(embed=embed)
        await interaction.response.send_message(f"Timeout applied to {self.user} for {timeout_duration} minutes.", ephemeral=True)

# The main mod panel command
class ModPanel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        init_db()

    @app_commands.command(name="modpanel", description="Open the mod panel for a user")
    @app_commands.checks.has_role(STAFF_ROLE)
    @app_commands.describe(user="The user to moderate")
    async def modpanel(self, interaction: discord.Interaction, user: discord.Member):
        staff = interaction.user
        
        punishments = get_previous_punishments(user.id)
        punishments_text = ""
        for idx, punishment in enumerate(punishments, start=1):
            punishments_text += f"{idx}. {punishment[2]}\n   Staff: <@{punishment[1]}>\n   Reason: {punishment[3]}\n"

        embed = discord.Embed(title=f"Mod-Panel on {user.display_name}", color=discord.Color.purple())
        embed.add_field(name="Previous Punishments", value=punishments_text or "No previous punishments.", inline=False)
        await interaction.response.send_message(embed=embed, view=PunishmentView(user, staff))

class PunishmentView(ui.View):
    def __init__(self, user, staff):
        super().__init__()
        self.add_item(PunishmentSelect(user, staff))

# Cog setup function
async def setup(bot):
    await bot.add_cog(ModPanel(bot), guilds=[discord.Object(id=GUILD_ID)])  # Register the command for the guild directly
