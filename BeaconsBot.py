import discord
import os
import sys
import gettext

from dotenv import load_dotenv
from sqlitedict import SqliteDict
from discord.ext import commands
from datetime import datetime
from datetime import timedelta
from tabulate import tabulate
from functools import cache

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = os.getenv('BOT_PREFIX')
DATABASE_DIRECTORY_PATH = os.getenv('DATABASE_DIRECTORY_PATH', default = '.')

database_file_path = os.path.join(DATABASE_DIRECTORY_PATH, 'beacons.db.sqlite')
print(f'Database file path: \"{database_file_path}\"')

@cache
def translator(lang: str = 'en'):
    trans = gettext.translation('messages', localedir='locale', languages=(lang,), fallback=True)
    return trans.gettext

_en = translator('en')
_ru = translator('ru')
_ = _en # нужен для BABEL чтобы он мог создать .pot файл.


bot = commands.Bot(command_prefix=BOT_PREFIX)


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!\nPrefix: {bot.command_prefix}\nSTDOUT: {sys.stdout.encoding}')


@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        await message.channel.send(_('Веду список активных маяков. \nПрефикс для команд: **{0}**\nПопробуй команду: ```{0}help```').format(bot.command_prefix))
    await bot.process_commands(message)


@bot.command(_('маяк'),
             aliases=[_ru('маяк')],
             brief=' | '.join((_('Добавляет маяк в список'), _ru('Добавляет маяк в список'))),
             help='\n'.join((_('Если построил и зажёг маяк - добавь его в список.'), _ru('Если построил и зажёг маяк - добавь его в список.')))
             )
async def new_beacon(ctx, password, *, description = ''):
    _ = translator(ctx.guild.preferred_locale)
    beacon_id = password
    current_time = datetime.utcnow()
    expires_time = current_time + timedelta(hours = 1)
    
    with SqliteDict(database_file_path) as beacons:
        beacon_exists = beacon_id in beacons

        beacon_expired = False
        if beacon_exists:
            beacon = beacons[beacon_id]
            if current_time > beacon['expires']:
                beacon_expired = True
        
        if not beacon_exists or beacon_exists and beacon_expired:
            beacons[beacon_id] = {
                'guild': ctx.guild.id,
                'author': ctx.author.id,
                'expires': expires_time,
                'password': password,
                'description': description
                }
            beacons.commit()
        else:
            await ctx.send(_('Маяк с таким паролем уже существует.'))
        beacons.close();

        print(f'{ctx.author.name} lit a new beacon \"{password}\" at {ctx.guild.name}')
        await ctx.send(_('{0} зажёг новый маяк: \"{1}\"\n{2}').format(ctx.author.mention, password, description))


@bot.command(_('потушен'),
             aliases=[_ru('потушен')],
             brief=' | '.join((_('Удаляет маяк из списка'), _ru('Удаляет маяк из списка'))),
             help='\n'.join((_('Если маяком воспользовался - будь другом, удали его из списка.'), _ru('Если маяком воспользовался - будь другом, удали его из списка.')))
             )
async def close_beacon(ctx, password):
    _ = translator(ctx.guild.preferred_locale)
    beacon_id = password
    
    with SqliteDict(database_file_path) as beacons:
        if beacon_id in beacons:
            beacon = beacons[beacon_id]
            if beacon['guild'] == ctx.guild.id:
                beacon_author_id = beacon['author']
                beacons.pop(beacon_id)
                beacons.commit()
                beacons.close();
                print(f'{ctx.author.name} put out beacon \"{password}\"')
                await ctx.send(_('<@{0}>, {1} использовал или затушил маяк \"{2}\"').format(beacon_author_id, ctx.author.name, password))


@bot.command(_('маяки'),
             aliases=[_ru('маяки')],
             brief=' | '.join((_('Выводит список всех зажженных маяков'), _ru('Выводит список всех зажженных маяков'))),
             help='\n'.join((_('Список обновляется каждую минуту. Неиспользованные маяки гаснут в игре через час, поэтому они автоматически удаляются из списка. Но всё равно, пожалуйста, удали маяк, если ты им воспользовался.'),_ru('Список обновляется каждую минуту. Неиспользованные маяки гаснут в игре через час, поэтому они автоматически удаляются из списка. Но всё равно, пожалуйста, удали маяк, если ты им воспользовался.')))
             )
async def list_all_beacons(ctx):
    _ = translator(ctx.guild.preferred_locale)
    current_time = datetime.utcnow()
    active_beacons = []
    count = 0
    
    with SqliteDict(database_file_path) as beacons:
        for beacon_id in beacons:
            beacon = beacons[beacon_id]
            if beacon['guild'] == ctx.guild.id and current_time < beacon['expires']:
                count+=1
                time_remains = round((beacon['expires'] - current_time).total_seconds() / 60)
                active_beacons.append([beacon["password"], time_remains, beacon["description"]])
        beacons.close()

    if count <= 0:
        await ctx.send(_('Активных маяков пока нет. Попробуйте позже.'))
    else:
        await ctx.send(_('Активные маяки:```{0}```').format(tabulate(active_beacons, [_('Пароль'), _('Минуты'), _('Описание')])))

bot.run(DISCORD_TOKEN);
