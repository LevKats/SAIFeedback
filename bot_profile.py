from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import Profile
from bot_utils import RegisterForm
from bot_utils import MainMenu
from db_requests import DBRequests


class BotProfile(BotBase):
    permission = "user"
    func_name = "Профиль"

    def __init__(self, database: DBRequests, descriptors: dict, dp):
        super().__init__(database, descriptors, dp)
        self.register_handlers()

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        activity = message.text
        telegram_id = str(message.from_user.id)
        student = self.database.get_student(
            telegram_id=telegram_id
        )
        if activity == BotProfile.func_name:
            await Profile.print_profile.set()
            await message.reply(
                ("Ваш профиль:\n"
                 "Имя: {}\n"
                 "Группа: {}\n"
                 "telegram id: {}").format(
                    student.nickname, student.group.name,
                    student.telegram_id
                ),
                reply_markup=BotBase.profile_keyboard()
            )

    async def print_profile_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "сменить имя":
            await Profile.edit_nickname.set()
            await message.reply(
                "Введите новое имя",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "сменить группу":
            async with state.proxy() as data:
                data["telegram_id"] = str(message.from_user.id)
            await RegisterForm.group.set()
            await message.reply(
                "Выберите группу",
                reply_markup=self.group_selection_keyboard()
            )
        elif text == "удалить профиль":
            await Profile.delete_profile_confirm.set()
            markup = BotBase.yes_no_keyboard()
            await message.reply(
                "Вы уверены?", reply_markup=markup
            )
        else:
            await message.reply("Неверная команда")

    async def edit_nickname_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "Да":
            async with state.proxy() as data:
                new_nickname = data['new_nickname']
            if new_nickname in self.database.list_students_names():
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                try:
                    student = self.database.get_student(
                        telegram_id=str(message.from_user.id)
                    )
                    student.nickname = new_nickname
                    self.database.update_student(student)
                    await state.finish()
                    await message.reply(
                        "Успех", reply_markup=types.ReplyKeyboardRemove()
                    )
                except RuntimeError:
                    await state.finish()
                    await message.reply(
                        "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                    )
        elif text == "Нет":
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неверная команда")

    async def edit_nickname_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text in self.database.list_students_names():
            await message.reply("Имя {} занято".format(text))
        else:
            async with state.proxy() as data:
                data['new_nickname'] = text
            markup = BotBase.yes_no_keyboard()
            await Profile.edit_nickname_confirm.set()
            await message.reply("Вы уверены?", reply_markup=markup)

    async def delete_profile_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "Да":
            try:
                self.database.delete_student(
                    self.database.get_student(
                        telegram_id=str(message.from_user.id)
                    )
                )
                await state.finish()
                await message.reply(
                    "Удалено", reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ощибка", reply_markup=types.ReplyKeyboardRemove()
                )
        elif text == "Нет":
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неверная команда")

    def register_handlers(self):
        self.dp.register_message_handler(
            self.menu_select_activity_handler,
            lambda message: message.text == BotProfile.func_name,
            state=MainMenu.select_activity,
        )
        self.dp.register_message_handler(
            self.print_profile_handler,
            state=Profile.print_profile
        )
        self.dp.register_message_handler(
            self.delete_profile_confirm_handler,
            state=Profile.delete_profile_confirm
        )
        self.dp.register_message_handler(
            self.edit_nickname_handler,
            state=Profile.edit_nickname
        )
        self.dp.register_message_handler(
            self.edit_nickname_confirm_handler,
            state=Profile.edit_nickname_confirm
        )
