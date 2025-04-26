from keep_alive import keep_alive
keep_alive()
import discord
from discord.ext import commands, tasks
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

    # List of founder user IDs
    founder_ids = [1327923421442736180,1097776051393929227,904290766225027083]  # replace with actual Discord user IDs

    founders = []
    for founder_id in founder_ids:
        user = guild.get_member(founder_id)
        if user:
            founders.append(user.mention)

    founder_list = ", ".join(founders) if founders else "Not Found"

    embed = discord.Embed(
        title=f"Server Info - {guild.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

    embed.add_field(name="👑 Founders", value=founder_list, inline=False)
    embed.add_field(name="📅 Created On", value=guild.created_at.strftime("%B %d, %Y"), inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🔐 Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="🌍 Region", value=str(guild.preferred_locale).capitalize(), inline=True)

    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! 🏓 `{round(bot.latency * 1000)}ms`")

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    await ctx.send(member.avatar.url)

import random

@bot.command(name="8ball")
async def eight_ball(ctx, *, question):
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


# Store sticky messages
sticky_data = {}

@bot.command()
@commands.has_permissions(manage_messages=True)
async def sticky(ctx, channel: discord.TextChannel, *, message):
    """Set a sticky message in a channel."""
    sticky_data[channel.id] = {"message": message, "last_message_id": None}
    
    # Send the first sticky
    sent_message = await channel.send(message)
    sticky_data[channel.id]["last_message_id"] = sent_message.id
    
    await ctx.send(f"✅ Sticky message set for {channel.mention}.")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def removesticky(ctx, channel: discord.TextChannel):
    """Remove sticky message from a channel."""
    if channel.id in sticky_data:
        del sticky_data[channel.id]
        await ctx.send(f"🗑️ Sticky message removed from {channel.mention}.")
    else:
        await ctx.send(f"❌ No sticky message found in {channel.mention}.")

# Listen to every new message
@bot.event
async def on_message(message):
    await bot.process_commands(message)  # Important to allow other commands

    if message.author.bot:
        return

    if message.channel.id in sticky_data:
        # Delete old sticky
        try:
            old_message_id = sticky_data[message.channel.id]["last_message_id"]
            old_message = await message.channel.fetch_message(old_message_id)
            await old_message.delete()
        except:
            pass  # maybe deleted already

        # Send new sticky
        new_sticky = await message.channel.send(sticky_data[message.channel.id]["message"])
        sticky_data[message.channel.id]["last_message_id"] = new_sticky.id

import os

# -- Invite Tracking --
invites_cache = {}
user_invite_counts = {}

WELCOME_CHANNEL_ID = 1363797902291374110  # Your welcome channel ID

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    # Cache invites when bot starts
    for guild in bot.guilds:
        invites_cache[guild.id] = await guild.invites()

@bot.event
async def on_member_join(member):
    await asyncio.sleep(1)  # slight delay so invites update

    guild = member.guild
    before_invites = invites_cache.get(guild.id, [])
    after_invites = await guild.invites()
    invites_cache[guild.id] = after_invites

    inviter = None
    for invite in after_invites:
        for old_invite in before_invites:
            if invite.code == old_invite.code and invite.uses > old_invite.uses:
                inviter = invite.inviter
                break
        if inviter:
            break

    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if welcome_channel:
        if inviter:
            user_invite_counts[inviter.id] = user_invite_counts.get(inviter.id, 0) + 1
            await welcome_channel.send(
                f"👋 Welcome {member.mention} to **Veracity**!\n"
                f"🎉 Invited by **{inviter.name}**."
            )
        else:
            await welcome_channel.send(
                f"👋 Welcome {member.mention} to **Veracity**!\n"
                f"🎉 Couldn't detect who invited you."
            )

@bot.event
async def on_member_remove(member):
    guild = member.guild
    invites_cache[guild.id] = await guild.invites()

# -- Commands --

@bot.command()
async def invites(ctx, member: discord.Member = None):
    """Check how many invites a user has."""
    member = member or ctx.author
    invites = user_invite_counts.get(member.id, 0)
    await ctx.send(f"🔗 {member.mention} has **{invites}** invites!")

@bot.command()
async def inviteleaderboard(ctx):
    """Top inviters leaderboard."""
    sorted_invites = sorted(user_invite_counts.items(), key=lambda x: x[1], reverse=True)
    pages = []
    
    for i in range(0, len(sorted_invites), 10):
        chunk = sorted_invites[i:i+10]
        description = ""
        for index, (user_id, count) in enumerate(chunk, start=i+1):
            user = ctx.guild.get_member(user_id)
            if user:
                description += f"**{index}.** {user.name} — {count} invites\n"
            else:
                description += f"**{index}.** Unknown User — {count} invites\n"
        
        embed = discord.Embed(
            title="🏆 Invite Leaderboard",
            description=description,
            color=discord.Color.gold()
        )
        pages.append(embed)

    if not pages:
        await ctx.send("❌ No invites to display yet!")
        return

    current_page = 0
    message = await ctx.send(embed=pages[current_page])

    await message.add_reaction("⏪")
    await message.add_reaction("⏩")

    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["⏪", "⏩"] and reaction.message.id == message.id

    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)

            if str(reaction.emoji) == "⏩":
                if current_page < len(pages) - 1:
                    current_page += 1
                    await message.edit(embed=pages[current_page])
            elif str(reaction.emoji) == "⏪":
                if current_page > 0:
                    current_page -= 1
                    await message.edit(embed=pages[current_page])

            await message.remove_reaction(reaction, user)
        except Exception:
            break
            
bot.run(os.getenv('TOKEN'))

