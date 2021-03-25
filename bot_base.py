from db_requests import DBRequests

from aiogram import types

from abc import abstractmethod


class BotBase(object):
    def __init__(self, database: DBRequests, descriptors: dict, dp, bot):
        self.database = database
        self.descriptors = descriptors
        self.dp = dp
        self.bot = bot

    @abstractmethod
    def register_handlers(self):
        pass

    @staticmethod
    def state_description(lst, index_now):
        rows = ["", "Прогресс:"]
        for i, state in enumerate(lst):
            if i == index_now:
                rows.append('\u27a1' + ' ' + state)
            elif i < index_now:
                rows.append('\u2705' + " " + state)
            else:
                rows.append('\u274c' + " " + state)
        return "\n".join(rows)

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
        markup = BotBase.select_common_keyboard(descriptor)
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
    def none_state_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("/menu", "/help")
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

    @staticmethod
    def teacher_activity_keyboard():
        markup = types.ReplyKeyboardMarkup(
            resize_keyboard=True, selective=True
        )
        markup.add("/menu")
        markup.add("Сменить имя")
        markup.add("Сменить email")
        markup.add("Удалить преподавателя")
        return markup
