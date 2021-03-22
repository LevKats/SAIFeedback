from aiogram import types
from aiogram.dispatcher import FSMContext

from bot_base import BotBase
from bot_utils import MainMenu
from bot_utils import FeedBack
from bot_utils import Descriptor
from bot_utils import batch_generator
from db_requests import DBRequests


class BotFeedback(BotBase):
    permission = "user"
    func_name = "Отзывы"

    MAX_TITLE_SYMBOLS = 50

    def __init__(self, database: DBRequests, descriptors: dict, dp):
        self.states_list = [
            "заголовок",
            "событие (опционально)",
            "учитель (опционально)",
            "текст",
            "анонимно?"
        ]
        super().__init__(database, descriptors, dp)
        self.register_handlers()

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        def approved_emoji(is_approved):
            return '\u274c' if not is_approved else '\u2705'

        activity = message.text
        telegram_id = str(message.from_user.id)
        student = self.database.get_student(
            telegram_id=telegram_id
        )
        if activity == BotFeedback.func_name:
            await FeedBack.select_feedback.set()
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=True),
                lambda row: " ".join([
                    approved_emoji(row[0].is_approved),
                    row[0].title
                ])
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)

    async def select_feedback_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        student = self.database.get_student(
            telegram_id=str(message.from_user.id)
        )
        telegram_id = student.telegram_id
        descriptor = self.descriptors[telegram_id]

        def approved_emoji(is_approved):
            return '\u274c' if not is_approved else '\u2705'

        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Написать новый отзыв":
            await FeedBack.new_feedback_title.set()
            await message.reply(
                "Введите заголовок\n" + BotBase.state_description(self.states_list, 0),
                reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Убрать фильтры":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=True),
                lambda row: " ".join([
                    approved_emoji(row[0].is_approved),
                    row[0].title
                ])
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Показать мои отзывы":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, student=student),
                lambda row: " ".join([
                    approved_emoji(row[0].is_approved),
                    row[0].title
                ])
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Показать немодерированные отзывы" and \
                student.permissions != "user":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=False),
                lambda row: " ".join([
                    approved_emoji(row[0].is_approved),
                    row[0].title
                ])
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    generator_row = descriptor[text]
                    feedback = generator_row[0]
                    data["selected_feedback"] = feedback.title
                    feedback_name = data["selected_feedback"]
                markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True, selective=True
                )
                try:
                    self.database.get_student(
                        telegram_id=telegram_id
                    )
                    self.database.get_feedback(feedback_name)
                except RuntimeError:
                    return
                if feedback.student_id == student.id or\
                        student.permissions != 'user':
                    markup.add("Удалить")
                if student.permissions != 'user' and not feedback.is_approved:
                    markup.add("Одобрить")
                if feedback.is_approved:
                    markup.add("Проголосовать")
                markup.add("ОК")

                def get_exist_attr(obj, attr):
                    return getattr(obj, attr, None)

                await FeedBack.feedback_activity.set()
                await message.reply(("Заголовок: \n{}\n"
                                     "Дата: {}\n"
                                     "Автор: {}\n"
                                     "На предмет {}\n"
                                     "На Преподавателя {}\n"
                                     "Текст: \n{}\n"
                                     "Голосов: {}\n"
                                     "Проверено модератором: {}").format(
                    feedback.title, feedback.date,
                    get_exist_attr(generator_row[3], "nickname")
                    if not feedback.anonymously else "Скрыто",
                    get_exist_attr(generator_row[1], "name"),
                    get_exist_attr(generator_row[2], "name"),
                    feedback.text, feedback.votes, feedback.is_approved
                ), reply_markup=markup)
            except RuntimeError:
                await message.reply("Нет такого отзыва")

    async def feedback_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        student = self.database.get_student(
            telegram_id=str(message.from_user.id)
        )
        telegram_id = student.telegram_id
        descriptor = self.descriptors[telegram_id]

        async with state.proxy() as data:
            feedback_name = data["selected_feedback"]

        feedback = self.database.get_feedback(feedback_name)

        if (feedback.student_id == student.id or student.permissions != 'user')\
                and text == "Удалить":
            await FeedBack.delete_feedback_confirm.set()
            markup = BotBase.yes_no_keyboard()
            await message.reply(
                "Вы уверены?", reply_markup=markup
            )
        elif student.permissions != 'user' and not feedback.is_approved and \
                text == "Одобрить":
            try:
                self.database.approve_feedback(feedback)
            except RuntimeError:
                pass
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await FeedBack.select_feedback.set()
            await message.reply("Отзывы", reply_markup=markup)
        elif feedback.is_approved and text == "Проголосовать":
            feedback.votes = feedback.votes + 1
            try:
                self.database.update_feedback(feedback)
                await state.finish()
                await message.reply(
                    "Успех", reply_markup=BotBase.none_state_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=BotBase.none_state_keyboard()
                )
        elif text == "ОК":
            markup = BotBase.select_feedback_keyboard(descriptor, student)
            await FeedBack.select_feedback.set()
            await message.reply("Отзывы", reply_markup=markup)
        else:
            await message.reply("Неверная команда")

    async def delete_feedback_confirm_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        student = self.database.get_student(
            telegram_id=str(message.from_user.id)
        )
        async with state.proxy() as data:
            feedback = self.database.get_feedback(data["selected_feedback"])
            print(feedback)
        if text == "Да":
            await state.finish()
            if feedback.student_id == student.id or \
                    student.permissions != 'user':
                try:
                    # it's detached somehow...
                    # TODO find solution
                    self.database.delete_feedback(
                        self.database.get_feedback(feedback.title)
                    )
                    await message.reply(
                        "Удалено", reply_markup=BotBase.none_state_keyboard()
                    )
                except RuntimeError:
                    await message.reply(
                        "Ошибка", reply_markup=BotBase.none_state_keyboard()
                    )
            else:
                await message.reply(
                    "Ошибка", reply_markup=BotBase.none_state_keyboard()
                )
        elif text == "Нет":
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=BotBase.none_state_keyboard()
            )
        else:
            await message.reply("Неверная команда")

    async def new_feedback_title_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if len(text) > BotFeedback.MAX_TITLE_SYMBOLS:
            await message.reply(
                ("Превышено максимальное количество"
                 " символов в заголовке - {}/{}."
                 "Попробуйте снова").format(
                    len(text), BotFeedback.MAX_TITLE_SYMBOLS
                ))
            return
        try:
            student = self.database.get_student(
                telegram_id=str(message.from_user.id)
            )
        except RuntimeError:
            await state.finish()
            await message.reply("Ошибка")
            return
        try:
            self.database.get_feedback(text)
            await message.reply("Введите другой заголовок. Этот используется")
        except RuntimeError:
            descriptor = Descriptor(
                batch_generator(self.database.get_student_events(student), 5),
            )
            async with state.proxy() as data:
                data["student"] = student.nickname
                data["title"] = text
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await FeedBack.new_feedback_event.set()
            await message.reply(
                "Мероприятия\n" + BotBase.state_description(self.states_list, 1),
                reply_markup=markup
            )

    async def new_feedback_event_handler(
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
            markup.add("Пропустить")
            await message.reply("Мероприятия", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Мероприятия", reply_markup=markup)
        elif text == 'Пропустить':
            async with state.proxy() as data:
                data["event"] = None
            await FeedBack.new_feedback_teacher.set()
            descriptor = Descriptor(
                batch_generator(self.database.get_teacher_name_list(), 5),
            )
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply(
                "Преподаватели\n" + BotBase.state_description(self.states_list, 2),
                reply_markup=markup
            )
        else:
            try:
                event = self.database.get_event(text)
                async with state.proxy() as data:
                    data["event"] = event.name
                await FeedBack.new_feedback_teacher.set()
                descriptor = Descriptor(
                    batch_generator(self.database.get_teacher_name_list(), 5),
                )
                telegram_id = str(message.from_user.id)
                self.descriptors[telegram_id] = descriptor
                try:
                    descriptor.next()
                except RuntimeError:
                    pass
                markup = BotBase.select_common_keyboard(descriptor)
                markup.add("Пропустить")
                await message.reply(
                    "Преподаватели\n" + BotBase.state_description(self.states_list, 2),
                    reply_markup=markup
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def new_feedback_teacher_handler(
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
            markup.add("Пропустить")
            await message.reply("Преподаватели", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = BotBase.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Преподаватели", reply_markup=markup)
        elif text == 'Пропустить':
            async with state.proxy() as data:
                data["teacher"] = None
            await FeedBack.new_feedback_text.set()
            await message.reply(
                "Введите текст отзыва\n" + BotBase.state_description(self.states_list, 3),
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                async with state.proxy() as data:
                    teacher = self.database.get_teacher(text)
                    data["teacher"] = teacher.name
                await FeedBack.new_feedback_text.set()
                await message.reply(
                    "Введите текст отзыва\n" + BotBase.state_description(self.states_list, 3),
                    reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def new_feedback_text_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            data['text'] = text
            await FeedBack.new_feedback_anonymously.set()
            await message.reply(
                "Сделать анонимным?\n" + BotBase.state_description(self.states_list, 4),
                reply_markup=BotBase.yes_no_keyboard()
            )

    async def new_feedback_anonymously_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        if text not in ['Да', 'Нет']:
            await message.reply('Неверная команда')
        else:
            anonymously = text == 'Да'
            async with state.proxy() as data:
                try:
                    kwargs = {}
                    if data['event'] is not None:
                        kwargs['event'] = self.database.get_event(data['event'])
                    if data['teacher'] is not None:
                        kwargs['teacher'] = self.database.get_teacher(
                            data['teacher']
                        )
                    self.database.add_feedback(
                        self.database.get_student(nickname=data['student']),
                        data['title'], data['text'], anonymously, **kwargs
                    )
                    success = True
                except RuntimeError:
                    success = False
                await state.finish()
                await message.reply(
                    "Успех" if success else "Ошибка",
                    reply_markup=BotBase.none_state_keyboard()
                )

    def register_handlers(self):
        self.dp.register_message_handler(
            self.menu_select_activity_handler,
            lambda message: message.text == BotFeedback.func_name,
            state=MainMenu.select_activity,
        )

        self.dp.register_message_handler(
            self.select_feedback_handler,
            state=FeedBack.select_feedback
        )
        self.dp.register_message_handler(
            self.feedback_activity_handler,
            state=FeedBack.feedback_activity
        )
        self.dp.register_message_handler(
            self.delete_feedback_confirm_handler,
            state=FeedBack.delete_feedback_confirm
        )
        self.dp.register_message_handler(
            self.new_feedback_title_handler,
            state=FeedBack.new_feedback_title
        )
        self.dp.register_message_handler(
            self.new_feedback_teacher_handler,
            state=FeedBack.new_feedback_teacher
        )
        self.dp.register_message_handler(
            self.new_feedback_event_handler,
            state=FeedBack.new_feedback_event
        )
        self.dp.register_message_handler(
            self.new_feedback_text_handler,
            state=FeedBack.new_feedback_text
        )
        self.dp.register_message_handler(
            self.new_feedback_anonymously_handler,
            state=FeedBack.new_feedback_anonymously
        )
