# main.py
import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import timedelta
from keep_alive import keep_alive

keep_alive()

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Dictionaries
afk_users = {}
warns = {}

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you, be good or I'll spank"))
    print(f"✅ {bot.user} is online!")

#################################
# --- MODERATION COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member = None, duration: int = None, *, reason: str = None):
    if not member or not duration or not reason:
        return await ctx.send("⚠️ Usage: %timeout @user seconds reason")
    try:
        await member.timeout(timedelta(seconds=duration), reason=reason)
        await ctx.send(embed=make_mod_embed("⏳ Timeout Issued", ctx, member, reason, duration))
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this user.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: %ban @user reason")
    try:
        await member.ban(reason=reason)
        await ctx.send(embed=make_mod_embed("🔨 User Banned", ctx, member, reason))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: %kick @user reason")
    try:
        await member.kick(reason=reason)
        await ctx.send(embed=make_mod_embed("👢 User Kicked", ctx, member, reason))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: %mute @user reason")
    
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        try:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False)
        except discord.Forbidden:
            return await ctx.send("❌ I don't have permission to create the Muted role.")

    try:
        await member.add_roles(mute_role, reason=reason)
        await ctx.send(embed=make_mod_embed("🔇 User Muted", ctx, member, reason))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member = None):
    if not member:
        return await ctx.send("⚠️ Mention a user to unmute.")
    
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role or mute_role not in member.roles:
        return await ctx.send("⚠️ User is not muted.")

    try:
        await member.remove_roles(mute_role)
        await ctx.send(f"🔊 {member.mention} has been unmuted.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: %warn @user reason")
    
    warns.setdefault(member.id, []).append(reason)
    await ctx.send(embed=make_mod_embed("⚠️ User Warned", ctx, member, reason))

@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        return await ctx.send("⚠️ Usage: %softban @user reason")

    try:
        await member.ban(reason=reason, delete_message_days=1)
        await asyncio.sleep(1)  # slight delay to avoid hammering
        await ctx.guild.unban(discord.Object(id=member.id))
        await ctx.send(embed=make_mod_embed("🧹 Softban Executed", ctx, member, reason))
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

#####################################
# --- BASIC/INFO COMMANDS --- #
#####################################

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    embed = discord.Embed(title="🛌 AFK Activated", description=f"{ctx.author.mention} is now AFK: {reason}", color=discord.Color.blurple())
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member}'s Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"))
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    if amount < 1:
        return await ctx.send("⚠️ Amount must be positive.")
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Cleared {amount} messages.", delete_after=5)

#################################
# --- ROLE & CHANNEL COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Channel locked.")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Channel unlocked.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        return await ctx.send("⚠️ Usage: %giverole @user RoleName")
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send("❌ Role not found.")
    await member.add_roles(role)
    await ctx.send(f"✅ {member.mention} was given the **{role.name}** role.")

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        return await ctx.send("⚠️ Usage: %removerole @user RoleName")
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send("❌ Role not found.")
    await member.remove_roles(role)
    await ctx.send(f"🗑️ {role.name} role removed from {member.mention}.")

#################################
# --- AFK & EVENTS --- #
#################################

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto remove AFK status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        await message.channel.send(f"🎉 {message.author.mention}, welcome back! Your AFK status was removed.")

    # Notify if pinging AFK users
    for mention in message.mentions:
        if mention.id in afk_users:
            await message.channel.send(f"📨 {mention.display_name} is AFK: {afk_users[mention.id]}")

    await bot.process_commands(message)

# Invite Tracking System
@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")
    bot.invites = {}
    for guild in bot.guilds:
        bot.invites[guild.id] = await guild.invites()

@bot.event
async def on_invite_create(invite):
    bot.invites[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_invite_delete(invite):
    bot.invites[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_member_join(member):
    welcome_channel_id = 1363797902291374110
    welcome_channel = bot.get_channel(welcome_channel_id)

    if welcome_channel is None:
        print("Welcome channel not found!")
        return

    # Find the inviter
    invites_before = bot.invites.get(member.guild.id, [])
    invites_after = await member.guild.invites()

    inviter = None
    for invite in invites_before:
        for new_invite in invites_after:
            if invite.code == new_invite.code and invite.uses < new_invite.uses:
                inviter = invite.inviter
                break
        if inviter:
            break

    # Update invites cache
    bot.invites[member.guild.id] = invites_after

    inviter_name = inviter.name if inviter else "Unknown"

    # Welcome messages with emojis
    welcome_messages = [
        f"🎉 Welcome {member.mention} to the server! Invited by **{inviter_name}**! Let's get this party started! 🎊",
        f"👋 Hey {member.mention}, welcome aboard! Huge thanks to **{inviter_name}** for the invite! 🙌",
        f"🚀 {member.mention} just landed! Invited by **{inviter_name}**! Let's make some memories! 💥",
        f"🎮 Welcome {member.mention}, our newest player! Invited by the awesome **{inviter_name}**! 🙏",
        f"🌟 {member.mention} has joined the crew! Big shoutout to **{inviter_name}** for the invite! 💯",
        f"💫 Welcome {member.mention}! **{inviter_name}** is the legend who brought you here! 🌈",
        f"🔥 {member.mention} just arrived! Invited by the one and only **{inviter_name}**! 🌟",
        f"🏆 Cheers {member.mention}! **{inviter_name}** did an amazing job bringing you here! 🥳",
        f"🎉 A new member, {member.mention}! Huge thanks to **{inviter_name}** for the invite! 🎈",
        f"🎤 Everyone, please welcome {member.mention} to the fam! Invited by **{inviter_name}**! 🙌",
        f"🚀 {member.mention} has arrived! Big shoutout to **{inviter_name}** for the invite! Let's make it epic! 🎮",
        f"💥 Welcome {member.mention}! Thanks to **{inviter_name}**, the legend who made this happen! 💪",
        f"🌍 {member.mention} just joined us! **{inviter_name}** is the one who brought you here! 🎉",
        f"🌟 Hey {member.mention}, welcome! Thanks to **{inviter_name}** for the warm invite! 🌈",
        f"🎉 A warm welcome to {member.mention}! **{inviter_name}** is the MVP here! 💯",
        f"🎈 Hooray, {member.mention} is here! Invited by **{inviter_name}**, let's make this a blast! 🎉",
        f"🎮 Welcome {member.mention}, ready to join the action! Thanks to **{inviter_name}** for the invite! 🚀",
        f"🎉 Woohoo! {member.mention} has joined! Shoutout to **{inviter_name}** for the invite! 🔥"
    ]

    welcome_message = random.choice(welcome_messages)
    await welcome_channel.send(welcome_message)


# Run bot
bot.run(os.getenv('TOKEN'))
