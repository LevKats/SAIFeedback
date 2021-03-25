from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import MainMenu
from bot_utils import EditModerators
from bot_utils import Descriptor
from bot_utils import batch_generator
from db_requests import DBRequests


class BotModerators(BotBase):
    permission = "admin"
    func_name = "Модераторы"

    def __init__(self, database: DBRequests, descriptors: dict, dp, bot):
        super().__init__(database, descriptors, dp, bot)
        self.register_handlers()

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        activity = message.text
        telegram_id = str(message.from_user.id)
        student = self.database.get_student(
            telegram_id=telegram_id
        )
        if activity == BotModerators.func_name and \
                student.permissions != 'user':
            descriptor = Descriptor(batch_generator(
                self.database.list_students_names(permissions="moderator"), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditModerators.select_moderator.set()
            await message.reply("Модераторы", reply_markup=markup)

    @staticmethod
    def moderator_activity_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("ОК", "Разжаловать")
        return markup

    async def select_moderator_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        telegram_id = str(message.from_user.id)
        descriptor = self.descriptors[telegram_id]
        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await message.reply("Модераторы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await message.reply("Модераторы", reply_markup=markup)
        elif text == 'Добавить':
            async with state.proxy() as data:
                data['selected_moderator'] = None
            await EditModerators.new_moderator_nickname.set()
            await message.reply(
                "Введите nickname нового модератора",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                moderator = self.database.get_student(nickname=text)
                if moderator.permissions != "moderator":
                    await message.reply("Неверная команда")
                    return
                async with state.proxy() as data:
                    data['selected_moderator'] = moderator.name
                await EditModerators.moderator_activity.set()
                await message.reply(
                    "Модератор: {}".format(
                        moderator,
                    ),
                    reply_markup=BotModerators.moderator_activity_keyboard()
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def new_moderator_nickname_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        try:
            moderator = self.database.get_student(nickname=text)
            if moderator.permissions != 'user':
                await message.reply("Неверное имя. Попробуйте еще")
                return
            moderator.permissions = 'moderator'
            self.database.update_student(moderator)
            await state.finish()
            await message.reply(
                "Успех", reply_markup=BotBase.none_state_keyboard()
            )
        except RuntimeError:
            await message.reply("Неверное имя. Попробуйте еще")

    async def moderator_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        telegram_id = str(message.from_user.id)
        descriptor = self.descriptors[telegram_id]
        if text == "ОК":
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditModerators.select_moderator.set()
            await message.reply("Модераторы", reply_markup=markup)
        elif text == "Разжаловать":
            await EditModerators.delete_moderator_confirm.set()
            await message.reply(
                "Вы уверены?", reply_markup=BotBase.yes_no_keyboard()
            )
        else:
            await message.reply("Неверная команда")

    async def delete_moderator_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == 'Да':
            with state.proxy() as data:
                moderator_name = data['selected_moderator']
            try:
                moderator = self.database.get_student(nickname=moderator_name)
                moderator.permissions = "user"
                self.database.update_student(moderator)
                await state.finish()
                await message.reply(
                    "Успех", reply_markup=BotBase.none_state_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=BotBase.none_state_keyboard()
                )
        elif text == 'Нет':
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=BotBase.none_state_keyboard()
            )
        else:
            await message.reply("Неизвестная команда")

    def register_handlers(self):
        self.dp.register_message_handler(
            self.menu_select_activity_handler,
            lambda message: message.text == BotModerators.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_moderator_handler,
            state=EditModerators.select_moderator
        )
        self.dp.register_message_handler(
            self.moderator_activity_handler,
            state=EditModerators.moderator_activity
        )
        self.dp.register_message_handler(
            self.new_moderator_nickname_handler,
            state=EditModerators.new_moderator_nickname
        )
        self.dp.register_message_handler(
            self.delete_moderator_confirm_handler,
            state=EditModerators.delete_moderator_confirm
        )
