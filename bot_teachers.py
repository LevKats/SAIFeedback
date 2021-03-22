from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import MainMenu
from bot_utils import EditTeachers
from bot_utils import Descriptor
from bot_utils import batch_generator
from db_requests import DBRequests


class BotTeachers(BotBase):
    permission = "moderator"
    func_name = "Учителя"

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
        if activity == BotTeachers.func_name and student.permissions != 'user':
            descriptor = Descriptor(batch_generator(
                self.database.get_teacher_name_list(), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditTeachers.select_teacher.set()
            await message.reply("Учителя", reply_markup=markup)

    async def select_teacher_handler(
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
            await message.reply("События", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await message.reply("События", reply_markup=markup)
        elif text == 'Добавить':
            async with state.proxy() as data:
                data['selected_teacher'] = None
            await EditTeachers.new_teacher_name.set()
            await message.reply(
                "Введите новое имя (ФИО) учителя",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                teacher = self.database.get_teacher(text)
                async with state.proxy() as data:
                    data['selected_teacher'] = teacher.name
                await EditTeachers.teacher_activity.set()
                await message.reply(
                    ("Преподаватель: {}\n"
                     "email: {}").format(
                        teacher.name, teacher.email,
                    ),
                    reply_markup=BotBase.teacher_activity_keyboard()
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def teacher_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text

        if self.database.get_student(
                telegram_id=str(message.from_user.id)
        ).permissions == 'user':
            await state.finish()
            await message.reply(
                "Ошибка", reply_markup=BotBase.none_state_keyboard()
            )
        elif text == "Сменить имя":
            await EditTeachers.new_teacher_name.set()
            await message.reply(
                "Введите новое имя (ФИО) учителя",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Сменить email":
            await EditTeachers.new_teacher_email.set()
            await message.reply(
                "Введите новый email",
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Удалить преподавателя":
            await EditTeachers.delete_teacher_confirm.set()
            await message.reply(
                "Удалить преподавателя?", BotBase.yes_no_keyboard()
            )
        else:
            await message.reply("Неверная команда")

    async def new_teacher_name_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_teacher = data['selected_teacher'] is None
            teacher_name = data['selected_teacher']
        if text in self.database.get_teacher_name_list():
            await message.reply("Имя {} занято. Введите другое".format(text))
        elif not is_new_teacher:
            teacher = self.database.get_teacher(teacher_name)
            teacher.name = text
            self.database.update_teacher(teacher)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                data['new_teacher_name'] = text
            await EditTeachers.new_teacher_email.set()
            await message.reply(
                "Введите новый email",
                reply_markup=types.ReplyKeyboardRemove()
            )

    async def new_teacher_email_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_teacher = data['selected_teacher'] is None
            teacher_name = data['selected_teacher']
        if not is_new_teacher:
            teacher = self.database.get_teacher(teacher_name)
            teacher.email = text
            self.database.update_group(teacher)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=BotBase.none_state_keyboard()
            )
        else:
            async with state.proxy() as data:
                try:
                    self.database.add_teacher(
                        data['new_teacher_name'], text
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

    async def delete_teacher_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == 'Да':
            with state.proxy() as data:
                teacher_name = data['selected_teacher']
            try:
                self.database.delete_teacher(
                    self.database.get_teacher(teacher_name)
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
            lambda message: message.text == BotTeachers.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_teacher_handler,
            state=EditTeachers.select_teacher
        )
        self.dp.register_message_handler(
            self.teacher_activity_handler,
            state=EditTeachers.teacher_activity
        )
        self.dp.register_message_handler(
            self.new_teacher_name_handler,
            state=EditTeachers.new_teacher_name
        )
        self.dp.register_message_handler(
            self.new_teacher_email_handler,
            state=EditTeachers.new_teacher_email
        )
        self.dp.register_message_handler(
            self.delete_teacher_confirm_handler,
            state=EditTeachers.delete_teacher_confirm
        )
