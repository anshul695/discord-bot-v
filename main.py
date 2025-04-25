from keep_alive import keep_alive
keep_alive()
import discord
from discord.ext import commands
import os
from datetime import timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Dictionary for AFK users
afk_users = {}
# Dictionary for warnings
warns = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you, be good or I'll spank"))
    print(f'{bot.user} is online!')

# TIMEOUT command
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member = None, duration: int = None, *, reason: str = None):
    if not member or not duration or not reason:
        return await ctx.send("⚠️ Please mention a user, duration (in seconds), and a reason. Example: `%timeout @user 60 spamming`")

    await member.timeout(timedelta(seconds=duration), reason=reason)

    embed = discord.Embed(
        title="⏳ Timeout Issued",
        color=discord.Color.gold(),
        timestamp=ctx.message.created_at
    )
    embed.add_field(name="👤 User", value=member.mention)
    embed.add_field(name="⏱ Duration", value=f"{duration} seconds")
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# BAN command
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Please mention a user and a reason. Example: `%ban @user spamming`")

    await member.ban(reason=reason)

    embed = discord.Embed(
        title="🔨 User Banned",
        color=discord.Color.red(),
        timestamp=ctx.message.created_at
    )
    embed.add_field(name="👤 User", value=member.mention)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# KICK command
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Please mention a user and a reason. Example: `%kick @user being rude`")

    await member.kick(reason=reason)

    embed = discord.Embed(
        title="👢 User Kicked",
        color=discord.Color.orange(),
        timestamp=ctx.message.created_at
    )
    embed.add_field(name="👤 User", value=member.mention)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

# MUTE command (role-based)
@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Please mention a user and a reason. Example: `%mute @user spamming`")

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, speak=False, send_messages=False)

    await member.add_roles(mute_role, reason=reason)

    embed = discord.Embed(
        title="🔇 User Muted",
        color=discord.Color.dark_gray(),
        timestamp=ctx.message.created_at
    )
    embed.add_field(name="👤 User", value=member.mention)
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    if member is None or reason is None:
        await ctx.send("⚠️ Please mention a user and provide a reason. Example: `%warn @user spamming`")
        return

    if member.id not in warns:
        warns[member.id] = []

    warns[member.id].append(reason)

    embed = discord.Embed(
        title="⚠️ User Warned",
        description=f"{member.mention} has been warned.",
        color=discord.Color.orange()
    )
    embed.add_field(name="📝 Reason", value=reason, inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.timestamp = ctx.message.created_at

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member = None, *, reason: str = None):
    if not member:
        return await ctx.send("⚠️ Please mention a user to unmute. Example: `%unmute @user`")

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        return await ctx.send("⚠️ Muted role does not exist.")

    if mute_role not in member.roles:
        return await ctx.send(f"⚠️ {member.mention} is not muted.")

    await member.remove_roles(mute_role, reason=reason)

    embed = discord.Embed(
        title="🔊 User Unmuted",
        color=discord.Color.green(),
        timestamp=ctx.message.created_at
    )
    embed.add_field(name="👤 User", value=member.mention)
    embed.add_field(name="📝 Reason", value=reason if reason else "No reason provided", inline=False)
    embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
    await ctx.send(f"✅ Deleted {amount} messages.", delete_after=5)

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    embed = discord.Embed(
        title="🛌 AFK Activated",
        description=f"{ctx.author.mention} is now AFK: {reason}",
        color=discord.Color.blurple()
    )
    await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Remove AFK if the author was AFK
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        embed = discord.Embed(
            title="🎉 Welcome Back!",
            description=f"{message.author.mention}, your AFK status has been removed.",
            color=discord.Color.green()
        )
        await message.channel.send(embed=embed)

    # Let others know if they're pinging an AFK user
    for mention in message.mentions:
        if mention.id in afk_users:
            embed = discord.Embed(
                title="📨 User is AFK",
                description=f"{mention.display_name} is AFK: {afk_users[mention.id]}",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔒 Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔓 Channel unlocked.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        return await ctx.send("⚠️ Usage: `%giverole @user Role Name`")

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")

    await member.add_roles(role)
    await ctx.send(f"✅ {role.name} role has been given to {member.mention}.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        return await ctx.send("⚠️ Usage: `%removerole @user Role Name`")

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")

    await member.remove_roles(role)
    await ctx.send(f"🗑️ {role.name} role has been removed from {member.mention}.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: `%softban @user reason`")

    try:
        await member.ban(reason=reason, delete_message_days=1)
        await member.unban(member)
        embed = discord.Embed(
            title="🧹 User Softbanned",
            color=discord.Color.red(),
            timestamp=ctx.message.created_at
        )
        embed.add_field(name="👤 User", value=member.mention)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.add_field(name="👮 Moderator", value=ctx.author.mention, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member.name}'s Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"{guild.name} Server Info", color=discord.Color.green())
    embed.add_field(name="Owner", value=guild.owner)
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Created", value=guild.created_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.send(embed=embed)

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

import random

@bot.command()
async def _8ball(ctx, *, question):
    responses = [
        "Yes.", "No.", "Maybe.", "Definitely!", "Absolutely not.",
        "Ask again later.", "I'm not sure.", "Without a doubt.", "Nah.", "You wish."
    ]
    await ctx.send(f"🎱 {random.choice(responses)}")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="🛠️ VeraMod Bot Commands",
        description="Here are all the available commands categorized for you!",
        color=discord.Color.blue()
    )

    # 👥 Member Commands
    embed.add_field(
        name="👥 Member Commands",
        value=(
            "`%afk reason` – Set yourself as AFK\n"
            "`%userinfo @user` – View user information\n"
            "`%serverinfo` – View server information\n"
            "`%avatar @user` – View someone's avatar\n"
            "`%ping` – Check bot latency\n"
            "`%8ball question` – Ask the magic 8ball a question"
        ),
        inline=False
    )

    # 🔨 Moderation Commands (Mods & Admins Only)
    embed.add_field(
        name="🔨 Moderation Commands",
        value=(
            "`%ban @user reason` – Ban a user\n"
            "`%kick @user reason` – Kick a user\n"
            "`%mute @user reason` – Mute a user with Muted role\n"
            "`%unmute @user` – Unmute a muted user\n"
            "`%timeout @user seconds reason` – Timeout a user temporarily\n"
            "`%softban @user reason` – Ban and immediately unban (deletes messages)\n"
            "`%warn @user reason` – Warn a user\n"
            "`%removewarn @user` – Remove the latest warning for a user\n"
            "`%lock` – Lock the current channel\n"
            "`%unlock` – Unlock the current channel\n"
            "`%giverole @user Role Name` – Give a role to a user\n"
            "`%removerole @user Role Name` – Remove a role from a user"
        ),
        inline=False
    )

    # ⚙️ Utility Commands (Mods Only)
    embed.add_field(
        name="⚙️ Utility Commands",
        value=(
            "`%purge amount` – Delete messages in bulk"
        ),
        inline=False
    )

    # ℹ️ Footer
    embed.set_footer(text=f"Requested by {ctx.author}")

    await ctx.send(embed=embed)


import os

bot.run(os.getenv('TOKEN'))

