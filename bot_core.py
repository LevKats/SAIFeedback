from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

from bot_base import BotBase
from db_requests import DBRequests
from bot_utils import MainMenu
from bot_utils import RegisterForm

import logging


class BotCore(BotBase):
    def __init__(self, token: str, database: DBRequests, admin_nickname, *args):
        """
        kwargs: {name: (module, permission)}
        """
        self.token = token
        self.bot = Bot(token=self.token)
        self.storage = MemoryStorage()
        self.admin_nickname = admin_nickname

        self.states_list = [
            "никнейм", "группа"
        ]

        descriptors = {}

        super().__init__(
            database, descriptors, Dispatcher(self.bot, storage=self.storage)
        )
        try:
            self.database.add_group("DEFAULT", "email@example.com", "ADMIN")
            logging.info("Group DEFAULT added")
        except RuntimeError:
            logging.info("Group DEFAULT existed")

        self.register_handlers()

        self.modules = []

        self.main_menu_keyboards = {
            "user": types.ReplyKeyboardMarkup(
                resize_keyboard=True, selective=True
            ),
            "moderator": types.ReplyKeyboardMarkup(
                resize_keyboard=True, selective=True
            ),
            "admin": types.ReplyKeyboardMarkup(
                resize_keyboard=True, selective=True
            ),
        }
        permissions = {"user": 0, "moderator": 1, "admin": 2}

        for module in args:
            priority = permissions[module.permission]
            for permission in self.main_menu_keyboards:
                if priority <= permissions[permission]:
                    self.main_menu_keyboards[permission].add(module.func_name)
            self.modules.append(module(database, descriptors, self.dp))
        for permission in self.main_menu_keyboards:
            self.main_menu_keyboards[permission].add("Помощь")

    async def start_handler(self, message: types.Message):
        telegram_id = str(message.from_user.id)
        try:
            student = self.database.get_student(telegram_id=telegram_id)
            await message.reply(
                ("Здравствуйте, {}!\n"
                 "Используйте /help если не знаете, что делать"
                 ).format(student.nickname))
            # Set state
        except RuntimeError:
            await RegisterForm.nickname.set()
            await message.reply(
                "Здравствуйте! Как к Вам обращаться (nickname)?\n" +
                BotBase.state_description(self.states_list, 0)
            )

    async def help_handler(self, message: types.Message, state: FSMContext):
        if state is not None:
            await state.finish()
        telegram_id = str(message.from_user.id)
        try:
            student = self.database.get_student(telegram_id=telegram_id)
            await message.reply(
                ("Ваше имя {}\n"
                 "Используйте /start для начала общения с ботом\n"
                 "Используйте /menu для открытия меню").format(
                    student.nickname
                ),
                reply_markup=BotBase.none_state_keyboard()
            )
        except RuntimeError:
            await message.reply(
                ("Используйте /start для начала общения с ботом\n"
                 "Используйте /menu для открытия меню"),
                reply_markup=BotBase.none_state_keyboard()
            )

    async def nickname_handler(
            self, message: types.Message, state: FSMContext
    ):
        nicknames = self.database.list_students_names()
        if message.text in nicknames:
            await message.reply(
                "К сожалению, имя {} занято. Введите другое.".format(
                    message.text
                )
            )
        else:
            nickname = message.text
            telegram_id = str(message.from_user.id)
            self.database.add_student(
                nickname, telegram_id, "DEFAULT", "user"
            )
            student = self.database.get_student(nickname=nickname)
            student.chat_id = message.chat.id
            self.database.update_student(student)
            async with state.proxy() as data:
                data['telegram_id'] = telegram_id
                data['nickname'] = nickname
            await RegisterForm.next()

            markup = self.group_selection_keyboard()
            await message.reply(
                "Приятно познакомиться, {}! В какой вы группе?\n".format(
                    nickname
                ) + BotBase.state_description(self.states_list, 1),
                reply_markup=markup
            )

    async def group_handler(
            self, message: types.Message, state: FSMContext
    ):
        group = message.text
        async with state.proxy() as data:
            if group in self.database.list_groups():
                data['group'] = group
                student = self.database.get_student(
                    telegram_id=data["telegram_id"]
                )
                student.group = self.database.get_group(group)
                self.database.update_student(student)
                await state.finish()
                # await MainMenu.select_activity.set()
                await message.reply(
                    "Установлена группа {}".format(group),
                    reply_markup=BotBase.none_state_keyboard()
                )
            elif group == "Нет в списке":
                student = self.database.get_student(
                    telegram_id=str(message.from_user.id)
                )
                if student.permissions == "user":
                    await state.finish()
                    await message.reply(
                        ("Пока Вам назначена группа по умолчанию."
                         " Напишите {}, чтобы группу добавили и"
                         " измените группу в своем профиле позже").format(
                            self.admin_nickname
                        ),
                        reply_markup=BotBase.none_state_keyboard()
                    )
                else:
                    await state.finish()
                    await message.reply(
                        ("Пока Вам назначена группа по умолчанию."
                         " Добавьте новую группу и"
                         " измените группу в своем профиле позже"),
                        reply_markup=BotBase.none_state_keyboard()
                    )
            else:
                markup = self.group_selection_keyboard()
                await message.reply(
                    "Нет группы {}. Попробуйте еще раз".format(
                        group
                    ), reply_markup=markup
                )

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        telegram_id = str(message.from_user.id)
        try:
            student = self.database.get_student(telegram_id=telegram_id)
        except RuntimeError:
            await message.reply(
                "Бот пока с не знаком с Вами. Используйте /start"
            )
            return
        if message.text == "Помощь":
            await state.finish()
            await message.reply(
                "Используйте /help", reply_markup=BotBase.none_state_keyboard()
            )
        else:
            markup = self.main_menu_keyboards[student.permissions]
            await message.reply(
                "Неверное действие. Попробуйте еще раз",
                reply_markup=markup
            )

    async def menu_handler(self, message: types.Message, state: FSMContext):
        if state is not None:
            await state.finish()
        telegram_id = str(message.from_user.id)
        try:
            student = self.database.get_student(telegram_id=telegram_id)
        except RuntimeError:
            await message.reply(
                "Бот пока с не знаком с Вами. Используйте /start"
            )
            return
        markup = self.main_menu_keyboards[student.permissions]
        await MainMenu.select_activity.set()
        await message.reply("Главное меню", reply_markup=markup)

    def register_handlers(self):
        self.dp.register_message_handler(
            self.start_handler, commands='start'
        )
        self.dp.register_message_handler(
            self.help_handler, commands='help', state="*"
        )
        self.dp.register_message_handler(
            self.menu_handler, commands="menu", state="*"
        )

        self.dp.register_message_handler(
            self.nickname_handler, state=RegisterForm.nickname
        )
        self.dp.register_message_handler(
            self.group_handler, state=RegisterForm.group
        )

        self.dp.register_message_handler(
            self.menu_select_activity_handler,
            lambda message: message.text not in [
                module.func_name for module in self.modules
            ], state=MainMenu.select_activity
        )

    def start_polling(self):
        executor.start_polling(self.dp, skip_updates=True)
