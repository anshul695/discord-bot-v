from keep_alive import keep_alive
keep_alive()
import discord
from discord.ext import commands, tasks
import os
from datetime import timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Dictionary for AFK users g
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


# Invite Cache
invites_cache = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for guild in bot.guilds:
        invites_cache[guild.id] = await guild.invites()

@bot.event
async def on_invite_create(invite):
    invites_cache[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_invite_delete(invite):
    invites_cache[invite.guild.id] = await invite.guild.invites()

@bot.event
async def on_member_join(member):
    await asyncio.sleep(2)  # Wait to make sure invites update

    invites_before = invites_cache.get(member.guild.id, [])
    invites_after = await member.guild.invites()

    inviter = None
    for invite in invites_before:
        for after_invite in invites_after:
            if invite.code == after_invite.code and invite.uses < after_invite.uses:
                inviter = invite.inviter
                break

    invites_cache[member.guild.id] = invites_after

    welcome_channel = bot.get_channel(YOUR_WELCOME_CHANNEL_ID)  # Replace with your welcome channel ID
    if inviter:
        await welcome_channel.send(f"👋 Welcome {member.mention} to Veracity!\nInvited by: **{inviter}**")
    else:
        await welcome_channel.send(f"👋 Welcome {member.mention} to Veracity!\nCouldn't find who invited you!")

# Command: %invites
@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)  # 1 use every 5 sec
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    total_invites = 0
    try:
        invites = await ctx.guild.invites()
        for invite in invites:
            if invite.inviter == member:
                total_invites += invite.uses
        await ctx.send(f"🔗 {member.mention} has **{total_invites}** invites!")
    except Exception as e:
        await ctx.send("❌ Failed to fetch invites. Try again later.")

# Command: %inviteleaderboard
@bot.command(name="inviteleaderboard")
@commands.cooldown(1, 10, commands.BucketType.user)
async def inviteleaderboard(ctx):
    try:
        invites = await ctx.guild.invites()
        invite_count = {}

        for invite in invites:
            if invite.inviter:
                invite_count[invite.inviter] = invite_count.get(invite.inviter, 0) + invite.uses

        if not invite_count:
            return await ctx.send("❌ No invites to display yet!")

        sorted_invites = sorted(invite_count.items(), key=lambda x: x[1], reverse=True)

        pages = []
        per_page = 10
        for i in range(0, len(sorted_invites), per_page):
            page = sorted_invites[i:i+per_page]
            description = ""
            for idx, (user, uses) in enumerate(page, start=i+1):
                description += f"**{idx}.** [{user}](https://discord.com/users/{user.id}) — **{uses} invites**\n"
            embed = discord.Embed(title="📈 Top Inviters", description=description, color=discord.Color.blurple())
            pages.append(embed)

        current_page = 0
        message = await ctx.send(embed=pages[current_page])

        if len(pages) > 1:
            await message.add_reaction("⬅️")
            await message.add_reaction("➡️")

            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

            while True:
                try:
                    reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                    if str(reaction.emoji) == "➡️" and current_page < len(pages) - 1:
                        current_page += 1
                        await message.edit(embed=pages[current_page])
                        await message.remove_reaction(reaction, user)
                    elif str(reaction.emoji) == "⬅️" and current_page > 0:
                        current_page -= 1
                        await message.edit(embed=pages[current_page])
                        await message.remove_reaction(reaction, user)
                    else:
                        await message.remove_reaction(reaction, user)
                except asyncio.TimeoutError:
                    break
    except Exception as e:
        await ctx.send("❌ Failed to fetch invite leaderboard. Try again later.")

import discord
from discord.ext import commands, tasks
from collections import defaultdict
import random

intents = discord.Intents.default()
intents.members = True  # IMPORTANT: Enable member intents
intents.guilds = True
intents.invites = True
intents.messages = True
intents.message_content = True  # Needed for commands

bot = commands.Bot(command_prefix="%", intents=intents)

# Invite cache to track who invited whom
invite_cache = {}

# Invite counts
user_invites = defaultdict(int)

# Welcome channel ID
WELCOME_CHANNEL_ID = 1363797902291374110

# Random welcome messages
welcome_messages = [
    "🎉 Welcome {member} to Veracity! Invited by {inviter}. Let's get the hype started! 🚀",
    "👋 Hey {member}, welcome aboard! Thanks to {inviter} for bringing you in!",
    "✨ {member} just joined us, brought here by {inviter}! Hope you have an amazing time!",
    "🔥 {member} landed into Veracity! A big shoutout to {inviter} for the invite!",
    "🎊 {member} has entered the arena! {inviter} made it happen!",
    "💥 {member} joins the chaos, thanks to {inviter}! Let's gooo!"
]

# Cache invites on bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    for guild in bot.guilds:
        invites = await guild.invites()
        invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
    print("Invite cache populated.")

# Update invite cache when invite is created or deleted
@bot.event
async def on_invite_create(invite):
    invites = await invite.guild.invites()
    invite_cache[invite.guild.id] = {i.code: i.uses for i in invites}

@bot.event
async def on_invite_delete(invite):
    invites = await invite.guild.invites()
    invite_cache[invite.guild.id] = {i.code: i.uses for i in invites}

# When a member joins
@bot.event
async def on_member_join(member):
    guild = member.guild
    try:
        # Fetch updated invites
        invites_after = await guild.invites()
        invites_before = invite_cache.get(guild.id, {})
        
        inviter = None
        for invite in invites_after:
            if invites_before.get(invite.code, 0) < invite.uses:
                inviter = invite.inviter
                user_invites[inviter.id] += 1
                break
        
        # Update cache
        invite_cache[guild.id] = {invite.code: invite.uses for invite in invites_after}

        # Pick a random welcome message
        welcome_msg = random.choice(welcome_messages)
        welcome_msg = welcome_msg.format(member=member.mention, inviter=inviter.name if inviter else "Unknown")
        
        # Send to welcome channel
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            await channel.send(welcome_msg)
        
    except Exception as e:
        print(f"Error handling member join: {e}")

# %invites command
@bot.command(name="invites")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = user_invites.get(member.id, 0)
    await ctx.send(f"📩 {member.mention} has **{count}** invites!")

# %inviteleaderboard command
@bot.command(name="inviteleaderboard", aliases=["inviteslb"])
async def invite_leaderboard(ctx, page: int = 1):
    entries = sorted(user_invites.items(), key=lambda x: x[1], reverse=True)
    per_page = 10
    pages = (len(entries) - 1) // per_page + 1
    if page > pages or page < 1:
        return await ctx.send(f"Invalid page number! There are only {pages} pages.")
    
    start = (page - 1) * per_page
    end = start + per_page
    leaderboard = ""
    for idx, (user_id, count) in enumerate(entries[start:end], start=start + 1):
        user = ctx.guild.get_member(user_id)
        if user:
            leaderboard += f"**{idx}.** {user.name} - **{count} invites**\n"
    
    embed = discord.Embed(
        title="🏆 Veracity Invite Leaderboard",
        description=leaderboard,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Page {page}/{pages}")
    await ctx.send(embed=embed)

bot.run(os.getenv('TOKEN'))

