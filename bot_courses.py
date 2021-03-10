from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import Courses
from bot_utils import Descriptor
from bot_utils import batch_generator
from bot_utils import MainMenu
from db_requests import DBRequests


class BotCourses(BotBase):
    permission = "user"
    func_name = "Курсы"

    def __init__(self, database: DBRequests, descriptors: dict, dp):
        super().__init__(database, descriptors, dp)
        self.register_handlers()

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        activity = message.text
        telegram_id = str(message.from_user.id)
        if activity == BotCourses.func_name:
            await Courses.select_course.set()
            try:
                student = self.database.get_student(
                    telegram_id=telegram_id
                )
            except RuntimeError:
                return
            descriptor = Descriptor(batch_generator(
                self.database.get_student_events(student), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)

    async def select_course_handler(
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
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif text == "Записаться на другой курс":
            await Courses.select_course_to_enrol.set()
            try:
                student = self.database.get_student(
                    telegram_id=telegram_id
                )
            except RuntimeError:
                return
            descriptor = Descriptor(batch_generator(
                self.database.get_available_events_for_student(student),
                5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        elif text == "ОК":
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif text == "Отменить запись":
            markup = BotBase.yes_no_keyboard()
            await Courses.delete_course_confirm.set()
            await message.reply("Вы уверены?", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data["event_to_delete"] = event.name
                markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True, selective=True
                )
                try:
                    student = self.database.get_student(
                        telegram_id=telegram_id
                    )
                    self.database.get_event(event.name)
                except RuntimeError:
                    return
                if not self.database.is_group_event(student, event):
                    markup.add("Отменить запись")
                markup.add("ОК")
                await message.reply(("Название: {}\n"
                                     "Дата первого занятия: {}\n"
                                     "Является регулярным? {}\n"
                                     "Преподаватель {}\n").format(
                    event.name, event.date, event.is_regular,
                    event.teacher.name), reply_markup=markup)
            except RuntimeError:
                await message.reply("Нет такого курса")

    async def select_course_to_enrol_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        # student = self.database.get_student(
        #     telegram_id=str(message.from_user.id)
        # )
        # telegram_id = message.from_user.id
        descriptor = self.descriptors[str(message.from_user.id)]
        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data["enrol_course"] = event.name
                markup = BotBase.yes_no_keyboard()
                await Courses.enrol_course_confirm.set()
                await message.reply("Вы уверены?", reply_markup=markup)
            except RuntimeError:
                await message.reply("Нет такого курса")

    async def delete_course_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "Да":
            async with state.proxy() as data:
                try:
                    self.database.delete_pearson_event(
                        self.database.get_student(
                            telegram_id=str(message.from_user.id)
                        ),
                        self.database.get_event(data["event_to_delete"])
                    )
                    await state.finish()
                    await message.reply(
                        "Удаление", reply_markup=types.ReplyKeyboardRemove()
                    )
                except RuntimeError:
                    await state.finish()
                    await message.reply(
                        "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                    )
        elif text == "Нет":
            await state.finish()
            await message.reply(
                "Отмена удаления", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неверный вариент")

    async def enrol_course_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text == "Да":
            async with state.proxy() as data:
                try:
                    self.database.add_pearson_event(
                        self.database.get_student(
                            telegram_id=str(message.from_user.id)
                        ).telegram_id,
                        data["enrol_course"]
                    )
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
                "Отмена записи", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неверный вариент")

    def register_handlers(self):
        self.dp.register_message_handler(
            self.menu_select_activity_handler,
            lambda message: message.text == BotCourses.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_course_handler, state=Courses.select_course
        )
        self.dp.register_message_handler(
            self.select_course_to_enrol_handler,
            state=Courses.select_course_to_enrol
        )
        self.dp.register_message_handler(
            self.delete_course_confirm_handler,
            state=Courses.delete_course_confirm
        )
        self.dp.register_message_handler(
            self.enrol_course_confirm_handler,
            state=Courses.enrol_course_confirm
        )
