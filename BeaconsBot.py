import discord
import os

from dotenv import load_dotenv
from sqlitedict import SqliteDict
from discord.ext import commands
from datetime import datetime
from datetime import timedelta
from tabulate import tabulate

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_PREFIX = os.getenv('BOT_PREFIX')

bot = commands.Bot(command_prefix=BOT_PREFIX)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

@bot.event
async def on_message(message):
    if bot.user.mentioned_in(message):
        await message.channel.send(f'Веду список активных маяков. \nПрефикс для команд: **{bot.command_prefix}**\nПопробуй команду: ```{bot.command_prefix}help```')
    await bot.process_commands(message)

@bot.command('маяк', aliases=['beacon', 'зажечь'], brief=f'Добавляет маяк в список.', help='Если построил и зажёг маяк - добавь его в список.')
async def new_beacon(ctx, password, *, description = ''):
    beacon_id = password
    current_time = datetime.utcnow()
    expires_time = current_time + timedelta(hours = 1)
    
    with SqliteDict('beacons.db.sqlite') as beacons:
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
            await ctx.send('Маяк с таким паролем уже существует.')
        beacons.close();

        print(f'{ctx.author.name} lit a new beacon \"{password}\" at {ctx.guild.name}')
        await ctx.send(f'{ctx.author.mention} зажёг новый маяк: \"{password}\"\n{description}')


@bot.command('удалить', aliases=['putout', 'использован', 'затушить', 'потушить'], brief='Удаляет маяк из списка.', help='Если маяком воспользовался - будь другом, удали его из списка.')
async def close_beacon(ctx, password):
    beacon_id = password
    
    with SqliteDict('beacons.db.sqlite') as beacons:
        if beacon_id in beacons:
            beacon = beacons[beacon_id]
            if beacon['guild'] == ctx.guild.id:
                beacon_author_id = beacon['author']
                beacons.pop(beacon_id)
                beacons.commit()
                beacons.close();
                print(f'{ctx.author.name} put out beacon \"{password}\"')
                await ctx.send(f'<@{beacon_author_id}>, {ctx.author.name} использовал или затушил маяк \"{password}\"')

@bot.command('маяки', aliases=['list'], brief='Выводит список всех зажженных маяков.', help='Список обновляется каждую минуту. Неиспользованные маяки гаснут в игре через час, поэтому они автоматически удаляются из списка. Но всё равно, пожалуйста, удали маяк, если ты им воспользовался.')
async def list_all_beacons(ctx):
    current_time = datetime.utcnow()
    active_beacons = []
    count = 0
    
    with SqliteDict('beacons.db.sqlite') as beacons:
        for beacon_id in beacons:
            beacon = beacons[beacon_id]
            if beacon['guild'] == ctx.guild.id and current_time < beacon['expires']:
                count+=1
                time_remains = round((beacon['expires'] - current_time).total_seconds() / 60)
                active_beacons.append([beacon["password"], time_remains, beacon["description"]])
        beacons.close()

    if count <= 0:
        await ctx.send(f'Активных маяков пока нет. Попробуйте позже.')
    else:
        await ctx.send('Активные маяки:```' + tabulate(active_beacons, ['Пароль', 'Минуты', 'Описание']) + '```')

bot.run(DISCORD_TOKEN);
