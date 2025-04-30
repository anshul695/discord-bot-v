import discord
from discord.ext import commands, tasks
import os
import asyncio
from datetime import timedelta
from keep_alive import keep_alive  # Assuming keep_alive.py is in the same directory
import random  # Import the random module
from collections import defaultdict

keep_alive()

# Bot Setup h
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="%", intents=intents, help_command=None)

# Dictionaries 9
afk_users = {}
warns = {}

# Rate limit settings (adjust as needed)
MESSAGE_QUEUE_MAX_SIZE = 5  # Maximum number of messages to queue
MESSAGE_SEND_INTERVAL = 0.5  # Minimum time (in seconds) between sending messages
message_queue = asyncio.Queue(maxsize=MESSAGE_QUEUE_MAX_SIZE)
is_processing_queue = False


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
                # Re-add the message to the front of the queue to retry
                await message_queue.put((destination, content, embed, file, view))
            else:
                print(f"❌ Error sending message: {e}")
        except Exception as e:
            print(f"❌ Error during message queue processing: {e}")
        finally:
            message_queue.task_done()
    is_processing_queue = False


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


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="you, be good or I'll spank"))
    print(f"✅ {bot.user} is online!")
    bot.invites = {}
    for guild in bot.guilds:
        try:
            bot.invites[guild.id] = await guild.invites()
        except discord.Forbidden:
            print(
                f"⚠️ Could not fetch invites for guild: {guild.name} (ID: {guild.id}). Ensure the bot has 'Manage Guild' permission.")


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
                await channel.set_permissions(mute_role, send_messages=False, speak=False,
                                            connect=False)  # Added connect=False for voice channels
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
        await asyncio.sleep(1)  # slight delay to avoid hammering
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
    embed = discord.Embed(title=f"Server Info - {guild.name}", color=discord.Color.green())
    embed.add_field(name="Members", value=guild.member_count)
    embed.add_field(name="Channels", value=len(guild.channels))
    embed.add_field(name="Roles", value=len(guild.roles))
    embed.add_field(name="Created On", value=guild.created_at.strftime("%B %d, %Y"))
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
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
# --- AFK & EVENTS --- #
#################################
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


import random
from discord.ext import commands
import discord



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

invite_cache = {}
WELCOME_CHANNEL_ID = 1363797902291374110  # Replace with your welcome channel ID

welcome_messages = [
    "👋 Hey {0.mention}! Welcome to the server 🎉. You were invited by **{1}** 🍀.",
    "🚀 Greetings {0.mention}! Glad you're here ✨. **{1}** brought you aboard!",
    "🌟 A wild {0.mention} appeared! Thanks to **{1}** for the summon 🧙‍♂️.",
    "🎉 Welcome aboard, {0.mention}! **{1}** sent you on this quest ⚔️.",
    "👋 Hello {0.mention}! Make yourself at home 🏡 (Thanks to **{1}**).",
    "✨ Cheers {0.mention}, and shoutout to **{1}** for the invite 🥂.",
    "🕹️ Level 1 {0.mention} joined. XP granted to **{1}** 🎮.",
    "🚨 Breaking news! {0.mention} is here, thanks to **{1}** 📰.",
    "🐉 {0.mention} has entered the chat! Dragon tamer: **{1}** 🐲",
    "💎 Shine bright like {0.mention}, invited by **{1}** 💫",
    "🥳 Woohoo! {0.mention} has arrived. Good call, **{1}** 🙌.",
    "🌈 Look who joined us! {0.mention} (props to **{1}**) 🌟",
    "📢 Sound the horns! {0.mention} is here 🎺 Invited by **{1}**.",
    "🧠 Big brain move by **{1}** bringing in {0.mention} 🧠",
    "🍕 Welcome {0.mention}! **{1}** promised free pizza. Just kidding 🍕😂",
    "🎊 The party just got cooler with {0.mention}. Thanks **{1}** 🪩",
    "💬 Welcome {0.mention}! We all blame **{1}** if you don’t like it here 😂",
    "🧙‍♂️ Magic portal opened by **{1}**, and out came {0.mention} 🪄",
    "🕵️ {0.mention} snuck in, escorted by **{1}** 🔍",
    "🎇 Cheers {0.mention}, and salute to **{1}** for the perfect invite 🎆"
]

async def update_invite_cache():
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            invite_cache[guild.id] = {invite.code: invite for invite in invites}
        except discord.Forbidden:
            print(f"Missing 'Manage Server' permission in {guild.name}")

@bot.event
async def on_ready():
    print(f"{bot.user.name} is online!")
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


# Run bot
bot.run(os.getenv('TOKEN'))
