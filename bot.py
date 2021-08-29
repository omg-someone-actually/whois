import discord
from discord.ext import commands

from ipinfo import getHandler
from ipaddress import ip_address as ip_checker 

from asyncpraw import Reddit

from json import load
from pprint import pprint


class settings:
    def __init__(self):
        """Retrieves data from settings.json to manage the project and ease of use to change settings."""
        with open("settings.json") as my_settings:
            self.all_settings = load(my_settings)

    def discord_bot(self, setting):
        return self.all_settings["discord_bot"][setting]

    def reddit_bot(self, setting):
        return self.all_settings["reddit_bot"][setting]

    def ipinfo(self, setting):
        return self.all_settings["ipinfo"][setting]
    
    def customization(self, setting):
        return self.all_settings["customization"][setting]

    

#Connects to my ipinfo.io account.
handler = getHandler(settings().ipinfo("access_token"))

#Establishes the client settings, and removes the help command for privacy.
client = commands.Bot(command_prefix=settings().discord_bot("bot_prefix"), intents=discord.Intents.all(), owner_ids=settings().customization("owner_ids"))
for command in settings().discord_bot("removed_commands"):
    client.remove_command(command)

#Authorizes my reddit bot.
reddit = Reddit(
    client_id= settings().reddit_bot("client_id"),
    client_secret= settings().reddit_bot("client_secret"),
    user_agent= settings().reddit_bot("user_agent"),
    usernmae = settings().reddit_bot("username"),
    password = settings().reddit_bot("password")
)

@client.event
async def on_ready():
    """
    
    Prints that the bot has logged in once we can start calling commands.
    
    """
    print(f"Logged in as {client.user}")


@client.command(name="lookup")
@commands.is_owner()
async def _lookup(ctx):
    """

    Gets various information to lookup and find the best matching results to return to the user.

    """

    def check(message):
        return message.channel == ctx.channel and message.author != client.user and message.content.startswith(";")

    await ctx.send("What is their first name?")
    raw_first_name = await client.wait_for("message", check=check)
    first_name = raw_first_name.content.strip(";")

    await ctx.send(f"What is {first_name}'s middle name?")
    raw_middle_name = await client.wait_for("message", check=check)
    middle_name = raw_middle_name.content.strip(";")

    if "skip" in middle_name:
        middle_name =  None
        await ctx.send("Skipped!")

    await ctx.send(f"What is {first_name}'s last name?")
    raw_last_name = await client.wait_for("message", check=check)
    last_name = raw_last_name.content.strip(";")

    def has_middle_name():
        if not middle_name:
            return ""
        return middle_name

    full_name = (f"{first_name} {has_middle_name()} {last_name}")

    await ctx.send(f"What is {first_name}'s age?")    
    raw_age = await client.wait_for('message', check=check)
    age = raw_age.content.strip(';')
    
    if "skip" in age:
        age = "Unknown"
        await ctx.send("Skipped!")

    await ctx.send("What state are they in?")
    raw_state = await client.wait_for('message', check=check)
    state = raw_state.content.strip(';')

    if "skip" in state:
        state = "Unknown"
        await ctx.send("Skipped!")

    await ctx.send(f"Name: {full_name}\nAge: {age}\nState: {state}")


@client.command(name="whois")
@commands.is_owner()
async def _whois(ctx, ip_address: str = None):
    """
    
    Uses a websites ip/a regular ip to fetch data then return it to the user.

    """


    def is_invalid_ip(ip_address):
        if not ip_address:
            return True

        try:
            ip_checker(ip_address)

        except Exception:
            return True

        return False

    if is_invalid_ip(ip_address):  
        await ctx.send("Invalid arguments.")
        return

    ip_details = handler.getDetails(ip_address)

    embed = discord.Embed(title=f"{ip_address} details.")
    embed.set_thumbnail(url=settings().customization("thumbnails")["ip"])

    ip_fields = {
        "City": ip_details.city, 
        "Region": ip_details.region, 
        "Country": ip_details.country,
        "Cordinates": ip_details.loc,
        "Isp company": ip_details.org,
        "Zipcode": ip_details.postal,
        "Timezone": ip_details.timezone
    }

    for field_name, field_value in ip_fields.items():
        embed.add_field(name=field_name, value=field_value)

    

    await ctx.send(embed=embed)


@client.command(name="details")
@commands.is_owner()
async def _details(ctx, account_type: str = None, user: str = None):
    """
    
    Gets details of a user account.

    """

    async def lookup_discord_account(user):
        
        characters_to_remove = ["<", ">", '@', '!']

        for character in characters_to_remove:
            user = user.replace(character, "")

        member: discord.Member = await client.fetch_user(user)
        
        account_details = {
            "Created": member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"), 
            "Id": member.id, 
            "Display name": member.display_name, 
            "Discriminator": member.discriminator
        }

        embed = discord.Embed(title=f"{member.display_name}#{member.discriminator}'s account details")
        embed.set_thumbnail(url=member.avatar_url)

        for field_name, field_value in account_details.items():
            embed.add_field(name=field_name, value=field_value)

        await ctx.send(embed=embed)

    async def lookup_reddit_account(user):
        redditor_details = await reddit.redditor(user, fetch=True)
        
        account_details = {
            "Name": redditor_details.name,
            "Id": redditor_details.id,
            "Total karma": redditor_details.total_karma,
            "Verified email": redditor_details.has_verified_email,
            "Has subscribed": redditor_details.has_subscribed,
            "Is mod": redditor_details.is_mod,
            "Is employee": redditor_details.is_employee
        }

        embed = discord.Embed(title=f"{user}'s account details")

        try:
            embed.set_thumbnail(url=redditor_details.icon_img)
        except Exception:
            embed.set_thumbnail(url=settings().customization("thumbnails")["reddit"])


        for field_name, field_value in account_details.items():
            if field_value in vars(redditor_details).keys():
                continue
            embed.add_field(name=field_name, value=field_value)
        
        await ctx.send(embed=embed)
        



    valid_social_media_options = {
        "discord": lookup_discord_account,
        "reddit": lookup_reddit_account
    }

    if not account_type or account_type not in valid_social_media_options:
            await ctx.send("Invalid arguments")
            return
    
    await valid_social_media_options[account_type](user)


if __name__ == "__main__":    
    client.run(settings().discord_bot("bot_token"))
