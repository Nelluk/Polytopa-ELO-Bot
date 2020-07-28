import modules.exceptions as exceptions
import logging
import datetime
import server_settings
from discord.ext import commands
# import discord
import configparser
logger = logging.getLogger('polybot.' + __name__)

config = configparser.ConfigParser()
config.read('config.ini')

try:
    discord_key = config['DEFAULT']['discord_key']
    psql_user = config['DEFAULT']['psql_user']
    psql_db = config['DEFAULT']['psql_db']
    owner_id = int(config['DEFAULT']['owner_id'])
except KeyError:
    logger.error('Error finding a required setting (discord_key / psql_user / psql_db / owner_id) in config.ini file')
    exit(0)

pastebin_key = config['DEFAULT'].get('pastebin_key', None)

server_ids = server_settings.server_shortcut_ids
# server_ids = {'main': 283436219780825088, 'polychampions': 478571892832206869, 'test': 478571892832206869, 'beta': 274660262873661442}

config = server_settings.server_list  # list of allowed servers and server-level settings
bot = None
run_tasks = True  # if set as False via command line option, tasks should check this and skip
team_elo_reset_date = '1/1/2020'

# bot invite URL https://discordapp.com/oauth2/authorize?client_id=484067640302764042&scope=bot
# bot invite URL for beta bot https://discordapp.com/oauth2/authorize?client_id=479029527553638401&scope=bot


lobbies = [{'guild': 283436219780825088, 'size_str': '1v1', 'size': [1, 1], 'ranked': True, 'remake_partial': True, 'notes': '**Newbie game** - 1075 elo max'},
           {'guild': 283436219780825088, 'size_str': '1v1', 'size': [1, 1], 'ranked': True, 'remake_partial': False, 'notes': ''},
           {'guild': 283436219780825088, 'size_str': 'FFA', 'size': [1, 1, 1], 'ranked': True, 'remake_partial': False, 'notes': ''},
           {'guild': 283436219780825088, 'size_str': '1v1', 'size': [1, 1], 'ranked': False, 'remake_partial': True, 'notes': ''},
           {'guild': 283436219780825088, 'size_str': 'FFA', 'size': [1, 1, 1], 'ranked': False, 'remake_partial': False, 'notes': ''},
           # {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': True, 'exp': 95, 'remake_partial': False, 'notes': 'Open to all'},
           # {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': False, 'exp': 95, 'remake_partial': False, 'role_locks': [None, 531567102042308609], 'notes': 'Newbie 2v2 game, Novas welcome <:novas:531568047824306188>'},
           {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': True, 'exp': 95, 'remake_partial': False, 'role_locks': [696841367103602768, 696841359616901150], 'notes': '**Newbie game**: Nova Red vs Nova Blue'},
           {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': True, 'exp': 95, 'remake_partial': False, 'role_locks': [696841359616901150, 696841367103602768], 'notes': '**Newbie game**: Nova Blue vs Nova Red'},
           {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': True, 'exp': 95, 'remake_partial': False, 'role_locks': [696841367103602768, 696841359616901150], 'notes': '**Newbie game**: Nova Red vs Nova Blue'},
           {'guild': 447883341463814144, 'size_str': '2v2', 'size': [2, 2], 'ranked': True, 'exp': 95, 'remake_partial': False, 'role_locks': [696841359616901150, 696841367103602768], 'notes': '**Newbie game**: Nova Blue vs Nova Red'},
           # {'guild': 447883341463814144, 'size_str': '3v3', 'size': [3, 3], 'ranked': False, 'exp': 95, 'remake_partial': False, 'role_locks': [None, 531567102042308609], 'notes': 'Newbie 3v3 game, Novas welcome <:novas:531568047824306188>'},
           # {'guild': 447883341463814144, 'size_str': '3v3', 'size': [3, 3], 'ranked': True, 'exp': 95, 'remake_partial': False, 'notes': 'Open to all'},
           {'guild': 478571892832206869, 'size_str': '3v3', 'size': [3, 3], 'ranked': False, 'exp': 95, 'remake_partial': False, 'role_locks': [None, 480350546172182530], 'notes': ''},
           {'guild': 478571892832206869, 'size_str': 'FFA', 'size': [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1], 'ranked': True, 'exp': 95, 'remake_partial': True, 'notes': 'Open to all'}]

discord_id_ban_list = [
    493503844865671187,  # BlueberryCraft#9080 (star hacker)
    436330481341169675,  # Mr Bucky
    481581027685564416,  # Shadow Knight
    # 396699990577119244,  # Skrealder
    # 481525222072254484,  # testaccount1
    342341358218117121,  # Caesar Augustas Trajan
    327433644589187072,  # Spacebar/Robit
    359831073737146369,  # Epi
    427018182310756352,  # Freeze
    386549614964244481,  # logs#4361
    313427349775450112,  # SouthPenguinJay#3692
    616737820261875721,  # CoolGuyNotFoolGuy#0498 troll who blatantly lied about game confirmations
    735809555837091861,  # XaeroXD8401  points cheater
]

poly_id_ban_list = [
    'pKUaK61nd2BzNY65',  # BlueberryCraft#9080 (star hacker)
    'MvSRS2t5vWLUyyuu',  # Caesar Augustas Trajan
    'AfMDTSO3yareZN2E',  # Freeze
    # 'qIqw1okeZZgaFpUL',  # Remalin (skre alt)
    # '815D2hK94mN7StoL',  # Skrealder
    'fOEjbnrzO9tg1QYT',  # Doggo#8422
    '8ZWg85d9PlogdY1H',  # Stupid#7043
    'R5NregRkLycUsq7C',  # Just7609
    '9x85fWIxxkLyOMem',  # logs#4361
    'JU1Zb9jGO4H1I4Ls',  # SouthPenguinJay#3692
    'MhJJohJENaeBUz7H',  # CoolGuyNotFoolGuy#0498
    '20aih8HH5IcromHX',  # XaeroXD8401
]


generic_teams_short = [('Home', ':stadium:'), ('Away', ':airplane:')]  # For two-team games
generic_teams_long = [('Sharks', ':shark:'), ('Owls', ':owl:'), ('Eagles', ':eagle:'), ('Tigers', ':tiger:'),
                      ('Bears', ':bear:'), ('Koalas', ':koala:'), ('Dogs', ':dog:'), ('Bats', ':bat:'),
                      ('Lions', ':lion:'), ('Cats', ':cat:'), ('Birds', ':bird:'), ('Spiders', ':spider:')]

date_cutoff = datetime.datetime.today() - datetime.timedelta(days=90)  # Players who haven't played since cutoff are not included in leaderboards


def get_setting(setting_name):
    return config['default'][setting_name]


def guild_setting(guild_id: int, setting_name: str):
    # if guild_id = None, default block will be used

    if guild_id:

        try:
            settings_obj = config[guild_id]
        except KeyError:
            logger.warn(f'Unknown guild id {guild_id} requested for setting name {setting_name}.')
            raise exceptions.CheckFailedError('Unauthorized: This guild is not in the config.ini file.')
            # return config['default'][setting_name]

        try:
            return settings_obj[setting_name]
        except KeyError:
            return config['default'][setting_name]

    else:
        return config['default'][setting_name]


def servers_included_in_global_lb():
    return [server for server, settings in config.items() if settings.get('include_in_global_lb', False)]


def get_matching_roles(discord_member, list_of_role_names):
    # Given a Discord.Member and a ['List of', 'Role names'], return set of role names that the Member has.polytopia_id
    member_roles = [x.name for x in discord_member.roles]
    return set(member_roles).intersection(list_of_role_names)


levels_info = ('***Level 1*** - *Join ranked games up to 3 players, unranked games up to 6 players. Host games up to 3 players.*\n\n'
               '***Level 2*** - *Join ranked games up to 6 players, unranked games up to 12 players. Host ranked games up to 4 players, unranked games up to 6 players.* (__Complete 2 games to attain, ranked or unranked__)\n\n'
               '***Level 3*** - *No restrictions on games* (__Complete 10 games to attain, ranked or unranked__)\n')


def get_user_level(ctx, user=None):
    user = ctx.author if not user else user

    if user.id == owner_id:
        return 7
    if is_mod(ctx, user=user):
        return 6
    if is_staff(ctx, user=user):
        return 5
    if get_matching_roles(user, guild_setting(ctx.guild.id, 'user_roles_level_4')):
        return 4  # advanced matchmaking abilities (leave own match, join others to match). can use settribes in bulk
    if get_matching_roles(user, guild_setting(ctx.guild.id, 'user_roles_level_3')):
        return 3  # host/join any
    if get_matching_roles(user, guild_setting(ctx.guild.id, 'user_roles_level_2')):
        return 2  # join ranked games up to 6p, unranked up to 12p
    if get_matching_roles(user, guild_setting(ctx.guild.id, 'user_roles_level_1')):
        return 1  # join ranked games up to 3p, unranked up to 6p. no hosting
    return 0


def can_user_join_game(user_level: int, game_size: int, is_ranked: bool = True, is_host: bool = True):
    # return bool_permission_given, str_error_message
    if is_host:
        if user_level <= 1 and game_size > 3:
            return False, f'You can only host games with a maximum of 3 players.\n{levels_info}'
        if user_level <= 2:
            if game_size > 4 and is_ranked:
                return False, f'You can only host ranked games of up to 4 players. More active players have permissons to host large games.\n{levels_info}'
            if game_size > 6:
                return False, f'You can only host unranked games of up to 6 players. More active players have permissons to host large games.\n{levels_info}'

    if user_level <= 1:
        if (is_ranked and game_size > 3) or (not is_ranked and game_size > 6):
            return False, f'You are a restricted user (*level 1*) - complete a few more ELO games to have more permissions.\n{levels_info}'
        if user_level <= 2:
            if (is_ranked and game_size > 6) or (not is_ranked and game_size > 12):
                return False, f'You are a restricted user (*level 2*) - complete a few more ELO games to have more permissions.\n{levels_info}'

    return True, None  # Game allowed


def is_staff(ctx, user=None):
    user = ctx.author if not user else user

    if user.id == owner_id:
        return True
    helper_roles = guild_setting(ctx.guild.id, 'helper_roles')
    mod_roles = guild_setting(ctx.guild.id, 'mod_roles')

    target_match = get_matching_roles(user, helper_roles + mod_roles)
    return len(target_match) > 0


def is_mod(ctx_or_member, user=None):
    # if member passed as first arg, checks to see if member is a mod of the guild they are a member of
    # if ctx is passed, will check second arg user as a mod, or check ctx.member as a mod
    if type(ctx_or_member).__name__ == 'Context':
        user = ctx_or_member.author if not user else user
        guild = ctx_or_member.guild
    else:
        # Assuming Member object passed
        user = ctx_or_member
        guild = user.guild

    if user.id == owner_id:
        return True
    mod_roles = guild_setting(guild.id, 'mod_roles')

    target_match = get_matching_roles(user, mod_roles)
    return len(target_match) > 0


def is_staff_check():
    # restrict commands to is_staff with syntax like @settings.is_staff_check()

    def predicate(ctx):
        return is_staff(ctx)
    return commands.check(predicate)


def is_mod_check():
    # restrict commands to is_staff with syntax like @settings.is_mod_check()

    def predicate(ctx):
        return is_mod(ctx)
    return commands.check(predicate)


def on_polychampions():

    def predicate(ctx):
        return ctx.guild.id == server_ids['polychampions'] or ctx.guild.id == server_ids['test']
    return commands.check(predicate)


def teams_allowed():

    def predicate(ctx):
        return guild_setting(ctx.guild.id, 'allow_teams')
    return commands.check(predicate)


def in_bot_channel():
    async def predicate(ctx):
        if guild_setting(ctx.guild.id, 'bot_channels') is None:
            return True
        if is_mod(ctx):
            return True
        if ctx.message.channel.id in guild_setting(ctx.guild.id, 'bot_channels') + guild_setting(ctx.guild.id, 'bot_channels_private'):
            return True
        else:
            if ctx.invoked_with == 'help' and ctx.command.name != 'help':
                # Silently fail check when help cycles through every bot command for a check.
                pass
            else:
                channel_tags = [f'<#{chan_id}>' for chan_id in guild_setting(ctx.guild.id, 'bot_channels')]
                await ctx.send(f'This command can only be used in a designated ELO bot channel. Try: {" ".join(channel_tags)}')
            return False
    return commands.check(predicate)


async def is_bot_channel_strict(ctx):
    if guild_setting(ctx.guild.id, 'bot_channels_strict') is None:
        if guild_setting(ctx.guild.id, 'bot_channels') is None:
            return True
        else:
            chan_list = guild_setting(ctx.guild.id, 'bot_channels')
    else:
        chan_list = guild_setting(ctx.guild.id, 'bot_channels_strict')
    if is_mod(ctx):
        return True
    if ctx.message.channel.id in chan_list + guild_setting(ctx.guild.id, 'bot_channels_private'):
        return True
    else:
        if ctx.invoked_with == 'help' and ctx.command.name != 'help':
            # Silently fail check when help cycles through every bot command for a check.
            pass
        else:
            # primary_bot_channel = chan_list[0]
            channel_tags = [f'<#{chan_id}>' for chan_id in chan_list]
            await ctx.send(f'This command can only be used in a designated bot spam channel. Try: {" ".join(channel_tags)}')
        return False


def in_bot_channel_strict():
    async def predicate(ctx):
        return await is_bot_channel_strict(ctx)
    return commands.check(predicate)
