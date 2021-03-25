from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import MainMenu
from bot_utils import EditEvents
from bot_utils import Descriptor
from bot_utils import batch_generator
from db_requests import DBRequests

from datetime import datetime


class BotEvents(BotBase):
    permission = "moderator"
    func_name = "События"

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
        if activity == "События" and student.permissions != 'user':
            descriptor = Descriptor(batch_generator(
                self.database.get_event_name_list(), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Новое событие")
            await EditEvents.select_event.set()
            await message.reply("События", reply_markup=markup)

    async def select_event_handler(
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
            markup.add("Новое событие")
            await message.reply("События", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Новое событие")
            await message.reply("События", reply_markup=markup)
        elif text == 'Новое событие':
            async with state.proxy() as data:
                data['selected_event'] = None
            await EditEvents.new_event_name.set()
            await message.reply(
                "Введите новое имя события",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                event = self.database.get_event(text)
                description = (
                    "Событие: {}\n"
                    "Дата: {}\n"
                    "Постоянное? {}\n"
                    "Преподаватель: {}"
                ).format(
                    event.name, event.date,
                    event.is_regular, event.teacher.name
                )
                async with state.proxy() as data:
                    data['selected_event'] = event.name
                await EditEvents.event_activity.set()
                await message.reply(
                    description,
                    reply_markup=BotBase.event_activity_keyboard()
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def event_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if self.database.get_student(
                telegram_id=str(message.from_user.id)
        ) == 'user':
            await state.finish()
            await message.reply(
                "Ошибка",
                reply_markup=BotBase.none_state_keyboard()
            )
        elif text == "Сменить имя":
            await EditEvents.new_event_name.set()
            await message.reply(
                "Введите новое имя события",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Сменить дату":
            await EditEvents.new_event_date.set()
            await message.reply(
                ("Введите новую дату события\n"
                 "Например, 13.04.21 09:30"),
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Сменить постоянность":
            await EditEvents.new_event_is_regular.set()
            await message.reply(
                "Событие регулярное?",
                reply_markup=BotBase.yes_no_keyboard()
            )
        elif text == "Сменить преподавателя":
            descriptor = Descriptor(batch_generator(
                self.database.get_teacher_name_list(), 5
            ))
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await EditEvents.new_event_teacher.set()
            await message.reply("Новый учитель", reply_markup=markup)
        elif text == "Удалить событие":
            await EditEvents.delete_event_confirm.set()
            await message.reply(
                "Вы уверены?",
                reply_markup=BotBase.yes_no_keyboard()
            )
        else:
            await message.reply("Неверная команда")

    async def new_event_name_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None
            event_name = data['selected_event']
        if text in self.database.get_event_name_list():
            await message.reply("Имя {} занято. Введите другое".format(text))
        elif not is_new_event:
            event = self.database.get_event(event_name)
            event.name = text
            self.database.update_event(event)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                data['new_event_name'] = text
            await EditEvents.new_event_date.set()
            await message.reply(
                ("Введите новую дату события\n"
                 "Например, 13.04.21 09:30"),
                reply_markup=types.ReplyKeyboardRemove()
            )

    async def new_event_date_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None
        try:
            date = datetime.strptime(text, "%d.%m.%y %H:%M")
            async with state.proxy() as data:
                if not is_new_event:
                    event = self.database.get_event(data['selected_event'])
                    event.date = date
                    self.database.update_event(event)
                else:
                    data['new_event_date'] = date
            if not is_new_event:
                await state.finish()
                await message.reply(
                    "Успех",
                    reply_markup=BotBase.none_state_keyboard()
                )
            else:
                await EditEvents.new_event_is_regular.set()
                await message.reply(
                    "Событие регулярное?",
                    reply_markup=BotBase.yes_no_keyboard()
                )
        except ValueError:
            await message.reply("Попробуйте снова")

    async def new_event_is_regular_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None
            event_name = data['selected_event']
        if text not in ['Да', 'Нет']:
            await message.reply("Неверная команда")
        elif not is_new_event:
            event = self.database.get_event(event_name)
            event.is_regular = text == 'Да'
            self.database.update_event(event)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                data['new_event_is_regular'] = text == 'Да'
            descriptor = Descriptor(batch_generator(
                self.database.get_teacher_name_list(), 5
            ))
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await EditEvents.new_event_teacher.set()
            await message.reply("Новый учитель", reply_markup=markup)

    async def new_event_teacher_handler(
            self, message: types.Message, state: FSMContext
    ):
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None

        text = message.text
        telegram_id = str(message.from_user.id)
        descriptor = self.descriptors[telegram_id]
        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("Новый учитель", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("Новый учитель", reply_markup=markup)
        else:
            try:
                teacher = self.database.get_teacher(text)
                if is_new_event:
                    async with state.proxy() as data:
                        try:
                            self.database.add_event(
                                data['new_event_name'],
                                data['new_event_date'],
                                data['new_event_is_regular'],
                                teacher.name
                            )
                            success = True
                        except RuntimeError:
                            success = False
                    await state.finish()
                    if success:
                        await message.reply(
                            "Успех",
                            reply_markup=BotBase.none_state_keyboard()
                        )
                    else:
                        await message.reply(
                            "Ошибка",
                            reply_markup=BotBase.none_state_keyboard()
                        )
                else:
                    async with state.proxy() as data:
                        event_name = data["selected_event"]
                    event = self.database.get_event(
                        event_name
                    )
                    teacher = self.database.get_teacher(text)
                    event.teacher = teacher
                    self.database.update_event(event)
                    await state.finish()
                    await message.reply(
                        "Успех",
                        reply_markup=BotBase.none_state_keyboard()
                    )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def delete_event_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == 'Да':
            with state.proxy() as data:
                event_name = data['selected_event']
            try:
                self.database.delete_event(
                    self.database.get_event(event_name)
                )
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
            lambda message: message.text == BotEvents.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_event_handler,
            state=EditEvents.select_event
        )
        self.dp.register_message_handler(
            self.event_activity_handler,
            state=EditEvents.event_activity
        )
        self.dp.register_message_handler(
            self.new_event_name_handler,
            state=EditEvents.new_event_name
        )
        self.dp.register_message_handler(
            self.new_event_date_handler,
            state=EditEvents.new_event_date
        )
        self.dp.register_message_handler(
            self.new_event_teacher_handler,
            state=EditEvents.new_event_teacher
        )
        self.dp.register_message_handler(
            self.new_event_is_regular_handler,
            state=EditEvents.new_event_is_regular
        )
        self.dp.register_message_handler(
            self.delete_event_confirm_handler,
            state=EditEvents.delete_event_confirm
        )
