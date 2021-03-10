from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor

from bot_base import BotBase
from db_requests import DBRequests
from bot_utils import MainMenu
from bot_utils import RegisterForm


class BotCore(BotBase):
    def __init__(self, token: str, database: DBRequests, admin_nickname, *args):
        """
        kwargs: {name: (module, permission)}
        """
        self.token = token
        self.bot = Bot(token=self.token)
        self.storage = MemoryStorage()
        self.admin_nickname = admin_nickname

        descriptors = {}

        super().__init__(
            database, descriptors, Dispatcher(self.bot, storage=self.storage)
        )
        self.register_handlers()

        self.modules = []
        self.main_menu_markup_user = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        self.main_menu_markup_moderator = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )

        permissions = {"user": 0, "moderator": 1, "admin": 2}

        for module in args:
            priority = permissions[module.permission]
            if priority >= permissions['moderator']:
                self.main_menu_markup_moderator.add(module.func_name)
            if priority >= permissions['user']:
                self.main_menu_markup_user.add(module.func_name)
            self.modules.append(module(database, descriptors, self.dp))
        self.main_menu_markup_user.add("Помощь")
        self.main_menu_markup_moderator.add("Помощь")

    async def start_handler(self, message: types.Message):
        telegram_id = str(message.from_user.id)
        try:
            student = self.database.get_student(telegram_id=telegram_id)
            await message.reply(
                ("Здравствуйте, {}!\n"
                 "Ипользуйте /help если не знаете, что делать"
                 ).format(student.nickname))
            # Set state
        except RuntimeError:
            await RegisterForm.nickname.set()
            await message.reply(
                "Здравствуйте! Как к Вам обращаться (nickname)?"
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
                )
            )
        except RuntimeError:
            await message.reply(
                ("Используйте /start для начала общения с ботом\n"
                 "Используйте /menu для открытия меню")
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
            async with state.proxy() as data:
                data['telegram_id'] = telegram_id
                data['nickname'] = nickname
            await RegisterForm.next()

            markup = self.group_selection_keyboard()
            await message.reply(
                "Приятно познакомиться, {}! В какой вы группе?".format(
                    nickname
                ), reply_markup=markup
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
                    reply_markup=types.ReplyKeyboardRemove()
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
                        reply_markup=types.ReplyKeyboardRemove()
                    )
                else:
                    await state.finish()
                    await message.reply(
                        ("Пока Вам назначена группа по умолчанию."
                         " Добавьте новую группу и"
                         " измените группу в своем профиле позже"),
                        reply_markup=types.ReplyKeyboardRemove()
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
                "Используйте /help", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            if student.permissions == 'user':
                markup = self.main_menu_markup_user
            else:
                markup = self.main_menu_markup_moderator
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
        if student.permissions == 'user':
            markup = self.main_menu_markup_user
        else:
            markup = self.main_menu_markup_moderator
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
