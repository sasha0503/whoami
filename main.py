import random

import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InputMediaPhoto
from typing import List

import logging

from whoami_player import session, Player, Game

API_TOKEN = "5566294805:AAHBm87FAti2DnpcxBG6VsSuqbBSRzHrn1M"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

join_button = KeyboardButton("приєднатися за кодом")
create_button = KeyboardButton("створити нову")
stop_button = KeyboardButton("зупинити")
back_button = KeyboardButton("⬅ ️назад")
start_button = KeyboardButton("почати гру 🚀")
name_button = KeyboardButton("побачити хто я 👀")
cat_button = KeyboardButton("подивитися котів")

inactive_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(join_button, create_button)
pregame_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(start_button, stop_button)
ingame_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(name_button, stop_button)
joining_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(back_button)
waiting_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(cat_button)

keyboards = {
    Player.INGAME: ingame_keyboard,
    Player.PREGAME: pregame_keyboard,
    Player.GETTINGNAME: ReplyKeyboardMarkup(),
    Player.WAITING: ReplyKeyboardMarkup(),
    Player.INACTIVE: inactive_keyboard,
    Player.JOINING: joining_keyboard
}


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = random.choice(emoji) + message.from_user.full_name
    q = session.query(Player).filter(Player.id == user_id)
    if not session.query(q.exists()).scalar():
        user = Player(user_id, username)
        session.add(user)
        session.commit()
    else:
        user: Player = q.first()
    await message.answer("добрий день!", reply_markup=keyboards[user.status])


emoji = ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐸', '🐷', '🐮', '🦁', '🐯', '🐨', '🐻', '🐥', '🦄', '🐝', '🐳']


async def check_user(user: Player, message: types.Message):
    if user is None:
        user_id = message.from_id
        username = random.choice(emoji) + message.from_user.full_name
        new_player = Player(user_id, username)
        session.add(new_player)
        session.commit()
        await message.answer("бот оновився, піф-паф", reply_markup=inactive_keyboard)
        return True
    return False


@dp.message_handler(lambda message: message.text == "приєднатися за кодом")
async def join(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.INACTIVE:
        await bot.send_message(user.id, f"🔐 надішли код гри", reply_markup=ReplyKeyboardRemove())
        user.status = Player.JOINING
        session.commit()
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "подивитися котів")
async def join(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.WAITING:
        cat = "test"
        while cat[-3:] != "jpg":
            r = requests.get("https://api.thecatapi.com/v1/images/search")
            cat = r.json()[0]["url"]
        if user.cat_id is None:
            msg = await bot.send_photo(user.id, photo=cat)
            user.cat_id = msg.message_id
            session.commit()
        else:
            await bot.edit_message_media(InputMediaPhoto(type="photo", media=cat), user.id, user.cat_id)
    else:
        await message.answer("спочатку треба виграти", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "⬅ ️назад")
async def join(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == user.JOINING:
        user.status = Player.INACTIVE
        session.commit()
        await message.answer("головне меню", reply_markup=inactive_keyboard)
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "створити нову")
async def create(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.INACTIVE:
        user.status = Player.PREGAME
        current_game = Game(user_id)
        session.add(current_game)
        user.game = current_game
        await bot.send_message(user.id, f"🔑 код гри: `{current_game.id}`", parse_mode="Markdown")
        answer = current_game.create_list(user.status, user_id)
        list_message = await bot.send_message(user.id, f"Список гравців:\n{answer}")
        user.list_id = list_message.message_id
        await message.answer("почніть гру, коли всі приєднаються", reply_markup=pregame_keyboard)
        session.commit()
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "зупинити")
async def cancel_game(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.INGAME or user.status == Player.PREGAME:
        current_game = user.game
        players: List[Player] = current_game.players
        for player in players:
            answer = current_game.create_list(Player.WAITING, player.id)
            await bot.edit_message_text(f"список гравців:\n{answer}", chat_id=player.id, message_id=player.list_id)
            player.status = Player.INACTIVE
            player.secret_name = ""
            user.cat_id = None
            player.game = None
            await bot.send_message(player.id, "гра зупинена", reply_markup=inactive_keyboard)
        session.delete(current_game)
        session.commit()
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "почати гру 🚀")
async def start_game(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.PREGAME:
        current_game = user.game
        if current_game and not current_game.is_on:
            players: List[Player] = current_game.players
            for j, player in enumerate(players):
                player.status = Player.GETTINGNAME
                await bot.delete_message(player.id, player.list_id)
                player.list_id = 0
                await bot.send_message(player.id, "запускаємо гру!")
                fellow = players[j - 1]
                player.fellow_id = fellow.id
                await bot.send_message(player.id, f"📝 загадай персонажа або людину для _{fellow.username[1:]}_ ",
                                       parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())
            current_game.is_on = True
            session.commit()
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "побачити хто я 👀")
async def get_name(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == user.INGAME:
        user.status = Player.WAITING
        session.commit()
        current_game = user.game
        players: List[Player] = current_game.players
        end_of_game = all(player.status == Player.WAITING for player in players)
        for player in players:
            answer = current_game.create_list(player.status, player.id)
            await bot.edit_message_text(f"список гравців:\n{answer}", chat_id=player.id, message_id=player.list_id)
        if end_of_game:
            for player in players:
                await bot.send_message(player.id, "_the end!_", parse_mode='Markdown', reply_markup=inactive_keyboard)
                player.status = Player.INACTIVE
                player.cat_id = None
                player.secret_name = ""
                session.delete(current_game)
        else:
            await message.answer("вітаю! чекаємо інших", reply_markup=waiting_keyboard)
        session.commit()
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler()
async def assign_name(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if await check_user(user, message):
        return
    if user.status == Player.JOINING:
        q = session.query(Game).filter(Game.id == message.text)
        if session.query(q.exists()).scalar():
            current_game = q.first()
            if current_game.is_on:
                user.status = Player.INACTIVE
                session.commit()
                await message.answer("сорі, гра вже почалася", reply_markup=inactive_keyboard)
            else:
                user.game = current_game
                user.status = Player.PREGAME
                answer = current_game.create_list(user.status, user_id)
                for player in current_game.players:
                    if player.id == user_id or not player.list_id:
                        list_message = await bot.send_message(player.id, f"список гравців:\n{answer}")
                        await bot.send_message(player.id, "почніть гру, коли всі приєднаються",
                                               reply_markup=pregame_keyboard)
                        player.list_id = list_message.message_id
                    else:
                        await bot.edit_message_text(f"список гравців:\n{answer}", player.id, player.list_id)
        else:
            await message.answer("немає такої гри 🤷‍♂️", reply_markup=joining_keyboard)
    elif user.status == Player.GETTINGNAME:
        current_game = user.game
        if current_game and current_game.is_on:
            fellow: Player = session.query(Player).filter(Player.id == user.fellow_id).first()
            fellow.secret_name = message.text
            user.status = Player.INGAME
            session.commit()
            players: List[Player] = current_game.players
            if all(player.secret_name != "" for player in players):
                for player in players:
                    await bot.send_message(player.id, "починаємо!", reply_markup=ingame_keyboard)
                    answer = current_game.create_list(player.status, player.id)
                    list_message = await bot.send_message(player.id, f"список гравців:\n{answer}")
                    player.list_id = list_message.message_id
                session.commit()
            else:
                await message.answer("всьо супер, зачекай інших")
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
