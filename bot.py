from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

from db_requests import DBRequests

from datetime import datetime


class Descriptor:
    def __init__(self, iterator, func=None):
        self.iterator = iterator
        self.data = []
        self.index = -1
        self.dict = {}
        self.func = func if func is not None else (lambda x: x)

    def next(self):
        if self.index + 1 == len(self.data):
            try:
                batch = next(self.iterator)
                batch_to_add = []
                for row in batch:
                    key = self.func(row)
                    batch_to_add.append(key)
                    self.dict[key] = row
                self.data.append(batch_to_add)
            except StopIteration:
                raise RuntimeError("list ends")
        self.index += 1
        return self.data[self.index]

    def __getitem__(self, item):
        if item not in self.dict:
            raise RuntimeError("no key {}".format(item))
        return self.dict[item]

    def get(self):
        if len(self.data) != 0:
            return self.data[self.index]
        else:
            raise RuntimeError("list is empty")

    def prev(self):
        if self.index <= 0:
            raise RuntimeError("self.index <= 0")
        self.index -= 1
        return self.data[self.index]


def batch_generator(iterable, batch_size):
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if len(batch) != 0:
        yield batch


class RegisterForm(StatesGroup):
    nickname = State()
    group = State()


class EditGroups(StatesGroup):
    select_group = State()

    group_activity = State()
    # creates if doesn't exist
    new_group_name = State()
    new_group_email = State()
    new_group_monitor = State()
    delete_group_confirm = State()

    select_group_event = State()
    delete_group_event_confirm = State()
    add_group_event_select = State()


class EditTeachers(StatesGroup):
    select_teacher = State()

    # creates if doesn't exist
    new_teacher_name = State()
    new_teacher_email = State()


class EditEvents(StatesGroup):
    select_event = State()
    event_activity = State()
    new_event_name = State()
    new_event_date = State()
    new_event_is_regular = State()
    new_event_teacher = State()
    delete_event_confirm = State()


class MainMenu(StatesGroup):
    select_activity = State()
    courses = State()
    profile = State()
    feedbacks = State()

    edit_groups = State()
    edit_events = State()
    edit_teachers = State()

    help = State()


class Profile(StatesGroup):
    print_profile = State()

    edit_nickname = State()
    edit_nickname_confirm = State()

    delete_profile_confirm = State()


class Courses(StatesGroup):
    select_course = State()

    select_course_to_enrol = State()
    enrol_course_confirm = State()

    delete_course_confirm = State()


class FeedBack(StatesGroup):
    select_feedback = State()

    feedback_activity = State()

    new_feedback_title = State()
    new_feedback_teacher = State()
    new_feedback_event = State()
    new_feedback_text = State()

    delete_feedback_confirm = State()


class SAIBot:
    def __init__(self, token: str, database: DBRequests, admin_nickname):
        self.token = token
        self.bot = Bot(token=self.token)
        self.storage = MemoryStorage()
        self.dp = Dispatcher(self.bot, storage=self.storage)
        self.database = database
        self.descriptors = {}

        self.admin_nickname = admin_nickname

        self.__register_handlers()

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
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("Курсы")
        markup.add("Профиль")
        markup.add("Отзывы")

        if student.permissions != "user":
            markup.add("Группы")
            markup.add("События")
            markup.add("Учителя")

        markup.add("Помощь")
        await MainMenu.select_activity.set()
        await message.reply("Главное меню", reply_markup=markup)

    def group_selection_keyboard(self, not_in_the_list="Нет в списке"):
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        available_groups = self.database.list_groups()
        for i in range(0, len(available_groups), 4):
            markup.add(
                *available_groups[i:min(i + 4, len(available_groups))]
            )
        markup.add(not_in_the_list)
        return markup

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

    @staticmethod
    def profile_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("/menu")
        markup.add("сменить имя")
        markup.add("сменить группу")
        markup.add("удалить профиль")
        return markup

    @staticmethod
    def select_common_keyboard(descriptor):
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("←", "/menu", "→")
        try:
            for row in descriptor.get():
                print(row)
                markup.add(row)
        except RuntimeError:
            pass
        return markup

    @staticmethod
    def select_feedback_keyboard(descriptor, student):
        markup = SAIBot.select_common_keyboard(descriptor)
        markup.add("Написать новый отзыв")
        markup.add("Показать мои отзывы")
        if student.permissions != "user":
            markup.add("Показать немодерированные отзывы")
        markup.add("Убрать фильтры")
        return markup

    @staticmethod
    def yes_no_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("Да", "Нет")
        return markup

    @staticmethod
    def group_activity_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("/menu")
        markup.add("Сменить имя")
        markup.add("Сменить email")
        markup.add("Сменить старосту")
        markup.add("События группы")
        markup.add("Удалить группу")
        return markup

    @staticmethod
    def event_activity_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("/menu")
        markup.add("Сменить имя")
        markup.add("Сменить дату")
        markup.add("Сменить постоянность")
        markup.add("Сменить преподавателя")
        markup.add("Удалить событие")
        return markup

    async def menu_select_activity_handler(
            self, message: types.Message, state: FSMContext
    ):
        activity = message.text
        telegram_id = str(message.from_user.id)
        student = self.database.get_student(
            telegram_id=telegram_id
        )
        if activity == "Курсы":
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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif activity == "Профиль":
            await Profile.print_profile.set()
            await message.reply(
                ("Ваш профиль:\n"
                 "Имя: {}\n"
                 "Группа: {}\n"
                 "telegram id: {}").format(
                    student.nickname, student.group.name,
                    student.telegram_id
                ),
                reply_markup=SAIBot.profile_keyboard()
            )
        elif activity == "Отзывы":
            await FeedBack.select_feedback.set()
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=True),
                lambda row: row[0].title
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)

        elif activity == "Группы" and student.permissions != 'user':
            await EditGroups.select_group.set()
            markup = self.group_selection_keyboard("Новая группа")
            await message.reply("Группы", reply_markup=markup)
        elif activity == "События" and student.permissions != 'user':
            descriptor = Descriptor(batch_generator(
                self.database.get_event_name_list(), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Новое событие")
            await EditEvents.select_event.set()
            await message.reply("События", reply_markup=markup)
        elif activity == "Учителя" and student.permissions != 'user':
            descriptor = Descriptor(batch_generator(
                self.database.get_teacher_name_list(), 5
            ))
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditTeachers.select_teacher.set()
            await message.reply("Учителя", reply_markup=markup)
        elif activity == "Помощь":
            await state.finish()
            await message.reply(
                "Используйте /help", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply(
                "Неверное действие. Попробуйте еще раз"
            )

    async def select_course_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        student = self.database.get_student(
            telegram_id=str(message.from_user.id)
        )
        telegram_id = student.telegram_id
        descriptor = self.descriptors[telegram_id]
        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        elif text == "ОК":
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Записаться на другой курс")
            await message.reply("Ваши курсы", reply_markup=markup)
        elif text == "Отменить запись":
            markup = SAIBot.yes_no_keyboard()
            await Courses.delete_course_confirm.set()
            await message.reply("Вы уверены?", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data["event_to_delete"] = event
                markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True, selective=True
                )
                try:
                    self.database.get_student(
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
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("Новый курс", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data["enrol_course"] = event
                markup = SAIBot.yes_no_keyboard()
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
                        data["event_to_delete"]
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
                        data["enrol_course"].name
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
            markup = SAIBot.yes_no_keyboard()
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
            markup = SAIBot.yes_no_keyboard()
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

    async def select_feedback_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        student = self.database.get_student(
            telegram_id=str(message.from_user.id)
        )
        telegram_id = student.telegram_id
        descriptor = self.descriptors[telegram_id]
        if text == "←":
            try:
                descriptor.prev()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Написать новый отзыв":
            await FeedBack.new_feedback_title.set()
            await message.reply(
                "Введите заголовок", reply_markup=types.ReplyKeyboardRemove()
            )
        elif text == "Убрать фильтры":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=True),
                lambda row: row[0].title
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Показать мои отзывы":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, student=student),
                lambda row: row[0].title
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        elif text == "Показать немодерированные отзывы" and \
                student.permissions != "user":
            descriptor = Descriptor(
                self.database.feedbacks_generator(5, is_approved=False),
                lambda row: row[0].title
            )
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await message.reply("Отзывы", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    generator_row = descriptor[text]
                    feedback = generator_row[0]
                    data["selected_feedback"] = feedback.title
                markup = types.ReplyKeyboardMarkup(
                    resize_keyboard=True, selective=True
                )
                try:
                    self.database.get_student(
                        telegram_id=telegram_id
                    )
                    self.database.get_feedback(data["selected_feedback"])
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
                    get_exist_attr(generator_row[3], "nickname"),
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
            feedback = self.database.get_feedback(data["selected_feedback"])

        if (feedback.student_id == student.id or student.permissions != 'user')\
                and text == "Удалить":
            await FeedBack.delete_feedback_confirm.set()
            markup = SAIBot.yes_no_keyboard()
            await message.reply(
                "Вы уверены?", reply_markup=markup
            )
        elif student.permissions != 'user' and not feedback.is_approved and \
                text == "Одобрить":
            try:
                self.database.approve_feedback(feedback)
            except RuntimeError:
                pass
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
            await FeedBack.select_feedback.set()
            await message.reply("Отзывы", reply_markup=markup)
        elif feedback.is_approved and text == "Проголосовать":
            feedback.votes = feedback.votes + 1
            try:
                self.database.update_feedback(feedback)
                await state.finish()
                await message.reply(
                    "Успех", reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
        elif text == "ОК":
            markup = SAIBot.select_feedback_keyboard(descriptor, student)
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
                        "Удалено", reply_markup=types.ReplyKeyboardRemove()
                    )
                except RuntimeError:
                    await message.reply(
                        "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                    )
            else:
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

    async def new_feedback_title_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await FeedBack.new_feedback_event.set()
            await message.reply("Мероприятия", reply_markup=markup)

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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Мероприятия", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Преподаватели", reply_markup=markup)
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
                markup = SAIBot.select_common_keyboard(descriptor)
                markup.add("Пропустить")
                await message.reply("Преподаватели", reply_markup=markup)
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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Мероприятия", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Пропустить")
            await message.reply("Мероприятия", reply_markup=markup)
        elif text == 'Пропустить':
            async with state.proxy() as data:
                data["teacher"] = None
            await FeedBack.new_feedback_text.set()
            await message.reply(
                "Введите текст отзыва",
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            try:
                teacher = self.database.get_teacher(text)
                async with state.proxy() as data:
                    data["teacher"] = teacher.name
                await FeedBack.new_feedback_text.set()
                await message.reply(
                    "Введите текст отзыва",
                    reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await message.reply("Неверная команда")

    async def new_feedback_text_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
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
                    data['title'], text, **kwargs
                )
                success = True
            except RuntimeError:
                success = False
            await state.finish()
            await message.reply(
                "Успех" if success else "Ошибка",
                reply_markup=types.ReplyKeyboardRemove()
            )

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
                markup = SAIBot.group_activity_keyboard()
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
                "Ошибка", reply_markup=types.ReplyKeyboardRemove()
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
                "Удалить группу?", SAIBot.yes_no_keyboard()
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
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
                return
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await message.reply("События группы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
                return
            telegram_id = str(message.from_user.id)
            self.descriptors[telegram_id] = descriptor
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("События", reply_markup=markup)
        else:
            try:
                async with state.proxy() as data:
                    event = self.database.get_event(text)
                    data['selected_event'] = event.name
                await EditGroups.delete_group_event_confirm.set()
                await message.reply(
                    ("Имя: {}\n"
                     "Дата: {}\n"
                     "Регулярное?: {}\n"
                     "Преподаватель: {}\n"
                     "УДАЛИТЬ?").format(
                        event.name, event.date, event.is_regular,
                        event.teacher.name),
                    reply_markup=SAIBot.yes_no_keyboard()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=types.ReplyKeyboardRemove()
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
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("События группы", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
                    reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=types.ReplyKeyboardRemove()
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
                reply_markup=types.ReplyKeyboardRemove()
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
                    reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка",
                    reply_markup=types.ReplyKeyboardRemove()
                )
        elif text == 'Нет':
            await state.finish()
            await message.reply(
                "ОК",
                reply_markup=types.ReplyKeyboardRemove()
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
            group = None
            if not is_new_group:
                group = self.database.get_group(data['selected_group'])
        if text in self.database.list_groups():
            await message.reply("Имя {} занято. Введите другое".format(text))
        elif not is_new_group:
            group.name = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=types.ReplyKeyboardRemove()
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
            group = None
            if not is_new_group:
                group = self.database.get_group(data['selected_group'])
        if not is_new_group:
            group.email = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=types.ReplyKeyboardRemove()
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
            group = None
            if not is_new_group:
                group = self.database.get_group(data['selected_group'])
        if not is_new_group:
            group.monitor = text
            self.database.update_group(group)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=types.ReplyKeyboardRemove()
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
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                await message.reply(
                    "Ошибка",
                    reply_markup=types.ReplyKeyboardRemove()
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
                    "Успех", reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
        elif text == 'Нет':
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неизвестная команда")

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
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Новое событие")
            await message.reply("События", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
                async with state.proxy() as data:
                    data['selected_event'] = event.name
                await EditEvents.event_activity.set()
                await message.reply(
                    ("Событие: {}\n"
                     "Дата: {}\n"
                     "Постоянное? {}\n"
                     "Преподаватель: {}").format(
                        event.name, event.date,
                        event.is_regular, event.teacher.name
                    ),
                    reply_markup=SAIBot.event_activity_keyboard()
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
                reply_markup=types.ReplyKeyboardRemove()
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
                reply_markup=SAIBot.yes_no_keyboard()
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
            markup = SAIBot.select_common_keyboard(descriptor)
            await EditEvents.new_event_teacher.set()
            await message.reply("Новый учитель", reply_markup=markup)
        elif text == "Удалить событие":
            await EditEvents.delete_event_confirm.set()
            await message.reply(
                "Вы уверены?",
                reply_markup=SAIBot.yes_no_keyboard()
            )
        else:
            await message.reply("Неверная команда")

    async def new_event_name_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None
            event = None
            if not is_new_event:
                event = self.database.get_event(data['selected_event'])
        if text in self.database.get_event_name_list():
            await message.reply("Имя {} занято. Введите другое".format(text))
        elif not is_new_event:
            event.name = text
            self.database.update_event(event)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=types.ReplyKeyboardRemove()
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
                    reply_markup=types.ReplyKeyboardRemove()
                )
            else:
                await EditEvents.new_event_is_regular.set()
                await message.reply(
                    "Событие регулярное?",
                    reply_markup=SAIBot.yes_no_keyboard()
                )
        except ValueError:
            await message.reply("Попробуйте снова")

    async def new_event_is_regular_handler(
            self, message: types.Message, state: FSMContext
    ):
        text = message.text
        async with state.proxy() as data:
            is_new_event = data['selected_event'] is None
            event = None
            if not is_new_event:
                event = self.database.get_event(data['selected_event'])
        if text not in ['Да', 'Нет']:
            await message.reply("Неверная команда")
        elif not is_new_event:
            event.is_regular = text == 'Да'
            self.database.update_event(event)
            await state.finish()
            await message.reply(
                "Успех",
                reply_markup=types.ReplyKeyboardRemove()
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
            markup = SAIBot.select_common_keyboard(descriptor)
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
            markup = SAIBot.select_common_keyboard(descriptor)
            await message.reply("Новый учитель", reply_markup=markup)
        elif text == "→":
            try:
                descriptor.next()
            except RuntimeError:
                pass
            markup = SAIBot.select_common_keyboard(descriptor)
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
                            reply_markup=types.ReplyKeyboardRemove()
                        )
                    else:
                        await message.reply(
                            "Ошибка",
                            reply_markup=types.ReplyKeyboardRemove()
                        )
                else:
                    async with state.proxy() as data:
                        event = self.database.get_event(
                            data["selected_event"]
                        )
                    event.teacher = teacher
                    self.database.update_event(event)
                    await state.finish()
                    await message.reply(
                        "Успех",
                        reply_markup=types.ReplyKeyboardRemove()
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
                    "Успех", reply_markup=types.ReplyKeyboardRemove()
                )
            except RuntimeError:
                await state.finish()
                await message.reply(
                    "Ошибка", reply_markup=types.ReplyKeyboardRemove()
                )
        elif text == 'Нет':
            await state.finish()
            await message.reply(
                "Отмена", reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            await message.reply("Неизвестная команда")

    async def select_teacher_handler(
            self, message: types.Message, state: FSMContext
    ):
        pass

    def __register_handlers(self):
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
            self.menu_select_activity_handler, state=MainMenu.select_activity
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

    def start_polling(self):
        executor.start_polling(self.dp, skip_updates=True)
