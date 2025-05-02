import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import datetime, timedelta
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
afk_data = {}  # {user_id: {"time": datetime, "mentions": int, "reason": str}}
warns = {}
bot.invites = {}
bot.invite_counts = defaultdict(lambda: defaultdict(int))
invite_cache = {}
invite_data = {}  # {guild_id: {invite_code: {uses: int, inviter: user_id}}}
invite_leaderboard = {}  # {guild_id: {user_id: invite_count}}

# Token system
AUTHORIZED_GIVERS = [1327923421442736180, 1097776051393929227, 904290766225027083]
TOKEN_FILE = 'tokens.json'
WELCOME_CHANNEL_ID = 1363797902291374110

# Rate limit settings
MESSAGE_QUEUE_MAX_SIZE = 5
MESSAGE_SEND_INTERVAL = 0.5
message_queue = asyncio.Queue(maxsize=MESSAGE_QUEUE_MAX_SIZE)
is_processing_queue = False

# Shop items
SHOP_ITEMS = {
    "brawl pass": {"price": 20000, "role_name": "Brawl Pass"},
    "nitro 1 month": {"price": 18000, "role_name": "Nitro Winner"},
    "custom role with custom color": {"price": 1500, "role_name": "Custom Role"},
    "server updates/sneak peeks": {"price": 1000, "role_name": "Sneak Peek Access"}
}

welcome_messages = [
    "👋 {0.mention} joined! Invited by **{1}** 🎉",
    "🚀 {0.mention} has arrived! Thanks to **{1}** 😎",
    "🎉 Welcome {0.mention}! Recruited by **{1}**",
    "🌟 {0.mention} is here! Shoutout to **{1}**",
    "🤝 {0.mention} joined via **{1}**'s invite"
]

# Utility functions
def make_embed(title=None, description=None, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Anshhhulll's Bot", icon_url="https://i.imgur.com/8Km9TLL.png")
    return embed

def make_mod_embed(title, ctx, member, reason=None, duration=None):
    embed = discord.Embed(title=title, color=discord.Color.orange())
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=False)
    embed.add_field(name="Member", value=member.mention, inline=False)
    if reason: embed.add_field(name="Reason", value=reason, inline=False)
    if duration: embed.add_field(name="Duration", value=f"{duration} seconds", inline=False)
    return embed

async def send_with_rate_limit(destination, content=None, *, embed=None, file=None, view=None):
    await message_queue.put((destination, content, embed, file, view))
    await process_message_queue()

async def process_message_queue():
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
            if e.status == 429:
                await asyncio.sleep(e.retry_after)
                await message_queue.put((destination, content, embed, file, view))
        except Exception as e:
            print(f"Error sending message: {e}")
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

# Invite tracking
async def update_invite_cache():
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite for invite in invites}
            for invite in invites:
                if invite.inviter:
                    invite_data.setdefault(guild.id, {})[invite.code] = {
                        "uses": invite.uses,
                        "inviter": invite.inviter.id
                    }
        except Exception as e:
            print(f"Error updating invites: {e}")

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
            embed = make_embed(description=welcome_msg, color=0x00ff00)
            await channel.send(embed=embed)
            
            # Update leaderboard
            if used_invite and used_invite.inviter:
                inviter_id = used_invite.inviter.id
                invite_leaderboard.setdefault(guild.id, {})[inviter_id] = invite_leaderboard.get(guild.id, {}).get(inviter_id, 0) + 1

        await update_invite_cache()
    except Exception as e:
        print(f"Error in member join: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Track AFK mentions
    for mention in message.mentions:
        if mention.id in afk_users and mention.id != message.author.id:
            if mention.id in afk_data:
                afk_data[mention.id]["mentions"] += 1
            await send_with_rate_limit(
                message.channel,
                embed=make_embed(
                    "📨 User is AFK",
                    f"{mention.display_name} is AFK: {afk_users[mention.id]}",
                    discord.Color.yellow()
                )
            )

    # Welcome back from AFK
    if message.author.id in afk_users:
        afk_info = afk_data.pop(message.author.id, {})
        duration = (datetime.utcnow() - afk_info.get("time", datetime.utcnow())).total_seconds()
        mentions = afk_info.get("mentions", 0)
        
        embed = make_embed(
            "🎉 Welcome Back!",
            f"{message.author.mention} is no longer AFK!\n"
            f"⏱️ You were AFK for {duration//60:.0f} minutes\n"
            f"📨 You received {mentions} mentions",
            discord.Color.green()
        )
        await send_with_rate_limit(message.channel, embed=embed)
        del afk_users[message.author.id]

    # Block invites
    allowed_roles = ["Board of Directors", "Associate Directors"]
    if not any(role.name in allowed_roles for role in message.author.roles):
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            try:
                await message.delete()
                embed = make_embed(
                    "⚠️ Discord Invites Not Allowed",
                    f"{message.author.mention} No invite links permitted!",
                    0xFF0000
                )
                warning = await message.channel.send(embed=embed)
                await asyncio.sleep(10)
                await warning.delete()
            except:
                pass

    await bot.process_commands(message)

#################################
# --- MODERATION COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    warns.setdefault(member.id, []).append(reason)
    await send_with_rate_limit(
        ctx,
        embed=make_mod_embed("⚠️ User Warned", ctx, member, reason)
    )

@bot.command()
@commands.has_permissions(kick_members=True)
async def warnings(ctx, member: discord.Member):
    user_warns = warns.get(member.id, [])
    embed = make_embed(
        f"Warnings for {member.display_name}",
        "\n".join(f"{i+1}. {warn}" for i, warn in enumerate(user_warns)) or "No warnings",
        0xFFA500
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    if member.id in warns:
        del warns[member.id]
    await ctx.send(embed=make_embed(
        "✅ Warnings Cleared",
        f"Cleared all warnings for {member.mention}",
        0x00FF00
    ))

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str):
    await member.kick(reason=reason)
    await send_with_rate_limit(
        ctx,
        embed=make_mod_embed("👢 User Kicked", ctx, member, reason)
    )

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str):
    await member.ban(reason=reason)
    await send_with_rate_limit(
        ctx,
        embed=make_mod_embed("🔨 User Banned", ctx, member, reason)
    )

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    await ctx.send(embed=make_embed(
        "🔓 User Unbanned",
        f"{user.name} has been unbanned",
        0x00FF00
    ))

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted") or \
               await ctx.guild.create_role(name="Muted")
    
    for channel in ctx.guild.channels:
        await channel.set_permissions(mute_role, send_messages=False, speak=False)
    
    await member.add_roles(mute_role, reason=reason)
    await send_with_rate_limit(
        ctx,
        embed=make_mod_embed("🔇 User Muted", ctx, member, reason)
    )

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role in member.roles:
        await member.remove_roles(mute_role)
    await ctx.send(embed=make_embed(
        "🔊 User Unmuted",
        f"{member.mention} can now speak again",
        0x00FF00
    ))

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=make_embed(
        "🧹 Messages Purged",
        f"Deleted {amount} messages",
        0x00FF00
    ))
    await asyncio.sleep(3)
    await msg.delete()

#################################
# --- INVITE COMMANDS --- #
#################################

@bot.command()
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    count = invite_leaderboard.get(ctx.guild.id, {}).get(member.id, 0)
    embed = make_embed(
        "📊 Invite Stats",
        f"{member.mention} has invited **{count}** members",
        0x00ff00
    )
    await ctx.send(embed=embed)

@bot.command()
async def invitelb(ctx, limit: int = 10):
    guild_data = invite_leaderboard.get(ctx.guild.id, {})
    if not guild_data:
        return await ctx.send(embed=make_embed("No invite data available yet!", color=0xFF0000))
    
    sorted_lb = sorted(guild_data.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    embed = make_embed("🏆 Invite Leaderboard", color=0xffd700)
    for i, (user_id, count) in enumerate(sorted_lb, 1):
        member = ctx.guild.get_member(user_id)
        if member:
            embed.add_field(
                name=f"{i}. {member.display_name}",
                value=f"**{count}** invites",
                inline=False
            )
    
    await ctx.send(embed=embed)

#################################
# --- TOKEN ECONOMY COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(administrator=True)
async def give(ctx, member: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_GIVERS:
        return await ctx.send(embed=make_embed("Permission Denied", "You can't give tokens", 0xFF0000))
    add_tokens(member.id, amount)
    await ctx.send(embed=make_embed(
        "✅ Tokens Given",
        f"Gave {amount} VRT tokens to {member.mention}",
        0x00ff00
    ))

@bot.command()
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    bal = get_balance(member.id)
    await ctx.send(embed=make_embed(
        "💰 Token Balance",
        f"{member.mention} has **{bal}** VRT tokens",
        0x7289da
    ))

@bot.command()
@commands.has_permissions(administrator=True)
async def remove(ctx, member: discord.Member, amount: int):
    if ctx.author.id not in AUTHORIZED_GIVERS:
        return await ctx.send(embed=make_embed("Permission Denied", "You can't remove tokens", 0xFF0000))
    if subtract_tokens(member.id, amount):
        await ctx.send(embed=make_embed(
            "❌ Tokens Removed",
            f"Removed {amount} VRT tokens from {member.mention}",
            0xFFA500
        ))
    else:
        await ctx.send(embed=make_embed(
            "⚠️ Error",
            "User doesn't have enough tokens",
            0xFF0000
        ))

@bot.command()
async def buy(ctx, *, item_name: str):
    item = SHOP_ITEMS.get(item_name.lower())
    if not item:
        return await ctx.send(embed=make_embed(
            "⚠️ Invalid Item",
            "That item doesn't exist in the shop",
            0xFF0000
        ))
    
    if subtract_tokens(ctx.author.id, item["price"]):
        role = discord.utils.get(ctx.guild.roles, name=item["role_name"]) or \
               await ctx.guild.create_role(name=item["role_name"])
        await ctx.author.add_roles(role)
        await ctx.send(embed=make_embed(
            "✅ Purchase Successful",
            f"You bought **{item_name}** for {item['price']} VRT tokens!",
            0x00ff00
        ))
    else:
        await ctx.send(embed=make_embed(
            "⚠️ Insufficient Tokens",
            "You don't have enough VRT tokens",
            0xFF0000
        ))

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

#################################
# --- BASIC COMMANDS --- #
#################################

@bot.command()
async def afk(ctx, *, reason="AFK"):
    afk_users[ctx.author.id] = reason
    afk_data[ctx.author.id] = {
        "time": ctx.message.created_at,
        "mentions": 0,
        "reason": reason
    }
    embed = make_embed("🛌 AFK Activated", 
                      f"{ctx.author.mention} is now AFK: {reason}",
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
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"))
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    await send_with_rate_limit(ctx, embed=embed)

bot.run(os.getenv('TOKEN'))
