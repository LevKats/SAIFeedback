from aiogram.dispatcher.filters.state import State, StatesGroup


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
    teacher_activity = State()
    # creates if doesn't exist
    new_teacher_name = State()
    new_teacher_email = State()
    delete_teacher_confirm = State()


class EditEvents(StatesGroup):
    select_event = State()
    event_activity = State()
    new_event_name = State()
    new_event_date = State()
    new_event_is_regular = State()
    new_event_teacher = State()
    delete_event_confirm = State()


class EditModerators(StatesGroup):
    select_moderator = State()
    moderator_activity = State()
    new_moderator_nickname = State()
    delete_moderator_confirm = State()


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
    new_feedback_anonymously = State()

    enter_message_to_author = State()

    delete_feedback_confirm = State()
