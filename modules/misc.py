import discord
from discord.ext import commands
import modules.models as models
import modules.utilities as utilities
import settings
import logging
import asyncio
import modules.exceptions as exceptions
import re
import datetime
import random
import peewee
# from modules.games import PolyGame
# import modules.achievements as achievements

logger = logging.getLogger('polybot.' + __name__)


class misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if settings.run_tasks:
            self.bg_task = bot.loop.create_task(self.task_broadcast_newbie_message())
            self.bg_task = bot.loop.create_task(self.task_send_polychamps_invite())

    @commands.command(hidden=True, aliases=['ts'])
    @commands.is_owner()
    async def test(self, ctx, *, arg: str = None):

        print(f'starting test')
        with models.db.atomic():
            await ctx.send(f'test')
            await asyncio.sleep(6)
        print('end test')

    @commands.command(hidden=True, aliases=['bulk_local_elo', 'ble', 'bge'])
    async def bulk_global_elo(self, ctx, *, args=None):
        """
        Given a list of players, or a single mentioned role, return that list sorted by player's global/local ELO.

        `[p]bulk_global elo nelluk koric rickdaheals`
        `[p]bulk_local_elo @Ronin`
        """
        if not args:
            return await ctx.send(f'Include list of players, example: `{ctx.prefix}bge nelluk koric` - @mentions and raw user IDs are supported')
        player_stats = []

        if ctx.message.role_mentions:
            arg_list = [str(member.id) for member in ctx.message.role_mentions[0].members]
        else:
            arg_list = args.split(' ')

        for arg in arg_list:
            try:
                player_match = models.Player.get_or_except(player_string=arg, guild_id=ctx.guild.id)
            except exceptions.NoSingleMatch:
                await ctx.send(f'Could not match `{arg}` to a player. Specify user with @Mention or user ID.')
                continue

            if ctx.invoked_with in ['bulk_local_elo', 'ble']:
                player_stats.append((player_match.elo, player_match))
            else:
                player_stats.append((player_match.discord_member.elo, player_match))

        player_stats.sort(key=lambda tup: tup[0], reverse=True)     # sort the list descending by ELO
        print(player_stats)

        if ctx.invoked_with in ['bulk_local_elo', 'ble']:
            message = '__Player name - Local ELO - Local games played__\n'
        else:
            message = '__Player name - Global ELO - Local games played__\n'

        for player in player_stats:
            message += f'{player[1].name} - {player[0]} - {player[1].games_played().count()}\n'

        await utilities.buffered_send(destination=ctx, content=message)

    @commands.command(usage=None)
    @settings.in_bot_channel_strict()
    async def guide(self, ctx):
        """
        Show an overview of what the bot is for

        Type `[p]guide` for an overview of what this bot is for and how to use it.
        """
        bot_desc = ('This bot is designed to improve Polytopia multiplayer by filling in gaps in two areas: competitive leaderboards, and matchmaking.\n'
                    # 'Its primary home is [PolyChampions](https://discord.gg/cX7Ptnv), a server focused on team play organized into a league.\n'
                    f'To register as a player with the bot use __`{ctx.prefix}setcode YOURPOLYCODEHERE`__')

        embed = discord.Embed(title=f'PolyELO Bot Donation Link', url='https://cash.me/$Nelluk/3', description=bot_desc)

        embed.add_field(name='Matchmaking',
            value=f'This helps players organize and find games.\nFor example, use __`{ctx.prefix}opengame 1v1`__ to create an open 1v1 game that others can join.\n'
                f'To see a list of open games you can join use __`{ctx.prefix}opengames`__. Once the game is full the host would use __`{ctx.prefix}startgame`__ to close it and track it for the leaderboards.\n'
                f'See __`{ctx.prefix}help matchmaking`__ for all commands.', inline=False)

        embed.add_field(name='ELO Leaderboards',
            value='Win your games and climb the leaderboards! Earn sweet ELO points!\n'
                'ELO points are gained or lost based on your game results. You will gain more points if you defeat an opponent with a higher ELO.\n'
                f'Use __`{ctx.prefix}lb`__ to view the individual leaderboards. There is also a __`{ctx.prefix}lbsquad`__ squad leaderboard. Form a squad by playing with the same person in multiple games!'
                f'\nSee __`{ctx.prefix}help`__ for all commands.', inline=False)

        embed.add_field(name='Finishing tracked games',
            value=f'Use the __`{ctx.prefix}win`__ command to tell the bot that a game has concluded.\n'
            f'For example if Nelluk wins game 10150, he would type __`{ctx.prefix}win 10150 nelluk`__. The losing player can confirm using the same command. '
            f'Games are auto-confirmed after 24 hours, or sooner if the losing side manually confirms.', inline=False)

        embed.set_thumbnail(url=self.bot.user.avatar_url_as(size=512))
        embed.set_footer(text='Developer: Nelluk')
        await ctx.send(embed=embed)

    @commands.command(usage=None)
    @settings.in_bot_channel_strict()
    async def credits(self, ctx):
        """
        Display development credits
        """
        embed = discord.Embed(title=f'PolyELO Bot Donation Link', url='https://cash.me/$Nelluk/3')

        embed.add_field(name='Developer', value='Nelluk')
        embed.add_field(name='Source code', value='https://github.com/Nelluk/Polytopia-ELO-Bot')

        embed.add_field(name='Contributions', value='rickdaheals, koric, Gerenuk, theSeahorse, Octo, Artemis', inline=False)

        embed.set_thumbnail(url=self.bot.user.avatar_url_as(size=512))
        await ctx.send(embed=embed)

    @commands.command()
    @settings.in_bot_channel_strict()
    async def stats(self, ctx):
        """ Display statistics on games logged with this bot """

        embed = discord.Embed(title='PolyELO Statistics')
        last_month = (datetime.datetime.now() + datetime.timedelta(days=-30))
        last_quarter = (datetime.datetime.now() + datetime.timedelta(days=-90))
        last_week = (datetime.datetime.now() + datetime.timedelta(days=-7))

        games_played = models.Game.select().where(models.Game.is_completed == 1)
        games_played_90d = models.Game.select().where((models.Game.is_pending == 0) & (models.Game.date > last_quarter))
        games_played_30d = models.Game.select().where((models.Game.is_pending == 0) & (models.Game.date > last_month))
        games_played_7d = models.Game.select().where((models.Game.is_pending == 0) & (models.Game.date > last_week))

        incomplete_games = models.Game.select().where((models.Game.is_pending == 0) & (models.Game.is_completed == 0))

        participants_90d = models.Lineup.select(models.Lineup.player.discord_member).join(models.Game).join_from(models.Lineup, models.Player).join(models.DiscordMember).where(
            (models.Lineup.game.date > last_quarter)
        ).group_by(models.Lineup.player.discord_member).distinct()

        participants_30d = models.Lineup.select(models.Lineup.player.discord_member).join(models.Game).join_from(models.Lineup, models.Player).join(models.DiscordMember).where(
            (models.Lineup.game.date > last_month)
        ).group_by(models.Lineup.player.discord_member).distinct()

        participants_7d = models.Lineup.select(models.Lineup.player.discord_member).join(models.Game).join_from(models.Lineup, models.Player).join(models.DiscordMember).where(
            (models.Lineup.game.date > last_week)
        ).group_by(models.Lineup.player.discord_member).distinct()

        embed.add_field(value='\u200b', name=f'`{"----------------------------------":<35}` Global (Local)', inline=False)
        game_stats = (f'`{"Total games completed:":<35}\u200b` {games_played.count()} ({games_played.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                      f'`{"Games created in last 90 days:":<35}\u200b`\u200b {games_played_90d.count()} ({games_played_90d.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                      f'`{"Games created in last 30 days:":<35}\u200b`\u200b {games_played_30d.count()} ({games_played_30d.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                      f'`{"Games created in last 7 days:":<35}\u200b`\u200b {games_played_7d.count()} ({games_played_7d.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                      f'`{"Incomplete games:":<35}\u200b` {incomplete_games.count()} ({incomplete_games.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                      )
        embed.add_field(value='\u200b', name=game_stats, inline=False)

        stats_2 = (f'`{"Participants in last 90 days:":<35}\u200b` {participants_90d.count()} ({participants_90d.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                   f'`{"Participants in last 30 days:":<35}\u200b` {participants_30d.count()} ({participants_30d.where(models.Game.guild_id == ctx.guild.id).count()})\n'
                   f'`{"Participants in last 7 days:":<35}\u200b` {participants_7d.count()} ({participants_7d.where(models.Game.guild_id == ctx.guild.id).count()})\n')
        embed.add_field(value='\u200b', name=stats_2, inline=False)

        await ctx.send(embed=embed)

    @commands.command(hidden=True, usage='message')
    # @commands.cooldown(1, 30, commands.BucketType.user)
    @settings.in_bot_channel_strict()
    async def pingall(self, ctx, *, message: str = None):
        """ Ping everyone in all of your incomplete games

        Not useable by all players.

         **Examples**
        `[p]pingall My phone died and I will make all turns tomorrow`
        Send a message to everyone in all of your incomplete games
        `[p]pingall @Glouc3stershire Glouc is in Tahiti and will play again tomorrow`
        *Staff:* Send a message to everyone in another player's games

        """
        if not message:
            return await ctx.send(f'Message is required.')

        m = utilities.string_to_user_id(message.split()[0])

        if m:
            logger.debug('Third party use of pingall')
            # Staff member using command on third party
            if settings.get_user_level(ctx) <= 3:
                logger.debug('insufficient user level')
                return await ctx.send(f'You do not have permission to use this command on another player\'s games.')
            message = ' '.join(message.split()[1:])  # remove @Mention first word of message
            target = str(m)
        else:
            logger.debug('first party usage of pingall')
            # Play using command on their own games
            if settings.get_user_level(ctx) <= 2:
                logger.debug('insufficient user level')
                return await ctx.send(f'You do not have permission to use this command. You can ask a server staff member to use this command on your games for you.')
            target = str(ctx.author.id)

        logger.debug(f'pingall target is {target}')

        try:
            player_match = models.Player.get_or_except(player_string=target, guild_id=ctx.guild.id)
        except exceptions.NoSingleMatch:
            return await ctx.send(f'User <@{target}> is not a registered ELO player.')

        game_list = models.Game.search(player_filter=[player_match], status_filter=2, guild_id=ctx.guild.id)
        logger.debug(f'{len(game_list)} incomplete games for target')

        list_of_players = []
        for g in game_list:
            list_of_players += [f'<@{l.player.discord_member.discord_id}>' for l in g.lineup]

        list_of_players = list(set(list_of_players))
        logger.debug(f'{len(list_of_players)} unique opponents for target')
        clean_message = utilities.escape_role_mentions(message)
        if len(list_of_players) > 100:
            await ctx.send(f'*Warning:* More than 100 unique players are addressed. Only the first 100 will be mentioned.')
        await ctx.send(f'Message to all players in unfinished games for <@{target}>: *{clean_message}*')

        recipient_message = f'Message recipients: {" ".join(list_of_players[:100])}'
        return await ctx.send(recipient_message[:2000])

    @commands.command(usage='game_id')
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def ping(self, ctx, game_id=None, *, message: str = None):
        """ Ping everyone in one of your games with a message

         **Examples**
        `[p]ping 100 I won't be able to take my turn today` - Send a message to everyone in game 100

        See `[p]help pingall` for a command to ping ALL incomplete games simultaneously.

        """

        try:
            game_id = int(game_id) if game_id else ''
        except ValueError:
            game_id = None

        if not game_id:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f'Game ID was not included. Example usage: `{ctx.prefix}ping 100 Here\'s a nice note for everyone in game 100.`')

        if not message:
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f'Message was not included. Example usage: `{ctx.prefix}ping 100 Here\'s a nice note`')

        if ctx.message.attachments:
            attachment_urls = '\n'.join([attachment.url for attachment in ctx.message.attachments])
            message += f'\n{attachment_urls}'

        # message = discord.utils.escape_mentions(message)  # to prevent @everyone vulnerability
        message = utilities.escape_role_mentions(message)

        try:
            game = models.Game.get(id=int(game_id))
        except ValueError:
            return await ctx.send(f'Invalid game ID "{game_id}".')
        except peewee.DoesNotExist:
            return await ctx.send(f'Game with ID {game_id} cannot be found.')

        if not game.player(discord_id=ctx.author.id) and not settings.is_staff(ctx):
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f'You are not a player in game {game.id}')

        permitted_channels = settings.guild_setting(game.guild_id, 'bot_channels')
        permitted_channels_private = []
        if settings.guild_setting(game.guild_id, 'game_channel_categories'):
            if game.game_chan:
                permitted_channels = [game.game_chan] + permitted_channels
            if game.smallest_team() > 1:
                permitted_channels_private = [gs.team_chan for gs in game.gamesides]
                permitted_channels = permitted_channels_private + permitted_channels
                # allows ping command to be used in private team channels - only if there is no solo squad in the game which would mean they cant see the message
                # this also adjusts where the @Mention is placed (sent to all team channels instead of simply in the ctx.channel)
            elif ctx.channel.id in [gs.team_chan for gs in game.gamesides]:
                channel_tags = [f'<#{chan_id}>' for chan_id in permitted_channels]
                ctx.command.reset_cooldown(ctx)
                return await ctx.send(f'This command cannot be used in this channel because there is at least one solo player without access to a team channel.\n'
                    f'Permitted channels: {" ".join(channel_tags)}')

        if ctx.channel.id not in permitted_channels and ctx.channel.id not in settings.guild_setting(game.guild_id, 'bot_channels_private'):
            channel_tags = [f'<#{chan_id}>' for chan_id in permitted_channels]
            ctx.command.reset_cooldown(ctx)
            return await ctx.send(f'This command can not be used in this channel. Permitted channels: {" ".join(channel_tags)}')

        player_mentions = [f'<@{l.player.discord_member.discord_id}>' for l in game.lineup]
        full_message = f'Message from {ctx.author.mention} (**{ctx.author.name}**) regarding game {game.id} **{game.name}**:\n*{message}*'

        if ctx.channel.id in permitted_channels_private:
            logger.debug(f'Ping triggered in private channel {ctx.channel.id}')
            await game.update_squad_channels(self.bot.guilds, game.guild_id, message=f'{full_message}\n{" ".join(player_mentions)}')
        else:
            logger.debug(f'Ping triggered in non-private channel {ctx.channel.id}')
            await game.update_squad_channels(self.bot.guilds, ctx.guild.id, message=full_message)
            await ctx.send(f'{full_message}\n{" ".join(player_mentions)}')

    @commands.command(aliases=['balance'])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    @settings.on_polychampions()
    async def league_balance(self, ctx, *, arg=None):
        league_teams = [('Ronin', ['The Ronin', 'The Bandits']),
                        ('Jets', ['The Jets', 'The Cropdusters']),
                        ('Bombers', ['The Bombers', 'The Dynamite']),
                        ('Lightning', ['The Lightning', 'The Pulse']),
                        ('Cosmonauts', ['The Cosmonauts', 'The Space Cadets']),
                        ('Crawfish', ['The Crawfish', 'The Shrimps']),
                        ('Sparkies', ['The Sparkies', 'The Pups']),
                        ('Wildfire', ['The Wildfire', 'The Flames']),
                        ('Mallards', ['The Mallards', 'The Drakes']),
                        ('Plague', ['The Plague', 'The Rats']),
                        ('Dragons', ['The Dragons', 'The Narwhals'])
                        ]

        league_balance = []
        indent_str = '\u00A0\u00A0 \u00A0\u00A0 \u00A0\u00A0'
        mia_role = discord.utils.get(ctx.guild.roles, name=settings.guild_setting(ctx.guild.id, 'inactive_role'))

        for team, team_roles in league_teams:

            pro_role = discord.utils.get(ctx.guild.roles, name=team_roles[0])
            junior_role = discord.utils.get(ctx.guild.roles, name=team_roles[1])

            if not pro_role or not junior_role:
                logger.warn(f'Could not load one team role from guild, using args: {team_roles}')
                continue

            try:
                pro_team = models.Team.get_or_except(team_roles[0], ctx.guild.id)
                junior_team = models.Team.get_or_except(team_roles[1], ctx.guild.id)
            except exceptions.NoSingleMatch:
                logger.warn(f'Could not load one team from database, using args: {team_roles}')
                continue

            pro_members, junior_members, pro_discord_ids, junior_discord_ids, mia_count = [], [], [], [], 0

            for member in pro_role.members:
                if mia_role in member.roles:
                    mia_count += 1
                else:
                    pro_members.append(member)
                    pro_discord_ids.append(member.id)
            for member in junior_role.members:
                if mia_role in member.roles:
                    mia_count += 1
                else:
                    junior_members.append(member)
                    junior_discord_ids.append(member.id)

            logger.info(team)
            combined_elo, player_games_total = models.Player.average_elo_of_player_list(list_of_discord_ids=junior_discord_ids + pro_discord_ids, guild_id=ctx.guild.id, weighted=True)

            pro_elo, _ = models.Player.average_elo_of_player_list(list_of_discord_ids=pro_discord_ids, guild_id=ctx.guild.id, weighted=False)
            junior_elo, _ = models.Player.average_elo_of_player_list(list_of_discord_ids=junior_discord_ids, guild_id=ctx.guild.id, weighted=False)

            league_balance.append(
                (team,
                 pro_team,
                 junior_team,
                 len(pro_members),
                 len(junior_members),
                 mia_count,
                 combined_elo,
                 player_games_total,
                 pro_elo,
                 junior_elo)
            )

        league_balance.sort(key=lambda tup: tup[6], reverse=True)     # sort by combined_elo

        embed = discord.Embed(title='PolyChampions League Balance Summary')
        for team in league_balance:
            embed.add_field(name=(f'{team[1].emoji} {team[0]} ({team[3] + team[4]}) {team[2].emoji}\n{indent_str} \u00A0\u00A0 ActiveELO™: {team[6]}'
                                  f'\n{indent_str} \u00A0\u00A0 Recent member-games: {team[7]}'),
                value=(f'-{indent_str}__**{team[1].name}**__ ({team[3]}) **ELO: {team[1].elo}** (Avg: {team[8]})\n'
                       f'-{indent_str}__**{team[2].name}**__ ({team[4]}) **ELO: {team[2].elo}** (Avg: {team[9]})\n'), inline=False)

        embed.set_footer(text='ActiveELO™ is the mean ELO of members weighted by how many games each member has played in the last 30 days.')

        await ctx.send(embed=embed)

    @commands.command(aliases=['nova', 'joinnovas'])
    @settings.on_polychampions()
    async def novas(self, ctx, *, arg=None):

        player, _ = models.Player.get_by_discord_id(discord_id=ctx.author.id, discord_name=ctx.author.name, discord_nick=ctx.author.nick, guild_id=ctx.guild.id)
        if not player:
            # Matching guild member but no Player or DiscordMember
            return await ctx.send(f'*{ctx.author.name}* was found in the server but is not registered with me. '
                f'Players can be register themselves with `{ctx.prefix}setcode POLYTOPIA_CODE`.')

        on_team, player_team = models.Player.is_in_team(guild_id=ctx.guild.id, discord_member=ctx.author)
        if on_team:
            return await ctx.send(f'You are already a member of team *{player_team.name}* {player_team.emoji}. Server staff is required to remove you from a team.')

        red_role = discord.utils.get(ctx.guild.roles, name='Nova Red')
        blue_role = discord.utils.get(ctx.guild.roles, name='Nova Blue')
        novas_role = discord.utils.get(ctx.guild.roles, name='The Novas')
        newbie_role = discord.utils.get(ctx.guild.roles, name='Newbie')

        if not red_role or not blue_role or not novas_role:
            return await ctx.send(f'Error finding Novas roles. Searched for *Nova Red* and *Nova Blue* and *The Novas*.')

        # TODO: team numbers may be inflated due to inactive members. Can either count up only player recency, or easier but less effective way
        # would be to have $deactivate remove novas roles and make them rejoin if they come back

        if len(red_role.members) > len(blue_role.members):
            await ctx.author.add_roles(blue_role, novas_role, reason='Joining Nova Blue')
            await ctx.send(f'Congrats, you are now a member of the **Nova Blue** team! To join the fight go to a bot channel and type `{ctx.prefix}novagames`')
        else:
            await ctx.author.add_roles(red_role, novas_role, reason='Joining Nova Red')
            await ctx.send(f'Congrats, you are now a member of the **Nova Red** team! To join the fight go to a bot channel and type `{ctx.prefix}novagames`')

        if newbie_role:
            await ctx.author.remove_roles(newbie_role, reason='Joining Novas')

    # @commands.command()
    # @commands.is_owner()
    # @settings.on_polychampions()
    # async def assign_novas(self, ctx, *, arg=None):
    #     novas_role = discord.utils.get(ctx.guild.roles, name='The Novas')
    #     red_role = discord.utils.get(ctx.guild.roles, name='Nova Red')
    #     blue_role = discord.utils.get(ctx.guild.roles, name='Nova Blue')

    #     async with ctx.typing():
    #         await ctx.send('Assigning half of Novas to *Nova Blue*...')
    #         for nova in novas_role.members[0::2]:
    #             # iterates over every other list member, starting with first member
    #             await nova.add_roles(blue_role, reason='Joining Nova Blue')

    #         await ctx.send('Assigning half of Novas to *Nova Red*...')
    #         for nova in novas_role.members[1::2]:
    #             # iterates over every other list member, starting with second member
    #             await nova.add_roles(red_role, reason='Joining Nova Red')

    #         await ctx.send('Done!')

    @commands.command(aliases=['undrafted'])
    @commands.cooldown(1, 30, commands.BucketType.channel)
    @settings.on_polychampions()
    async def undrafted_novas(self, ctx, *, arg=None):
        """Prints list of Novas who meet graduation requirements but have not been drafted

        Use `[p]undrafted_novas elo` to sort by global elo
        """

        grad_list = []
        grad_role = discord.utils.get(ctx.guild.roles, name='Free Agent')
        inactive_role = discord.utils.get(ctx.guild.roles, name=settings.guild_setting(ctx.guild.id, 'inactive_role'))
        # recruiter_role = discord.utils.get(ctx.guild.roles, name='Team Recruiter')
        if ctx.guild.id == settings.server_ids['test']:
            grad_role = discord.utils.get(ctx.guild.roles, name='Team Leader')

        for member in grad_role.members:
            if inactive_role and inactive_role in member.roles:
                logger.debug(f'Skipping {member.name} since they have Inactive role')
                continue
            try:
                dm = models.DiscordMember.get(discord_id=member.id)
                player = models.Player.get(discord_member=dm, guild_id=ctx.guild.id)
            except peewee.DoesNotExist:
                logger.debug(f'Player {member.name} not registered.')
                continue

            g_wins, g_losses = dm.get_record()
            wins, losses = player.get_record()
            recent_games = dm.games_played(in_days=14).count()
            all_games = dm.games_played().count()

            message = (f'**{player.name}**'
                f'\n\u00A0\u00A0 \u00A0\u00A0 \u00A0\u00A0 {recent_games} games played in last 14 days, {all_games} all-time'
                f'\n\u00A0\u00A0 \u00A0\u00A0 \u00A0\u00A0 ELO:  {dm.elo} *global* / {player.elo} *local*\n'
                f'\u00A0\u00A0 \u00A0\u00A0 \u00A0\u00A0 __W {g_wins} / L {g_losses}__ *global* \u00A0\u00A0 - \u00A0\u00A0 __W {wins} / L {losses}__ *local*\n')

            grad_list.append((message, all_games, dm.elo))

        await ctx.send(f'Listing {len(grad_list)} active members with the **{grad_role.name}** role...')

        if arg and arg.upper() == 'ELO':
            grad_list.sort(key=lambda tup: tup[2], reverse=False)     # sort the list ascending by num games played
        else:
            grad_list.sort(key=lambda tup: tup[1], reverse=False)     # sort the list ascending by num games played

        message = []
        for grad in grad_list:
            # await ctx.send(grad[0])
            message.append(grad[0])

        await utilities.buffered_send(destination=ctx, content=''.join(message))

    @commands.command(hidden=True, aliases=['random_tribes', 'rtribe'], usage='game_size [-banned_tribe ...]')
    @settings.in_bot_channel()
    async def rtribes(self, ctx, size='1v1', *args):
        """Show a random tribe combination for a given game size.
        This tries to keep the sides roughly equal in power.
        **Example:**
        `[p]rtribes 2v2` - Shows Ai-mo/Imperius & Xin-xi/Luxidoor
        `[p]rtribes 2v2 -hoodrick -aquarion` - Remove Hoodrick and Aquarion from the random pool. This could cause problems if lots of tribes are removed.
        """

        m = re.match(r"(\d+)v(\d+)", size.lower())
        if m:
            # arg looks like '3v3'
            if int(m[1]) != int(m[2]):
                return await ctx.send(f'Invalid match format {size}. Sides must be equal.')
            if not 0 < int(m[1]) < 7:
                return await ctx.send(f'Invalid match size {size}. Accepts 1v1 through 6v6')
            team_size = int(m[1])
        else:
            team_size = 1
            args = list(args) + [size]
            # Handle case of no size argument, but with tribe bans

        tribes = [
            ('Bardur', 1),
            ('Kickoo', 1),
            ('Luxidoor', 1),
            ('Imperius', 1),
            ('Elyrion', 2),
            ('Yadakk', 2),
            ('Zebasi', 2),
            ('Hoodrick', 2),
            ('Aquarion', 2),
            ('Oumaji', 3),
            ('Quetzali', 3),
            ('Vengir', 3),
            ('Ai-mo', 3),
            ('Xin-xi', 3)
        ]
        for arg in args:
            # Remove tribes from tribe list. This could cause problems if too many tribes are removed.
            if arg[0] != '-':
                continue
            removal = next(t for t in tribes if t[0].upper() == arg[1:].upper())
            tribes.remove(removal)

        team_home, team_away = [], []

        tribe_groups = {}
        for tribe, group in tribes:
            tribe_groups.setdefault(group, set()).add(tribe)

        available_tribe_groups = list(tribe_groups.values())
        for _ in range(team_size):
            available_tribe_groups = [tg for tg in available_tribe_groups if len(tg) >= 2]

            this_tribe_group = random.choice(available_tribe_groups)

            new_home, new_away = random.sample(this_tribe_group, 2)
            this_tribe_group.remove(new_home)
            this_tribe_group.remove(new_away)

            team_home.append(new_home)
            team_away.append(new_away)

        await ctx.send(f'Home Team: {" / ".join(team_home)}\nAway Team: {" / ".join(team_away)}')

    async def task_send_polychamps_invite(self):
        await self.bot.wait_until_ready()

        message = ('You have met the qualifications to be invited to the **PolyChampions** discord server! '
                   'PolyChampions is a competitive Polytopia server organized into a league, with a focus on team (2v2 and 3v3) games.'
                   '\n To join use this invite link: https://discord.gg/cX7Ptnv')
        while not self.bot.is_closed():
            sleep_cycle = (60 * 60 * 6)
            await asyncio.sleep(30)
            logger.info('Running task task_send_polychamps_invite')
            guild = discord.utils.get(self.bot.guilds, id=settings.server_ids['main'])
            if not guild:
                logger.warn('Could not load guild via server_id')
                break
            utilities.connect()
            dms = models.DiscordMember.members_not_on_polychamps()
            logger.info(f'{len(dms)} discordmember results')
            for dm in dms:
                wins_count, losses_count = dm.wins().count(), dm.losses().count()
                if wins_count < 5:
                    logger.debug(f'Skipping {dm.name} - insufficient winning games')
                    continue
                if dm.games_played(in_days=15).count() < 1:
                    logger.debug(f'Skipping {dm.name} - insufficient recent games')
                    continue
                if dm.elo_max > 1150:
                    logger.debug(f'{dm.name} qualifies due to higher ELO > 1150')
                elif wins_count > losses_count:
                    logger.debug(f'{dm.name} qualifies due to positive win ratio')
                else:
                    logger.debug(f'Skipping {dm.name} - ELO or W/L record insufficient')
                    continue

                logger.debug(f'Sending invite to {dm.name}')
                guild_member = guild.get_member(dm.discord_id)
                if not guild_member:
                    logger.debug(f'Could not load {dm.name} from guild {guild.id}')
                    continue
                try:
                    await guild_member.send(message)
                except discord.DiscordException as e:
                    logger.warn(f'Error DMing member: {e}')
                else:
                    dm.date_polychamps_invite_sent = datetime.datetime.today()
                    dm.save()
            await asyncio.sleep(sleep_cycle)

    async def task_broadcast_newbie_message(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            sleep_cycle = (60 * 60 * 3)
            await asyncio.sleep(10)

            for guild in self.bot.guilds:
                broadcast_channels = [guild.get_channel(chan) for chan in settings.guild_setting(guild.id, 'newbie_message_channels')]
                if not broadcast_channels:
                    continue

                prefix = settings.guild_setting(guild.id, 'command_prefix')
                # ranked_chan = settings.guild_setting(guild.id, 'ranked_game_channel')
                # unranked_chan = settings.guild_setting(guild.id, 'unranked_game_channel')
                bot_spam_chan = settings.guild_setting(guild.id, 'bot_channels_strict')[0]
                elo_guide_channel = 533391050014720040

                broadcast_message = (f'To register for ELO leaderboards and matchmaking use the command __`{prefix}setcode YOURCODEHERE`__')
                broadcast_message += f'\nTo get started with joining an open game, go to <#{bot_spam_chan}> and type __`{prefix}games`__'
                broadcast_message += f'\nFor full information go read <#{elo_guide_channel}>.'

                for broadcast_channel in broadcast_channels:
                    if broadcast_channel:
                        await broadcast_channel.send(broadcast_message, delete_after=(sleep_cycle - 5))

            await asyncio.sleep(sleep_cycle)


def setup(bot):
    bot.add_cog(misc(bot))
