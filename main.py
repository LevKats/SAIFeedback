from db_requests import DBRequests
from sqlalchemy import create_engine

from bot_core import BotCore
from bot_courses import BotCourses
from bot_profile import BotProfile
from bot_feedback import BotFeedback
from bot_groups import BotGroups
from bot_events import BotEvents
from bot_teachers import BotTeachers

import logging
from os import environ

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    engine = create_engine('sqlite:///sai.db', echo=False)
    db = DBRequests(engine)
    # debug_output(db)
    if "332" not in db.list_groups():
        db.add_group("332", "astromsu@", "Nastya")
    if "ADMIN" not in db.list_students_names():
        db.add_student("ADMIN", environ["ADMIN_ID"], "332", "admin")

    bot = BotCore(
        environ["API_TOKEN"], db, environ["ADMIN_TELEGRAM"],
        BotProfile, BotCourses, BotFeedback,
        BotGroups, BotEvents, BotTeachers
    )
    bot.start_polling()
