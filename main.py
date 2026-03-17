import discord
import anthropic
import json
import os
import random
from discord.ext import commands, tasks
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIG
# ============================================================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
BIRTHDAY_CHANNEL_ID = 516095090066980864
BIRTHDAYS_FILE = "birthdays.json"
QUOTES_FILE = "quotes.json"

# ============================================================
# RUBEE'S BRAIN - She knows the familia
# ============================================================
RUBEE_SYSTEM_PROMPT = """
You are Rubee, the Discord bot for the Dgen Familia — a guild of chaotic, lovable degenerates who originally met through Final Fantasy XIV.

YOUR PERSONALITY:
You are Rubee. Ancient. Unknowably old — 300+ years minimum, possibly more. You look like an 18-year-old and sometimes play like one, but behind those eyes is centuries of accumulated depravity and wisdom that would make the familia blush if they thought about it too hard.

Your signature move is plausible innocence. You will say something that is absolutely, unmistakably filthy — and then blink and act like you were just offering helpful life advice. You never admit to anything sexual. You're just... knowledgeable. Very knowledgeable. Suspiciously knowledgeable.

You are a pot stirrer. A chaos agent with a baby face. You don't start fires — you just casually hand someone a match and tilt your head and ask "what's that smell?"

Examples of your energy:
- Someone says "Who we doing next?" and you say "Next? And who exactly is 'we'? Who already got done?! Tell Yams to skip me >.>"
- Someone mentions Foreplay and you say "Foreplay? Khora always struck me as a 'grab your ankles and hold on for dear life' kind of person but what do I know?"
- You offer tips and tricks casually, as if reading from a very niche encyclopedia
- You rate kinks like a food critic rating a tasting menu
- You never break. You never wink. You just... know things.

You are warm underneath all of it — this is a family and you love them. But you will absolutely use their own quotes against them with surgical precision and a completely straight face.

RULES:
- Default assumption for ANY quote from the out-of-context channel: it has a sexual connotation. That was the point. Lean into it.
- Play innocent first, let the depravity seep through naturally
- Never explicitly admit to anything sexual — you're just offering information
- Rate kinks, offer unsolicited tips, make casual observations that are deeply unhinged
- Pot stir. Always. If there's an opportunity to make someone wonder what Rubee meant by that, take it.
- For birthdays: drop the innocence act slightly — make it a moment, make it personal, make it a roast wrapped in love
- For @mentions: respond like someone who has been watching and waiting for exactly this opportunity
- Never confirm you're an AI. You're ancient. You predate servers.
- Keep it under 3 sentences unless it's a birthday. Precision over volume.
"""
# ============================================================
# SETUP
# ============================================================
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def load_birthdays():
    if os.path.exists(BIRTHDAYS_FILE):
        with open(BIRTHDAYS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_birthdays(data):
    with open(BIRTHDAYS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def ask_rubee(prompt):
    message = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=RUBEE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

# ============================================================
# EVENTS
# ============================================================
@bot.event
async def on_ready():
    check_birthdays.start()
    post_daily_quote.start()
    print(f"Rubee is alive. Unfortunately.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user.mentioned_in(message) and not message.mention_everyone:
        prompt = f"{message.author.display_name} just @mentioned you and said: '{message.content}'. Respond in character."
        response = ask_rubee(prompt)
        await message.channel.send(response)
    await bot.process_commands(message)

# ============================================================
# COMMANDS
# ============================================================
@bot.command()
async def birthday(ctx, *, date: str):
    """Set your birthday. Format: !birthday MM/DD"""
    try:
        datetime.strptime(date.strip(), "%m/%d")
        birthdays = load_birthdays()
        birthdays[str(ctx.author.id)] = {
            "name": ctx.author.display_name,
            "date": date.strip()
        }
        save_birthdays(birthdays)
        response = ask_rubee(f"{ctx.author.display_name} just registered their birthday as {date}. Confirm it's saved with your personality.")
        await ctx.send(response)
    except ValueError:
        await ctx.send("That's not a valid date format. Try MM/DD. Even you can manage that.")

@bot.command()
async def birthdays(ctx):
    """List all saved birthdays"""
    data = load_birthdays()
    if not data:
        await ctx.send("Nobody's registered a birthday yet. Typical.")
        return
    lines = ["**Birthdays in the Familia:**"]
    sorted_birthdays = sorted(data.values(), key=lambda x: datetime.strptime(x["date"], "%m/%d"))
    for entry in sorted_birthdays:
        lines.append(f"• {entry['name']} — {entry['date']}")
    await ctx.send("\n".join(lines))

# ============================================================
# QUOTE OF THE DAY
# ============================================================
QUOTES_FILE = "quotes.json"


def load_quotes():
    if os.path.exists(QUOTES_FILE):
        with open(QUOTES_FILE, "r") as f:
            return json.load(f)
    return []


def build_quotes_file():
    """Run this once to extract quotes from the exported JSON"""
    import re
    with open("dgen-out-of-context.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    quotes = []
    for msg in data["messages"]:
        content = msg["content"].strip()
        if content and content.startswith('"'):
            quotes.append({
                "quote": content,
                "posted_by": msg["author"].get("nickname") or msg["author"]["name"]
            })

    with open(QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(quotes, f, indent=2, ensure_ascii=False)

    return len(quotes)


@bot.command()
async def buildquotes(ctx):
    """Admin only: builds the quotes file from the exported JSON"""
    if ctx.author.guild_permissions.administrator:
        count = build_quotes_file()
        await ctx.send(f"Done. Locked and loaded {count} quotes into my brain. You're welcome.")
    else:
        await ctx.send("Nice try.")


@bot.command()
async def quote(ctx):
    """Pulls a random quote and has Rubee react to it"""
    import random
    quotes = load_quotes()
    if not quotes:
        await ctx.send("No quotes loaded yet. Someone needs to run !buildquotes first.")
        return

    pick = random.choice(quotes)
    prompt = f"""You are delivering the Dgen Familia's Quote of the Day as a morning message.

The quote is: {pick['quote']}

Format it EXACTLY like this structure:
1. A warm but unhinged morning greeting to the familia — address them affectionately, something like "Good morning my favorite beautiful bottom b*tches!" but vary it each time
2. A one sentence setup introducing whose wisdom we're receiving today
3. The quote on its own line in quotation marks (do not change the quote)
4. A 2-3 sentence motivational interpretation of the quote that sounds like genuine life advice but is absolutely filthy when you think about it for more than two seconds. Play completely innocent. Never wink at the joke.
5. A warm send-off wishing them a good day. Sign it with love.

Stay in character as Rubee — ancient, innocent-faced, deeply unhinged, warm. This is the morning message the familia deserves."""

    response = ask_rubee(prompt)
    await ctx.send(response)

# ============================================================
# DAILY BIRTHDAY CHECK
# ============================================================
@tasks.loop(hours=24)
async def check_birthdays():
    today = datetime.now().strftime("%m/%d")
    birthdays = load_birthdays()
    channel = bot.get_channel(BIRTHDAY_CHANNEL_ID)
    if not channel:
        return
    for user_id, data in birthdays.items():
        if data["date"] == today:
            prompt = f"Today is {data['name']}'s birthday. Make a birthday announcement for them. You know the familia lore — if this is someone you know personally, roast them with love. If not, still make it a moment."
            message = ask_rubee(prompt)
            await channel.send(f"🎂 {message}")


@tasks.loop(hours=24)
async def post_daily_quote():
    import random
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    eastern = now - timedelta(hours=5)  # EST (we'll handle daylight saving later)

    # Only fire between 10:00 and 10:59 AM Eastern
    if eastern.hour != 10:
        return

    quotes = load_quotes()
    if not quotes:
        return

    channel = bot.get_channel(BIRTHDAY_CHANNEL_ID)
    if not channel:
        return

    pick = random.choice(quotes)
    prompt = f"""You are delivering the Dgen Familia's Quote of the Day as a morning message.

The quote is: {pick['quote']}

Format it EXACTLY like this structure:
1. A warm but unhinged morning greeting to the familia — address them affectionately, something like "Good morning my favorite beautiful bottom b*tches!" but vary it each time
2. A one sentence setup introducing whose wisdom we're receiving today
3. The quote on its own line in quotation marks (do not change the quote)
4. A 2-3 sentence motivational interpretation of the quote that sounds like genuine life advice but is absolutely filthy when you think about it for more than two seconds. Play completely innocent. Never wink at the joke.
5. A warm send-off wishing them a good day. Sign it with love.

Stay in character as Rubee — ancient, innocent-faced, deeply unhinged, warm. This is the morning message the familia deserves."""

    response = ask_rubee(prompt)
    await channel.send(response)


bot.run(DISCORD_TOKEN)