from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import MainMenu
from bot_utils import EditGroups
from bot_utils import Descriptor
from bot_utils import batch_generator
from db_requests import DBRequests


class BotGroups(BotBase):
    permission = "moderator"
    func_name = "Группы"

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
        if activity == BotGroups.func_name and student.permissions != 'user':
            await EditGroups.select_group.set()
            markup = self.group_selection_keyboard("Новая группа")
            await message.reply("Группы", reply_markup=markup)

    async def select_group_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "Новая группа":
            async with state.proxy() as data:
                data['selected_group'] = None
            await EditGroups.new_group_name.set()
            await message.reply(
                "Введите новое имя группы",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                group = self.database.get_group(text)
                async with state.proxy() as data:
                    data['selected_group'] = group.name
                markup = BotBase.group_activity_keyboard()
                await EditGroups.group_activity.set()
                await message.reply(
                    ("Группа: {}\n"
                     "email: {}\n"
                     "Контакты старосты: {}").format(
                        group.name, group.email, group.monitor
                    ),
                    reply_markup=markup)
            except RuntimeError:
                await message.reply("Неверная команда")

    async def group_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            group_name = data['selected_group']

        if self.database.get_student(
                telegram_id=str(message.from_user.id)
        ).permissions == 'user':
            await state.finish()
            await message.reply(
                "Ошибка", reply_markup=BotBase.none_state_keyboard()
            )
        elif text == "Сменить имя":
            await EditGroups.new_group_name.set()
            await message.reply(
                "Введите новое имя группы",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Сменить email":
            await EditGroups.new_group_email.set()
            await message.reply(
                "Введите новый email",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Сменить старосту":
            await EditGroups.new_group_monitor.set()
            await message.reply(
                "Новый контакт старосты",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Удалить группу":
            await EditGroups.delete_group_confirm.set()
            await message.reply(
                "Удалить группу?", BotBase.yes_no_keyboard()
            )
        elif text == "События группы":
            try:
                descriptor = Descriptor(
                    batch_generator(
                        self.database.group_event_list(
                            self.database.get_group(group_name)
                        ), 5),
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=BotBase.none_state_keyboard()
                )
                return
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditGroups.select_group_event.set()
            await message.reply("События группы", reply_markup=markup)
        else:
            await message.reply("Неверная команда")

    async def select_group_event_handler(
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
            await message.reply("События группы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await message.reply("События группы", reply_markup=markup)
        elif text == 'Добавить':
            await EditGroups.add_group_event_select.set()
            try:
                descriptor = Descriptor(
                    batch_generator(
                        self.database.get_event_name_list(), 5),
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=BotBase.none_state_keyboard()
                )
                return
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("События", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data['selected_event'] = event.name
                    teacher_name = event.teacher.name
                await EditGroups.delete_group_event_confirm.set()
                await message.reply(
                    ("Имя: {}\n"
                     "Дата: {}\n"
                     "Регулярное?: {}\n"
                     "Преподаватель: {}\n"
                     "УДАЛИТЬ?").format(
                        event.name, event.date, event.is_regular,
                        teacher_name),
                    reply_markup=BotBase.yes_no_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=BotBase.none_state_keyboard()
                )

    async def add_group_event_select_handler(
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
            await message.reply("События группы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("События группы", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    self.database.add_group_event(
                        data['selected_group'], text
                    )
                await state.finish()
                await message.reply(
                    "Успех",
                    reply_markup=BotBase.none_state_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=BotBase.none_state_keyboard()
                )

    async def delete_group_event_confirm_handler(
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
        elif text == 'Да':
            try:
                async with state.proxy() as data:
                    self.database.delete_group_event(
                        self.database.get_group(data['selected_group']),
                        self.database.get_event(data['selected_event'])
                    )
                await state.finish()
                await message.reply(
                    "Успех",
                    reply_markup=BotBase.none_state_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=BotBase.none_state_keyboard()
                )
        elif text == 'Нет':
            await state.finish()
            await message.reply(
                "ОК",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            await message.reply(
                "Неверная команда",
            )

    async def new_group_name_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_group = data['selected_group'] is None
            group_name = data['selected_group']
        if text in self.database.list_groups():
            await message.reply("Имя {} занято. Введите другое".format(text))
        elif not is_new_group:
            group = self.database.get_group(group_name)
            group.name = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                data['new_group_name'] = text
            await EditGroups.new_group_email.set()
            await message.reply(
                "Введите новый email",
                reply_markup=types.ReplyKeyboardRemove()
            )

    async def new_group_email_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_group = data['selected_group'] is None
            group_name = data['selected_group']
        if not is_new_group:
            group = self.database.get_group(group_name)
            group.email = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                data['new_group_email'] = text
            await EditGroups.new_group_monitor.set()
            await message.reply(
                "Новый контакт старосты",
                reply_markup=types.ReplyKeyboardRemove()
            )

    async def new_group_monitor_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_group = data['selected_group'] is None
            group_name = data['selected_group']
        if not is_new_group:
            group = self.database.get_group(group_name)
            group.monitor = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                try:
                    self.database.add_group(
                        data['new_group_name'], data['new_group_email'], text
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

    async def delete_group_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == 'Да':
            with state.proxy() as data:
                group_name = data['selected_group']
            try:
                self.database.delete_group(
                    self.database.get_group(group_name)
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
            lambda message: message.text == BotGroups.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_group_handler,
            state=EditGroups.select_group
        )
        self.dp.register_message_handler(
            self.group_activity_handler,
            state=EditGroups.group_activity
        )
        self.dp.register_message_handler(
            self.new_group_name_handler,
            state=EditGroups.new_group_name
        )
        self.dp.register_message_handler(
            self.new_group_email_handler,
            state=EditGroups.new_group_email
        )
        self.dp.register_message_handler(
            self.new_group_monitor_handler,
            state=EditGroups.new_group_monitor
        )
        self.dp.register_message_handler(
            self.select_group_event_handler,
            state=EditGroups.select_group_event
        )
        self.dp.register_message_handler(
            self.delete_group_event_confirm_handler,
            state=EditGroups.delete_group_event_confirm
        )
        self.dp.register_message_handler(
            self.add_group_event_select_handler,
            state=EditGroups.add_group_event_select
        )
        self.dp.register_message_handler(
            self.delete_group_confirm_handler,
            state=EditGroups.delete_group_confirm
        )
