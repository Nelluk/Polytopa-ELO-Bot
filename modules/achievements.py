import discord
# from discord.ext import commands
import logging
# import asyncio
import modules.models as models
import settings
import peewee
logger = logging.getLogger('polybot.' + __name__)


# ELO Rookie - 2+ games
# ELO Player - 10+ games
# ELO Veteran - 1200+ games
# ELO Hero - 1350+ elo
# ELO Champion - #1 local or global leaderboard


async def set_champion_role():

    # global_champion = models.DiscordMember.select().order_by(-models.DiscordMember.elo).limit(1).get()
    global_champion = models.DiscordMember.leaderboard(date_cutoff=settings.date_cutoff, guild_id=None, max_flag=False).limit(1).get()

    for guild in settings.bot.guilds:
        logger.info(f'Attempting champion set for guild {guild.name}')
        role = discord.utils.get(guild.roles, name='ELO Champion')
        if not role:
            logger.warn(f'Could not load ELO Champion role in guild {guild.name}')
            continue

        # local_champion = models.Player.select().where(models.Player.guild_id == guild.id).order_by(-models.Player.elo).limit(1).get()
        local_champion = models.Player.leaderboard(date_cutoff=settings.date_cutoff, guild_id=guild.id, max_flag=False).limit(1).get()

        local_champion_member = guild.get_member(local_champion.discord_member.discord_id)
        global_champion_member = guild.get_member(global_champion.discord_id)

        try:
            for old_champion in role.members:
                if old_champion in [local_champion_member, global_champion_member]:
                    logger.debug(f'Skipping role removal for {old_champion.display_name} since champion is the same')
                else:
                    await old_champion.remove_roles(role, reason='Recurring reset of champion list')
                    logger.info(f'removing ELO Champion role from {old_champion.name}')

            if local_champion_member:
                logger.info(f'adding ELO Champion role to {local_champion_member.name}')
                await local_champion_member.add_roles(role, reason='Local champion')
            else:
                logger.warn(f'Couldnt find local champion {local_champion} in guild {guild.name}!')

            if global_champion_member:
                logger.info(f'adding ELO Champion role to {global_champion_member.name}')
                await global_champion_member.add_roles(role, reason='Global champion')
            else:
                logger.warn(f'Couldnt find global champion {global_champion.name} in guild {guild.name}!')
        except discord.DiscordException as e:
            logger.warn(f'Error during set_champion_role for guild {guild.id}: {e}')
            continue


async def set_experience_role(discord_member):
    logger.debug(f'processing experience role for member {discord_member.name}')
    completed_games = discord_member.completed_game_count(only_ranked=False)

    for guildmember in list(discord_member.guildmembers):
        guild = discord.utils.get(settings.bot.guilds, id=guildmember.guild_id)
        member = guild.get_member(discord_member.discord_id) if guild else None

        if not member:
            logger.debug(f'Skipping guild {guildmember.guild_id}, could not load both guild and its member object')
            continue

        role_list = []

        role = None
        if completed_games >= 2:
            role = discord.utils.get(guild.roles, name='ELO Rookie')
            role_list.append(role) if role is not None else None
        if completed_games >= 10:
            role = discord.utils.get(guild.roles, name='ELO Player')
            role_list.append(role) if role is not None else None
        if discord_member.elo_max >= 1200:
            role = discord.utils.get(guild.roles, name='ELO Veteran')
            role_list.append(role) if role is not None else None
        if discord_member.elo_max >= 1350:
            role = discord.utils.get(guild.roles, name='ELO Hero')
            role_list.append(role) if role is not None else None
        if discord_member.elo_max >= 1500:
            role = discord.utils.get(guild.roles, name='ELO Elite')
            role_list.append(role) if role is not None else None
        if discord_member.elo_max >= 1650:
            role = discord.utils.get(guild.roles, name='ELO Master')
            role_list.append(role) if role is not None else None
        if discord_member.elo_max >= 1800:
            role = discord.utils.get(guild.roles, name='ELO Titan')
            role_list.append(role) if role is not None else None

        if not role:
            continue

        if role not in member.roles:
            logger.debug(f'Applying new achievement role {role.name} to {member.display_name}')
            try:
                if role not in role_list or len(role_list) > 1:
                    await member.remove_roles(*role_list)
                    logger.info(f'removing roles from member {member}:\n:{role_list}')
                await member.add_roles(role)
                logger.info(f'adding role {role} to member {member}')
            except discord.DiscordException as e:
                logger.warn(f'Error during set_experience_role for guild {guild.id} member {member.display_name}: {e}')

        max_local_elo = models.Player.select(peewee.fn.Max(models.Player.elo)).where(models.Player.guild_id == guild.id).scalar()
        max_global_elo = models.DiscordMember.select(peewee.fn.Max(models.DiscordMember.elo)).scalar()

        if discord_member.elo >= max_global_elo or guildmember.elo >= max_local_elo:
            # This player has #1 spot in either local OR global leaderboard. Apply ELO Champion role on any server where the player is:
            await set_champion_role()
