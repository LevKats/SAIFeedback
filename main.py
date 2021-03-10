from db_requests import DBRequests
from sqlalchemy import create_engine

from bot_core import BotCore
from bot_courses import BotCourses
from bot_profile import BotProfile
from bot_feedback import BotFeedback
from bot_groups import BotGroups
from bot_events import BotEvents
from bot_teachers import BotTeachers
from bot_moderators import BotModerators

import logging
from os import environ

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    engine = create_engine('sqlite:///sai.db', echo=False)
    db = DBRequests(engine)
    # debug_output(db)
    try:
        db.add_group("DEFAULT", "email@example.com", "ADMIN")
    except RuntimeError:
        pass
    if "ADMIN" not in db.list_students_names():
        db.add_student("ADMIN", environ["ADMIN_ID"], "DEFAULT", "admin")

    bot = BotCore(
        environ["API_TOKEN"], db, environ["ADMIN_TELEGRAM"],
        BotProfile, BotCourses, BotFeedback,
        BotGroups, BotEvents, BotTeachers,
        BotModerators
    )
    bot.start_polling()
