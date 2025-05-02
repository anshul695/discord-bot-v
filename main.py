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

def load_invite_data():
    if not os.path.exists(INVITE_DATA_FILE):
        return {}
    try:
        with open(INVITE_DATA_FILE, 'r') as f:
            data = json.load(f)
            return {int(guild_id): guild_data for guild_id, guild_data in data.items()}
    except:
        return {}

def save_invite_data(data):
    with open(INVITE_DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_invite_leaderboard():
    if not os.path.exists(INVITE_LEADERBOARD_FILE):
        return {}
    try:
        with open(INVITE_LEADERBOARD_FILE, 'r') as f:
            data = json.load(f)
            return {int(guild_id): {int(user_id): count for user_id, count in guild_data.items()} 
                   for guild_id, guild_data in data.items()}
    except:
        return {}

def save_invite_leaderboard(data):
    with open(INVITE_LEADERBOARD_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Bot Setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Data Storage
afk_users = {}  # {user_id: {"time": datetime, "reason": str}}
afk_mentions = defaultdict(list)  # {user_id: [{"author": user_id, "message": str, "time": datetime, "jump_url": str}]}
warns = defaultdict(list)  # {user_id: [{"reason": str, "moderator": user_id, "time": datetime}]}
invite_data = load_invite_data()  # Load from file
invite_leaderboard = load_invite_leaderboard()  # Load from file
member_join_times = defaultdict(list)  # {guild_id: [datetime]}
muted_members = set()  # {guild_id: {user_id}}

# Configuration
AUTHORIZED_GIVERS = [1327923421442736180, 1097776051393929227, 904290766225027083]
TOKEN_FILE = 'tokens.json'
WELCOME_CHANNEL_ID = 1363797902291374110
MOD_LOG_CHANNEL_ID = 1361974563952529583  # Replace with your mod log channel ID
INVITE_DATA_FILE = 'invite_data.json'         # Stores invite usage data
INVITE_LEADERBOARD_FILE = 'invite_leaderboard.json'  # Stores leaderboard counts

# Rate limiting
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

# 8Ball responses
BALL_RESPONSES = [
    "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes - definitely.",
    "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
    "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
    "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.",
    "Very doubtful."
]

# Utility Functions
def make_embed(title=None, description=None, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Anshhhulll's Bot")
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

# Token System
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
    save_tokens(data=tokens)

def subtract_tokens(user_id, amount):
    tokens = load_tokens()
    user_id = str(user_id)
    if tokens.get(user_id, 0) >= amount:
        tokens[user_id] -= amount
        save_tokens(data=tokens)
        return True
    return False

def get_balance(user_id):
    tokens = load_tokens()
    return tokens.get(str(user_id), 0)

# Invite Tracking
async def update_invite_cache():
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_data[guild.id] = {invite.code: {"uses": invite.uses, "inviter": invite.inviter.id} 
                                    for invite in invites if invite.inviter}
save_invite_data(invite_data)  # <-- ADD THIS LINE
        except Exception as e:
            print(f"Error updating invites: {e}")

# Events

@tasks.loop(minutes=5.0)
async def save_invite_data_task():
    save_invite_data(invite_data)
    save_invite_leaderboard(invite_leaderboard)

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you, be good or I'll spank"))
    print(f"✅ {bot.user} is online!")
    await update_invite_cache()
save_invite_data_task.start()  # <-- ADD THIS LINE
    
    # Initialize member join times
    for guild in bot.guilds:
        async for member in guild.fetch_members(limit=None):
            if member.joined_at:
                member_join_times[guild.id].append(member.joined_at.replace(tzinfo=None))

@bot.event
async def on_invite_create(invite):
    await update_invite_cache()

@bot.event
async def on_invite_delete(invite):
    await update_invite_cache()

@bot.event
async def on_member_join(member):
    guild = member.guild
    member_join_times[guild.id].append(datetime.utcnow())
    
    if guild.id not in invite_data:
        await update_invite_cache()
        return
    
    try:
        new_invites = await guild.invites()
        used_invite = None
        
        for invite in new_invites:
            old_data = invite_data[guild.id].get(invite.code)
            if old_data and invite.uses > old_data["uses"]:
                used_invite = invite
                break
        
        inviter = used_invite.inviter if used_invite else "someone mysterious"
        channel = guild.get_channel(WELCOME_CHANNEL_ID)
        if channel:
            welcome_msg = random.choice(welcome_messages).format(member, inviter)
            await channel.send(welcome_msg)
            
            if used_invite and used_invite.inviter:
    inviter_id = used_invite.inviter.id
    invite_leaderboard.setdefault(guild.id, {})[inviter_id] = invite_leaderboard.get(guild.id, {}).get(inviter_id, 0) + 1
    save_invite_leaderboard(invite_leaderboard)  # <-- ADD THIS LINE

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
            afk_mentions[mention.id].append({
                "author": message.author.id,
                "message": message.content[:50] + ("..." if len(message.content) > 50 else ""),
                "time": message.created_at.replace(tzinfo=None),
                "jump_url": message.jump_url
            })
            
            # Send AFK notice in embed
            embed = discord.Embed(
                description=f"ℹ️ {mention.display_name} is AFK: {afk_users[mention.id]['reason']}",
                color=discord.Color.orange()
            )
            await message.channel.send(embed=embed)

    # Welcome back from AFK
    if message.author.id in afk_users:
        mentions = afk_mentions.pop(message.author.id, [])
        duration = (datetime.utcnow() - afk_users[message.author.id]["time"]).total_seconds()
        reason = afk_users[message.author.id]["reason"]
        duration_str = f"{duration//3600:.0f} hours, {(duration%3600)//60:.0f} minutes" if duration >= 3600 else f"{duration//60:.0f} minutes"
        
        # Create view with button only if there are mentions
        view = discord.ui.View()
        if mentions:
            button = discord.ui.Button(
                label=f"See {len(mentions)} mentions",
                style=discord.ButtonStyle.blurple,
                custom_id=f"afk_mentions_{message.author.id}"
            )
            
            async def button_callback(interaction):
                # Only allow the AFK user to see their mentions
                if interaction.user.id != message.author.id:
                    await interaction.response.send_message(
                        "❌ These mentions are private to the AFK user.",
                        ephemeral=True
                    )
                    return
                    
                mention_list = "\n".join(
                    f"• <@{m['author']}>: {m['message']} ([Jump]({m['jump_url']}))" 
                    for m in mentions[:25]  # Limit to 25 mentions to avoid too long messages
                )
                
                embed = discord.Embed(
                    title=f"🔔 You were mentioned {len(mentions)} times while AFK",
                    description=mention_list,
                    color=discord.Color.blue()
                )
                
                if len(mentions) > 25:
                    embed.set_footer(text=f"Showing 25 out of {len(mentions)} mentions")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            
            button.callback = button_callback
            view.add_item(button)
        
        # Welcome back embed (public)
        embed = discord.Embed(
            title="🎉 Welcome Back!",
            description=f"{message.author.mention} is no longer AFK",
            color=discord.Color.green()
        )
        embed.add_field(name="⏱️ Duration", value=duration_str, inline=True)
        embed.add_field(name="📨 Mentions", value=str(len(mentions)), inline=True)
        embed.add_field(name="💬 Reason", value=reason, inline=False)
        
        await message.channel.send(embed=embed, view=view)
        del afk_users[message.author.id]

    # Block invites
    allowed_roles = ["Board of Directors", "Associate Directors"]
    if not any(role.name in allowed_roles for role in message.author.roles):
        if "discord.gg/" in message.content.lower() or "discord.com/invite/" in message.content.lower():
            try:
                await message.delete()
                warning = await message.channel.send(
                    f"⚠️ {message.author.mention} Discord invites aren't allowed here!",
                    delete_after=10
                )
            except:
                pass

    await bot.process_commands(message)

#################################
# --- MODERATION COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(kick_members=True)
async def warn(ctx, member: discord.Member, *, reason: str):
    warns[member.id].append({
        "reason": reason,
        "moderator": ctx.author.id,
        "time": datetime.utcnow()
    })
    
    embed = make_embed(
        "⚠️ User Warned",
        f"{member.mention} has been warned by {ctx.author.mention}\nReason: {reason}",
        discord.Color.orange()
    )
    await send_with_rate_limit(ctx, embed=embed)
    
    # Send to mod log
    mod_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        await send_with_rate_limit(mod_channel, embed=embed)

@bot.command()
async def warnings(ctx, member: discord.Member):
    user_warns = warns.get(member.id, [])
    warn_list = "\n".join(
        f"{i+1}. {w['reason']} (by <@{w['moderator']}> at {w['time'].strftime('%Y-%m-%d %H:%M')})"
        for i, w in enumerate(user_warns)
    ) or "No warnings"
    
    embed = make_embed(
        f"Warnings for {member.display_name}",
        warn_list,
        discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def clearwarns(ctx, member: discord.Member):
    if member.id in warns:
        del warns[member.id]
    embed = make_embed(
        "✅ Warnings Cleared",
        f"All warnings for {member.mention} have been cleared",
        discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str):
    await member.kick(reason=reason)
    embed = make_embed(
        "👢 User Kicked",
        f"{member.mention} has been kicked by {ctx.author.mention}\nReason: {reason}",
        discord.Color.orange()
    )
    await send_with_rate_limit(ctx, embed=embed)
    
    # Send to mod log
    mod_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        await send_with_rate_limit(mod_channel, embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str):
    await member.ban(reason=reason)
    embed = make_embed(
        "🔨 User Banned",
        f"{member.mention} has been banned by {ctx.author.mention}\nReason: {reason}",
        discord.Color.red()
    )
    await send_with_rate_limit(ctx, embed=embed)
    
    # Send to mod log
    mod_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        await send_with_rate_limit(mod_channel, embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user)
    embed = make_embed(
        "🔓 User Unbanned",
        f"{user.name} has been unbanned by {ctx.author.mention}",
        discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    
    if not mute_role:
        mute_role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(mute_role, send_messages=False, speak=False)
    
    await member.add_roles(mute_role, reason=reason)
    muted_members.add((ctx.guild.id, member.id))
    
    embed = make_embed(
        "🔇 User Muted",
        f"{member.mention} has been muted by {ctx.author.mention}\nReason: {reason}",
        discord.Color.orange()
    )
    await send_with_rate_limit(ctx, embed=embed)
    
    # Send to mod log
    mod_channel = ctx.guild.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        await send_with_rate_limit(mod_channel, embed=embed)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    mute_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if mute_role and mute_role in member.roles:
        await member.remove_roles(mute_role)
        muted_members.discard((ctx.guild.id, member.id))
        
        embed = make_embed(
            "🔊 User Unmuted",
            f"{member.mention} has been unmuted by {ctx.author.mention}",
            discord.Color.green()
        )
        await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 10):
    if amount <= 0 or amount > 100:
        return await ctx.send(embed=make_embed(
            "Invalid Amount",
            "Please specify a number between 1 and 100",
            discord.Color.red()
        ))
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(embed=make_embed(
        "🧹 Messages Purged",
        f"Deleted {len(deleted) - 1} messages",
        discord.Color.green()
    ))
    await asyncio.sleep(3)
    await msg.delete()

#################################
# --- ROLE MANAGEMENT COMMANDS --- #
#################################

@bot.command()
@commands.has_permissions(manage_roles=True)
async def giverole(ctx, member: discord.Member, role: discord.Role):
    if role.position >= ctx.guild.me.top_role.position:
        return await ctx.send(embed=make_embed(
            "⚠️ Error",
            "I can't assign roles higher than my highest role",
            discord.Color.red()
        ))
    
    await member.add_roles(role)
    await ctx.send(embed=make_embed(
        "✅ Role Added",
        f"Gave {role.mention} to {member.mention}",
        discord.Color.green()
    ))

@bot.command()
@commands.has_permissions(manage_roles=True)
async def removerole(ctx, member: discord.Member, role: discord.Role):
    if role.position >= ctx.guild.me.top_role.position:
        return await ctx.send(embed=make_embed(
            "⚠️ Error",
            "I can't remove roles higher than my highest role",
            discord.Color.red()
        ))
    
    if role not in member.roles:
        return await ctx.send(embed=make_embed(
            "⚠️ Error",
            f"{member.mention} doesn't have the {role.mention} role",
            discord.Color.red()
        ))
    
    await member.remove_roles(role)
    await ctx.send(embed=make_embed(
        "❌ Role Removed",
        f"Removed {role.mention} from {member.mention}",
        discord.Color.green()
    ))

#################################
# --- FUN COMMANDS --- #
#################################

@bot.command(aliases=['8ball'])
async def eightball(ctx, *, question: str):
    response = random.choice(BALL_RESPONSES)
    embed = make_embed(
        "🎱 Magic 8 Ball",
        f"**Question:** {question}\n**Answer:** {response}",
        discord.Color.purple()
    )
    await ctx.send(embed=embed)

@bot.command()
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = make_embed(
        f"🖼️ {member.display_name}'s Avatar",
        color=discord.Color.blue()
    )
    embed.set_image(url=member.display_avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def coinflip(ctx):
    result = random.choice(["Heads", "Tails"])
    embed = make_embed(
        "🪙 Coin Flip",
        f"The coin landed on **{result}**!",
        discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command()
async def roll(ctx, sides: int = 6):
    if sides < 2:
        return await ctx.send(embed=make_embed(
            "⚠️ Invalid Dice",
            "Dice must have at least 2 sides",
            discord.Color.red()
        ))
    
    result = random.randint(1, sides)
    embed = make_embed(
        "🎲 Dice Roll",
        f"You rolled a **{result}** (1-{sides})",
        discord.Color.green()
    )
    await ctx.send(embed=embed)

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
        return await ctx.send(embed=make_embed(
            "No Invite Data",
            "No invite tracking data available yet",
            discord.Color.red()
        ))
    
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
# --- MEMBER STATS COMMANDS --- #
#################################

@bot.command()
async def membercount(ctx):
    """Shows detailed member statistics"""
    guild = ctx.guild
    now = datetime.utcnow()
    
    # Calculate time periods
    time_periods = {
        "Last 2 hours": timedelta(hours=2),
        "Last 6 hours": timedelta(hours=6),
        "Last 12 hours": timedelta(hours=12),
        "Last 24 hours": timedelta(days=1),
        "Last 7 days": timedelta(days=7)
    }
    
    # Count members in each period
    join_counts = {}
    for period, delta in time_periods.items():
        cutoff = now - delta
        join_counts[period] = sum(1 for join_time in member_join_times[guild.id] if join_time > cutoff)
    
    # Count online members
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    
    embed = make_embed(
        f"👥 {guild.name} Member Statistics",
        f"Total Members: **{guild.member_count}**",
        discord.Color.blue()
    )
    
    # Add join time breakdown
    join_stats = "\n".join(
        f"• {period}: **{count}** joins" 
        for period, count in join_counts.items()
    )
    embed.add_field(name="Recent Joins", value=join_stats, inline=False)
    
    # Add online status
    embed.add_field(
        name="Online Status",
        value=f"🟢 Online: **{online}**\n🔴 Offline: **{guild.member_count - online}**",
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
        return await ctx.send(embed=make_embed(
            "Permission Denied",
            "You're not authorized to give tokens",
            discord.Color.red()
        ))
    
    if amount <= 0:
        return await ctx.send(embed=make_embed(
            "Invalid Amount",
            "Please specify a positive number",
            discord.Color.red()
        ))
    
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
        return await ctx.send(embed=make_embed(
            "Permission Denied",
            "You're not authorized to remove tokens",
            discord.Color.red()
        ))
    
    if amount <= 0:
        return await ctx.send(embed=make_embed(
            "Invalid Amount",
            "Please specify a positive number",
            discord.Color.red()
        ))
    
    if subtract_tokens(member.id, amount):
        await ctx.send(embed=make_embed(
            "❌ Tokens Removed",
            f"Removed {amount} VRT tokens from {member.mention}",
            0xFFA500
        ))
    else:
        await ctx.send(embed=make_embed(
            "⚠️ Error",
            f"{member.mention} doesn't have enough tokens",
            discord.Color.red()
        ))

@bot.command()
async def shop(ctx):
    embed = make_embed("🛒 VRT Token Shop", color=0xffd700)
    for item, data in SHOP_ITEMS.items():
        embed.add_field(
            name=item.title(),
            value=f"Price: {data['price']} tokens\nReward: {data['role_name']} role",
            inline=False
        )
    await ctx.send(embed=embed)

@bot.command()
async def buy(ctx, *, item_name: str):
    item = SHOP_ITEMS.get(item_name.lower())
    if not item:
        return await ctx.send(embed=make_embed(
            "⚠️ Invalid Item",
            "That item doesn't exist in the shop",
            discord.Color.red()
        ))
    
    if not subtract_tokens(ctx.author.id, item["price"]):
        return await ctx.send(embed=make_embed(
            "⚠️ Insufficient Tokens",
            "You don't have enough VRT tokens",
            discord.Color.red()
        ))
    
    role = discord.utils.get(ctx.guild.roles, name=item["role_name"])
    if not role:
        role = await ctx.guild.create_role(name=item["role_name"])
    
    await ctx.author.add_roles(role)
    await ctx.send(embed=make_embed(
        "✅ Purchase Successful",
        f"You bought **{item_name}** for {item['price']} VRT tokens!\n"
        f"You now have the **{role.name}** role",
        0x00ff00
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
                await interaction.response.send_message(
                    "📩 We've sent you a DM with the application form. Please check your inbox!",
                    ephemeral=True
                )
            except discord.Forbidden:
                await interaction.response.send_message(
                    "⚠️ I couldn't DM you. Please enable DMs and try again.",
                    ephemeral=True
                )

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
    afk_users[ctx.author.id] = {
        "time": datetime.utcnow(),
        "reason": reason
    }
    afk_mentions[ctx.author.id] = []
    
    embed = discord.Embed(
        description=f"🛌 {ctx.author.mention} is now AFK: {reason}",
        color=discord.Color.orange()
    )
    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    
    embed = make_embed(
        f"ℹ️ {member.display_name}'s Information",
        f"ID: `{member.id}`",
        discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(
        name="Account Created",
        value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        inline=True
    )
    embed.add_field(
        name="Joined Server",
        value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"),
        inline=True
    )
    embed.add_field(
        name=f"Roles ({len(roles)})",
        value=" ".join(roles) if roles else "No roles",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def serverinfo(ctx):
    guild = ctx.guild
    online = sum(1 for m in guild.members if m.status != discord.Status.offline)
    
    embed = make_embed(
        f"🏰 {guild.name} Server Information",
        f"Owner: {guild.owner.mention}",
        discord.Color.green()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(
        name="Members",
        value=f"Total: {guild.member_count}\nOnline: {online}",
        inline=True
    )
    embed.add_field(
        name="Channels",
        value=f"Text: {len(guild.text_channels)}\nVoice: {len(guild.voice_channels)}",
        inline=True
    )
    embed.add_field(
        name="Created On",
        value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        inline=False
    )
    
    if guild.premium_tier > 0:
        embed.add_field(
            name="Server Boosts",
            value=f"Level: {guild.premium_tier}\nBoosters: {guild.premium_subscription_count}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = make_embed(
        "🤖 Bot Help Menu",
        "Here are all the available commands:",
        discord.Color.blue()
    )
    
    # Moderation
    embed.add_field(
        name="🔨 Moderation",
        value="`warn`, `warnings`, `clearwarns`, `kick`, `ban`, `unban`, `mute`, `unmute`, `purge`",
        inline=False
    )
    
    # Role Management
    embed.add_field(
        name="🎭 Role Management",
        value="`giverole`, `removerole`",
        inline=False
    )
    
    # Fun
    embed.add_field(
        name="🎉 Fun",
        value="`8ball`, `avatar`, `coinflip`, `roll`",
        inline=False
    )
    
    # Invites
    embed.add_field(
        name="📊 Invites",
        value="`invites`, `invitelb`",
        inline=False
    )
    
    # Member Stats
    embed.add_field(
        name="👥 Member Stats",
        value="`membercount`, `userinfo`, `serverinfo`",
        inline=False
    )
    
    # Token Economy
    embed.add_field(
        name="💰 Token Economy",
        value="`balance`, `shop`, `buy`",
        inline=False
    )
    
    # Utility
    embed.add_field(
        name="🛠️ Utility",
        value="`afk`, `apply`, `help`",
        inline=False
    )
    
    embed.set_footer(text="Use % before each command | Example: %help")
    await ctx.send(embed=embed)

bot.run(os.getenv('TOKEN'))
