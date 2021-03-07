# import aiogram.utils.markdown as md
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
# from aiogram.dispatcher.filters import Text
from aiogram.dispatcher.filters.state import State, StatesGroup
# from aiogram.types import ParseMode
from aiogram.utils import executor

from db_requests import DBRequests

# from functools import partial


class Descriptor:
    def __init__(self, iterator):
        self.iterator = iterator
        self.data = []
        self.index = -1

    def next(self):
        if self.index + 1 == len(self.data):
            try:
                self.data.append(next(self.iterator))
            except StopIteration:
                raise RuntimeError("list ends")
        self.index += 1
        return self.data[self.index]

    def prev(self):
        self.index -= 1
        return self.data[self.index]


class RegisterForm(StatesGroup):
    nickname = State()
    group = State()


class EditGroups(StatesGroup):
    select_group = State()

    # creates if doesn't exist
    new_group_name = State()
    new_group_email = State()
    new_group_monitor = State()


class EditTeachers(StatesGroup):
    select_teacher = State()

    # creates if doesn't exist
    new_teacher_name = State()
    new_teacher_email = State()


class EditEvents(StatesGroup):
    select_event = State()
    new_group_name = State()
    new_group_date = State()
    new_group_is_regular = State()
    new_group_teacher = State()


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

    edit_group = State()
    edit_group_confirm = State()

    delete_profile = State()
    delete_profile_confirm = State()


class Courses(StatesGroup):
    select_course = State()

    select_course_to_enrol = State
    enrol_course_confirm = State()

    delete_course_confirm = State


class FeedBack(StatesGroup):
    select_feedback = State()
    feedback_id = State()
    is_ok = State()
    activity = State()

    write_feedback = State()
    new_feedback_title = State()
    new_feedback_type = State()
    new_feedback_teacher = State()
    new_feedback_event = State()
    new_feedback_text = State()
    write_feedback_confirm = State()

    approve = State()
    delete_feedback = State()
    vote = State()


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
                # await MainMenu.select_activity.set()

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
        return markup

    @staticmethod
    def select_common_keyboard(descriptor):
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("←", "/menu", "→")
        for row in descriptor.next():
            markup.add(row)
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
            descriptor = Descriptor(iter(
                self.database.get_student_events(student)
            ))
            self.descriptors[telegram_id] = descriptor
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
                    student.nickname, self.database.get_group(
                        student.group_id
                    ), student.telegram_id
                ),
                reply_markup=SAIBot.profile_keyboard()
            )
        elif activity == "Отзывы":
            await FeedBack.select_feedback.set()
            descriptor = Descriptor(
                iter([
                    row[0].title for row in
                    self.database.feedbacks_generator(5)
                ])
            )
            self.descriptors[telegram_id] = descriptor
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Написать новый отзыв")
            markup.add("Показать мои отзывы")
            if student.permissions != "user":
                markup.add("Показать немодерированные отзывы")
            await message.reply("Отзывы", reply_markup=markup)

        elif activity == "Группы" and student.permissions != 'user':
            await EditGroups.select_group.set()
            markup = self.group_selection_keyboard("Новая группа")
            await message.reply("Группы", reply_markup=markup)
        elif activity == "События" and student.permissions != 'user':
            descriptor = Descriptor(iter(self.database.get_event_name_list()))
            self.descriptors[telegram_id] = descriptor
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Новое событие")
            await EditEvents.select_event.set()
            await message.reply("События", reply_markup=markup)
        elif activity == "Учителя" and student.permissions != 'user':
            descriptor = Descriptor(iter(self.database.get_teacher_name_list()))
            self.descriptors[telegram_id] = descriptor
            markup = SAIBot.select_common_keyboard(descriptor)
            markup.add("Добавить")
            await EditTeachers.select_teacher.set()
            await message.reply("Учителя", reply_markup=markup)
        elif activity == "Помощь":
            await state.finish()
            await message.reply("Используйте /help")
        else:
            await message.reply(
                "Неверное действие. Попробуйте еще раз"
            )

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

    def start_polling(self):
        executor.start_polling(self.dp, skip_updates=True)
