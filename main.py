from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from typing import List

import logging

from whoami_player import session, Player

API_TOKEN = "5566294805:AAHBm87FAti2DnpcxBG6VsSuqbBSRzHrn1M"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

join_button = KeyboardButton("приєднатися за кодом")
create_button = KeyboardButton("створити нову")
stop_button = KeyboardButton("зупинити")
start_button = KeyboardButton("почати гру 🚀")
name_button = KeyboardButton("побачити хто я 👀")

inactive_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(join_button, create_button)
pregame_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(start_button, stop_button)
ingame_keyboard = ReplyKeyboardMarkup(resize_keyboard=True).row(name_button, stop_button)


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.full_name
    q = session.query(Player).filter(Player.id == user_id)
    if not session.query(q.exists()).scalar():
        new_player = Player(user_id, username)
        session.add(new_player)
        session.commit()
    await message.answer("добрий день!", reply_markup=inactive_keyboard)


@dp.message_handler(lambda message: message.text == "приєднатися за кодом")
async def join(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if user.status == user.INACTIVE:
        if current_game.is_on:
            user.status = Player.WAITING
            answer = current_game.create_list(user.status, user_id)
            list_message = await message.answer(f"список гравців:\n{answer}", reply_markup=ReplyKeyboardRemove())
            user.list_id = list_message.message_id
            session.commit()
            current_game.players.append(user_id)
            await message.answer("вибач, друже, гра вже почалася", reply_markup=ReplyKeyboardRemove())
        else:
            user.status = Player.PREGAME
            session.commit()
            current_game.players.append(user_id)
            answer = current_game.create_list(user.status, user_id)
            for id in current_game.players:
                player = session.query(Player).filter(Player.id == id).first()
                if id == user_id or not player.list_id:
                    list_message = await bot.send_message(player.id, f"список гравців:\n{answer}")
                    player.list_id = list_message.message_id
                else:
                    await bot.edit_message_text(f"список гравців:\n{answer}", player.id, player.list_id)
            await message.answer("почніть гру, коли всі приєднаються", reply_markup=pregame_keyboard)
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "зупинити")
async def cancel_game(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if user.status == Player.WAITING or user.status == Player.INACTIVE:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)
    else:
        players: List[Player] = session.query(Player).filter(Player.id.in_(current_game.players))
        for player in players:
            player.status = Player.INACTIVE
            player.secret_name = ""
            player.replay_id = 0
            current_game.is_on = False
            current_game.players = []
            await bot.send_message(player.id, "гра зупинена", reply_markup=inactive_keyboard)
        session.commit()
        current_game.players = []
        current_game.is_on = False


@dp.message_handler(lambda message: message.text == "почати гру 🚀")
async def start_game(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if user.status == Player.PREGAME:
        if not current_game.is_on:
            players: List[Player] = session.query(Player).filter(Player.id.in_(current_game.players))
            for j, player in enumerate(players):
                player.status = Player.INGAME
                await bot.delete_message(player.id, player.list_id)
                player.list_id = 0
                await bot.send_message(player.id, "запускаємо гру!")
                fellow = players[j - 1]
                replay_message = await bot.send_message(player.id,
                                                        f"загадай персонажа або особу для _{fellow.username}_ "
                                                        f"у відповідь на це повідомлення", parse_mode="Markdown",
                                                        reply_markup=ReplyKeyboardRemove())
                fellow.replay_id = replay_message.message_id
            session.commit()
            current_game.is_on = True
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler(lambda message: message.text == "побачити хто я 👀")
async def get_name(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if user.status == user.INGAME:
        user.status = Player.WAITING
        session.commit()
        players: List[Player] = session.query(Player).filter(Player.id.in_(current_game.players))
        end_of_game = all(player.status == Player.WAITING for player in players)
        for player in players:
            answer = current_game.create_list(player.status, player.id)
            await bot.edit_message_text(f"список гравців:\n{answer}", chat_id=player.id, message_id=player.list_id)
            if end_of_game:
                await bot.send_message(player.id, "_the end!_", parse_mode='Markdown', reply_markup=inactive_keyboard)
                player.status = Player.INACTIVE
                player.secret_name = ""
                player.replay_id = 0
                current_game.is_on = False
                current_game.players = []
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


@dp.message_handler()
async def assign_name(message: types.Message):
    user_id = message.from_id
    user: Player = session.query(Player).filter(Player.id == user_id).first()
    if message.reply_to_message is None:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)
        return
    replay_id = message.reply_to_message.message_id
    q = session.query(Player).filter(Player.replay_id == replay_id)
    if session.query(q.exists()).scalar() and user.status == Player.INGAME and current_game.is_on:
        fellow: Player = q.first()
        fellow.secret_name = message.text
        session.commit()
        players: List[Player] = session.query(Player).filter(Player.id.in_(current_game.players))
        if all(player.secret_name != "" for player in players):
            for player in players:
                await bot.send_message(player.id, "починаємо!", reply_markup=ingame_keyboard)
                answer = current_game.create_list(player.status, player.id)
                list_message = await bot.send_message(player.id, f"список гравців:\n{answer}")
                player.list_id = list_message.message_id
            session.commit()
        else:
            await message.answer("всьо супер, зачекай інших", reply_markup=ingame_keyboard)
    else:
        await message.answer("немає такого варіянту", reply_markup=message.reply_markup)


class Game:
    is_on: bool = False
    players: List[int] = []

    def __init__(self):
        self.is_on = False

    def create_list(self, status, exclude_id):
        answer = ""
        players: List[Player] = session.query(Player).filter(Player.id.in_(self.players))
        if status == Player.INGAME:
            for player in players:
                if player.id != exclude_id:
                    answer += f"$ {player.username} -- {player.secret_name}"
                    answer += " ✅\n" if player.status == Player.WAITING else "\n"
        elif status == Player.PREGAME:
            for player in players:
                answer += f"{player.username}\n"
        elif status == Player.WAITING:
            for player in players:
                answer += f"{player.username} -- {player.secret_name}"
                answer += " ✅\n" if player.status == Player.WAITING else "\n"
        elif status == Player.INACTIVE:
            answer += f"немає такого варіянту"
        if answer == "":
            answer = "ти тут сам"
        return answer


if __name__ == "__main__":
    for p in session.query(Player).all():
        p.status = Player.INACTIVE
        p.secret_name = ""
    session.commit()
    current_game = Game()
    executor.start_polling(dp, skip_updates=True)
