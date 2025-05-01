import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import timedelta
from keep_alive import keep_alive
import random
import json
from collections import defaultdict

keep_alive()

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Dictionaries
afk_users = {}
warns = {}
bot.invites = {}
bot.invite_counts = defaultdict(lambda: defaultdict(int))  # guild_id -> {user_id: count}
invite_cache = {}

# Token system
AUTHORIZED_GIVERS = [1327923421442736180, 1097776051393929227, 904290766225027083]  # Replace with real IDs
TOKEN_FILE = 'tokens.json'
WELCOME_CHANNEL_ID = 1363797902291374110  # Change this to your channel ID

# Rate limit settings
MESSAGE_QUEUE_MAX_SIZE = 5
MESSAGE_SEND_INTERVAL = 0.5
message_queue = asyncio.Queue(maxsize=MESSAGE_QUEUE_MAX_SIZE)
is_processing_queue = False

# Shop items
SHOP_ITEMS = {
    "brawl pass": {
        "price": 20000,
        "role_name": "Brawl Pass"
    },
    "nitro 1 month": {
        "price": 18000,
        "role_name": "Nitro Winner"
    },
    "custom role with custom color": {
        "price": 1500,
        "role_name": "Custom Role"
    },
    "server updates/sneak peeks": {
        "price": 1000,
        "role_name": "Sneak Peek Access"
    }
}

welcome_messages = [
    "👋 Hey {0.mention}! You were invited by **{1}** 🎉. Welcome aboard!",
    "🚀 Sup {0.mention}! **{1}** brought you here. Let's roll! 😎",
    "🎉 {0.mention} joined us, thanks to **{1}**! Welcome to the chaos 😈",
    "🌟 Look who's here – {0.mention}! Big thanks to **{1}** for the invite!",
    "🤝 {0.mention} joined! Give **{1}** a cookie 🍪 for the invite.",
    "🎈 Yay! {0.mention} is here. Invited by the awesome **{1}**!",
    "✨ {0.mention} just landed! Thanks, **{1}**, you're amazing!",
    "💥 Welcome {0.mention}! **{1}** thinks you're a good fit 😁",
    "🎯 {0.mention} was recruited by **{1}**. Let the fun begin!",
    "📣 {0.mention} is here! Courtesy of **{1}**'s invite skills!",
    "👀 {0.mention} appeared! Looks like **{1}** summoned you 😄",
    "📬 {0.mention} accepted **{1}**'s invite! Time to party 🎊",
    "🏆 {0.mention} joins the crew! High five to **{1}** ✋",
    "🌐 Welcome {0.mention}! Credit goes to **{1}** for the invite!",
    "🔔 Ding dong! {0.mention} arrived via **{1}**'s invite 🛎️",
    "🎶 {0.mention} is in the house! Thanks to **{1}** 💃",
    "🌈 {0.mention} joined – blame **{1}** if things get wild 😜",
    "🕶️ {0.mention} pulled up. **{1}** knew you'd love it here.",
    "💎 New gem alert: {0.mention} – invited by **{1}**!",
    "🔥 {0.mention} is on fire already. Nice pull by **{1}**!"
]

# Utility functions
def make_embed(title, description, color=discord.Color.blue()):
    """Creates a standard embed."""
    return discord.Embed(title=title, description=description, color=color)

def make_mod_embed(title, ctx, member, reason=None, duration=None):
    """Creates an embed for moderation actions."""
    embed = discord.Embed(title=title, color=discord.Color.orange())
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Member", value=member.mention, inline=False)
    if reason:
        embed.add_field(name="Reason", value=reason, inline=False)
    if duration:
        embed.add_field(name="Duration", value=f"{duration} seconds", inline=False)
    return embed

async def send_with_rate_limit(destination, content=None, *, embed=None, file=None, view=None):
    """Adds a message to the send queue."""
    await message_queue.put((destination, content, embed, file, view))
    await process_message_queue()

async def process_message_queue():
    """Processes the message queue with rate limiting."""
    global is_processing_queue
    if is_processing_queue or message_queue.empty():
        return

    is_processing_queue = True
    while not message_queue.empty():
        destination, content, embed, file, view = await message_queue.get()
        try:
            await destination.send(content=content, embed=embed, file=file, view=view)
            await asyncio.sleep(MESSAGE_SEND_INTERVAL)
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Too Many Requests
                retry_after = e.retry_after
                print(f"⚠️ Rate limit hit! Retrying after {retry_after} seconds.")
                await asyncio.sleep(retry_after)
                await message_queue.put((destination, content, embed, file, view))
            else:
                print(f"❌ Error sending message: {e}")
        except Exception as e:
            print(f"❌ Error during message queue processing: {e}")
        finally:
            message_queue.task_done()
    is_processing_queue = False

# Token system functions
def load_tokens():
    if not os.path.exists(TOKEN_FILE):
        return {}
    with open(TOKEN_FILE, 'r') as f:
        return json.load(f)

def save_tokens(data):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_tokens(user_id, amount):
    tokens = load_tokens()
    user_id = str(user_id)
    tokens[user_id] = tokens.get(user_id, 0) + amount
    save_tokens(tokens)

def subtract_tokens(user_id, amount):
    tokens = load_tokens()
    user_id = str(user_id)
    if tokens.get(user_id, 0) >= amount:
        tokens[user_id] -= amount
        save_tokens(tokens)
        return True
    return False

def get_balance(user_id):
    tokens = load_tokens()
    return tokens.get(str(user_id), 0)

# Invite tracking functions
async def update_invite_cache():
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite for invite in invites}
        except discord.Forbidden:
            print(f"[WARN] Missing 'Manage Guild' permission in: {guild.name}")
        except Exception as e:
            print(f"[ERROR] Updating invite cache: {e}")

# Events
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you, be good or I'll spank"))
    print(f"✅ {bot.user} is online!")
    await update_invite_cache()

@bot.event
async def on_invite_create(invite):
    await update_invite_cache()

@bot.event
async def on_invite_delete(invite):
    await update_invite_cache()

@bot.event
async def on_member_join(member):
    guild = member.guild
    if guild.id not in invite_cache:
        await update_invite_cache()
        return
    
    try:
        new_invites = await guild.invites()
        used_invite = None
        for invite in new_invites:
            old_invite = invite_cache[guild.id].get(invite.code)
            if old_invite and invite.uses > old_invite.uses:
                used_invite = invite
                break
            elif not old_invite:
                used_invite = invite
                break

        inviter = used_invite.inviter if used_invite else "someone mysterious"
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            welcome_msg = random.choice(welcome_messages).format(member, inviter)
            await channel.send(welcome_msg)

        await update_invite_cache()
    except Exception as e:
        print(f"[Error in on_member_join] {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto remove AFK status
    if message.author.id in afk_users:
        del afk_users[message.author.id]
        embed = make_embed("🎉 Welcome Back!",
                         f"{message.author.mention}, welcome back! Your AFK status was removed.",
                         discord.Color.green())
        await send_with_rate_limit(message.channel, embed=embed)

    # Notify if pinging AFK users
    for mention in message.mentions:
        if mention.id in afk_users:
            embed = make_embed("📨 User is AFK",
                             f"{mention.display_name} is AFK: {afk_users[mention.id]}",
                             discord.Color.yellow())
            await send_with_rate_limit(message.channel, embed=embed)

    await bot.process_commands(message)

#################################
# --- MODERATION COMMANDS --- #
#################################
@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member = None, duration: int = None, *, reason: str = None):
    if not member or not duration or not reason:
        embed = make_embed("⚠️ Timeout Usage", "%timeout @user seconds reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        await member.timeout(timedelta(seconds=duration), reason=reason)
        await send_with_rate_limit(ctx, embed=make_mod_embed("⏳ Timeout Issued", ctx, member, reason, duration))
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied", "I don't have permission to timeout this user.", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        embed = make_embed("⚠️ Ban Usage", "%ban @user reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        await member.ban(reason=reason)
        await send_with_rate_limit(ctx, embed=make_mod_embed("🔨 User Banned", ctx, member, reason))
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied", "I don't have permission to ban this user.", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        embed = make_embed("⚠️ Kick Usage", "%kick @user reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        await member.kick(reason=reason)
        await send_with_rate_limit(ctx, embed=make_mod_embed("👢 User Kicked", ctx, member, reason))
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied", "I don't have permission to kick this user.", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        embed = make_embed("⚠️ Mute Usage", "%mute @user reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role:
        try:
            mute_role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(mute_role, send_messages=False, speak=False, connect=False)
            embed = make_embed("✅ Muted Role Created",
                             "Created the 'Muted' role and set channel permissions.",
                             discord.Color.green())
            await send_with_rate_limit(ctx, embed=embed)
        except discord.Forbidden:
            embed = make_embed("❌ Permission Denied",
                             "I don't have permission to create the 'Muted' role.",
                             discord.Color.red())
            await send_with_rate_limit(ctx, embed=embed)
            return

    try:
        await member.add_roles(mute_role, reason=reason)
        await send_with_rate_limit(ctx, embed=make_mod_embed("🔇 User Muted", ctx, member, reason))
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage roles for this user.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member = None):
    if not member:
        embed = make_embed("⚠️ Unmute Usage", "Mention a user to unmute.", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return

    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not mute_role or mute_role not in member.roles:
        embed = make_embed("⚠️ Not Muted", "User is not muted.", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return

    try:
        await member.remove_roles(mute_role)
        embed = make_embed("🔊 User Unmuted", f"{member.mention} has been unmuted.",
                         discord.Color.green())
        await send_with_rate_limit(ctx, embed=embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage roles for this user.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        embed = make_embed("⚠️ Warn Usage", "%warn @user reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return

    warns.setdefault(member.id, []).append(reason)
    await send_with_rate_limit(ctx, embed=make_mod_embed("⚠️ User Warned", ctx, member, reason))

@bot.command()
@commands.has_permissions(ban_members=True)
async def softban(ctx, member: discord.Member = None, *, reason: str = None):
    if not member or not reason:
        embed = make_embed("⚠️ Softban Usage", "%softban @user reason", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return

    try:
        await member.ban(reason=reason, delete_message_days=1)
        await asyncio.sleep(1)
        await ctx.guild.unban(discord.Object(id=member.id))
        await send_with_rate_limit(ctx, embed=make_mod_embed("🧹 Softban Executed", ctx, member, reason))
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to ban/unban this user.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = None):
    if amount is None or amount < 1:
        embed = make_embed("⚠️ Purge Usage", "%purge <amount>", discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)
        embed = make_embed("✅ Messages Cleared",
                         f"Successfully cleared {len(deleted) - 1} messages.",
                         discord.Color.green())
        await send_with_rate_limit(ctx, embed=embed, delete_after=5)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage messages in this channel.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

#####################################
# --- BASIC/INFO COMMANDS --- #
#####################################
@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    embed = make_embed("🛌 AFK Activated", f"{ctx.author.mention} is now AFK: {reason}",
                      discord.Color.blurple())
    await send_with_rate_limit(ctx, embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"{member}'s Info", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=member.display_avatar.url if member.display_avatar else None)
    await send_with_rate_limit(ctx, embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    
    # Replace these with your actual founders' user IDs
    FOUNDER_IDS = [1327923421442736180, 1097776051393929227, 904290766225027083]
    
    # Get founder members
    founders = []
    for user_id in FOUNDER_IDS:
        founder = guild.get_member(user_id)
        if founder:
            founders.append(founder.mention)
    
    # Format creation date
    created_at = guild.created_at.strftime("%B %d, %Y")
    days_since_creation = (ctx.message.created_at - guild.created_at).days
    
    embed = discord.Embed(
        title=f"🏰 {guild.name} Server Information",
        color=discord.Color.green()
    )
    
    # Server Basics
    embed.add_field(
        name="📅 Created On",
        value=f"{created_at} ({days_since_creation} days ago)",
        inline=False
    )
    
    # Members
    embed.add_field(
        name="👥 Members",
        value=guild.member_count,
        inline=True
    )
    
    # Channels
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    embed.add_field(
        name="📚 Channels",
        value=f"{text_channels + voice_channels} total\n({text_channels} text, {voice_channels} voice)",
        inline=True
    )
    
    # Roles
    embed.add_field(
        name="🎭 Roles",
        value=len(guild.roles),
        inline=True
    )
    
    # Boost Status
    if guild.premium_tier > 0:
        embed.add_field(
            name="🚀 Boost Level",
            value=f"Level {guild.premium_tier}\n{guild.premium_subscription_count} boosts",
            inline=True
        )
    
    # Founders Section
    if founders:
        embed.add_field(
            name="👑 Founders",
            value="\n".join(founders),
            inline=False
        )
    
    # Server Icon
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await ctx.send(embed=embed)
#################################
# --- ROLE & CHANNEL COMMANDS --- #
#################################
@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        embed = make_embed("🔒 Channel Locked",
                         f"This channel has been locked by {ctx.author.mention}.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage channel permissions.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    try:
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        embed = make_embed("🔓 Channel Unlocked",
                         f"This channel has been unlocked by {ctx.author.mention}.",
                         discord.Color.green())
        await send_with_rate_limit(ctx, embed=embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage channel permissions.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        embed = make_embed("⚠️ Giverole Usage", "%giverole @user RoleName",
                         discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        embed = make_embed("❌ Role Not Found", f"Role '{role_name}' not found.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        await member.add_roles(role)
        embed = make_embed("✅ Role Given",
                         f"Given the role **{role.name}** to {member.mention}.",
                         discord.Color.green())
        await send_with_rate_limit(ctx, embed=embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage roles for this user.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member = None, *, role_name=None):
    if not member or not role_name:
        embed = make_embed("⚠️ Removerole Usage", "%removerole @user RoleName",
                         discord.Color.yellow())
        await send_with_rate_limit(ctx, embed=embed)
        return
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        embed = make_embed("❌ Role Not Found", f"Role '{role_name}' not found.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
        return
    try:
        await member.remove_roles(role)
        embed = make_embed("🗑️ Role Removed",
                         f"Removed the **{role.name}** role from {member.mention}.",
                         discord.Color.green())
        await send_with_rate_limit(ctx, embed=embed)
    except discord.Forbidden:
        embed = make_embed("❌ Permission Denied",
                         "I don't have permission to manage roles for this user.",
                         discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)
    except Exception as e:
        embed = make_embed("❌ Error", f"An error occurred: {e}", discord.Color.red())
        await send_with_rate_limit(ctx, embed=embed)

#################################
# --- TOKEN SYSTEM COMMANDS --- #
#################################
@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_GIVERS:
        return await ctx.send("❌ You are not authorized to give tokens.")
    if amount <= 0:
        return await ctx.send("❌ Please enter a positive amount.")
    add_tokens(member.id, amount)
    await ctx.send(f"✅ Gave {amount} VRT tokens to {member.display_name}.")

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = get_balance(member.id)
    await ctx.send(f"💰 {member.display_name} has {bal} VRT tokens.")

@bot.command()
async def shop(ctx):
    embed = discord.Embed(title="🛒 VRT Token Shop", color=discord.Color.gold())
    for item, data in SHOP_ITEMS.items():
        embed.add_field(name=item.title(), value=f"{data['price']} VRT tokens", inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, member: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_GIVERS:
        return await ctx.send("❌ You are not authorized to remove tokens.")
    if amount <= 0:
        return await ctx.send("❌ Please enter a positive amount.")
    if subtract_tokens(member.id, amount):
        await ctx.send(f"❌ Removed {amount} VRT tokens from {member.display_name}.")
    else:
        await ctx.send("⚠️ User doesn't have enough tokens to remove.")

@bot.command()
async def buy(ctx, *, item_name: str):
    item_name = item_name.lower()
    if item_name not in SHOP_ITEMS:
        return await ctx.send("❌ That item doesn't exist in the shop.")

    item = SHOP_ITEMS[item_name]
    price = item['price']
    role_name = item['role_name']

    if subtract_tokens(ctx.author.id, price):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            role = await ctx.guild.create_role(name=role_name)
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ You bought **{item_name}** for {price} VRT tokens and received the **{role_name}** role!")
    else:
        await ctx.send("❌ You don't have enough VRT tokens.")

#################################
# --- APPLICATION COMMAND --- #
#################################
@bot.command()
async def apply(ctx):
    class AppDropdown(discord.ui.Select):
        def __init__(self):
            options = [
                discord.SelectOption(label="Tournament Staff", description="Apply as a Tournament Staff"),
                discord.SelectOption(label="Esports Staff", description="Apply as an Esports Staff"),
                discord.SelectOption(label="Clubs Manager", description="Apply as a Clubs Manager"),
                discord.SelectOption(label="Server Moderation", description="Apply for Moderation role"),
                discord.SelectOption(label="Collab application", description="Apply for a Collaboration/Sponsorship")
            ]
            super().__init__(placeholder="Choose Application Type", min_values=1, max_values=1, options=options)

        async def callback(self, interaction: discord.Interaction):
            form_url = "https://alphaenforcers.blogspot.com/p/apply-to-be-part-of-our-management.html"

            try:
                await interaction.user.send(
                    f"🎉 **Thanks for applying for {self.values[0]}!**\n📝 Fill your form here: {form_url}\n\nBe honest and detailed in your answers!"
                )
                await interaction.response.send_message("📩 We've sent you a DM with the application form. Please check your inbox!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("⚠️ I couldn't DM you. Please enable DMs and try again.", ephemeral=True)

    class AppDropdownView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=None)
            self.add_item(AppDropdown())

    embed = discord.Embed(
        title="📋 Applications for joining our staff team and for collaborations/sponsorships",
        description=(
            "Interested in joining our staff or have a good collab/sponsorship deal?\n"
            "🧠 Use the dropdown below to choose your application type and receive the form in DMs!"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Anshhhulll | VRT Board of Directors")
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty)

    await ctx.send(embed=embed, view=AppDropdownView())

@bot.event
async def on_message(message):
    # Ignore bots and allowed roles
    if message.author.bot:
        return
    
    allowed_roles = ["Board of Directors", "Associate Directors"]  # Change to your role names
    if any(role.name in allowed_roles for role in message.author.roles):
        await bot.process_commands(message)
        return
    
    # Check for Discord invites
    if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
        try:
            await message.delete()
        except:
            pass  # If we can't delete, just continue
            
        # Create warning embed
        embed = discord.Embed(
            title="⚠️ Discord Invites Not Allowed",
            description=f"{message.author.mention} No Discord invite links are permitted here!",
            color=0xFF0000  # Red color for warning
        )
        embed.add_field(
            name="Rule Violation",
            value="Posting invite links is against server rules",
            inline=False
        )
        
        # Send to both channel and user
        warning = await message.channel.send(embed=embed)
        try:
            await message.author.send(embed=embed)
        except:
            pass  # Couldn't DM user
        
        # Delete warning after 10 seconds
        await asyncio.sleep(10)
        await warning.delete()
    
    await bot.process_commands(message)

# Run bot
bot.run(os.getenv('TOKEN'))
