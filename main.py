from db_requests import DBRequests
from sqlalchemy import create_engine
from bot import SAIBot
from datetime import datetime
import logging
from os import environ


def debug_output(db):
    logging.debug("\n\nTABLES:")
    session = db.session
    logging.debug("group:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.group).all()]))
    logging.debug("event:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.event).all()]))
    logging.debug("group_event:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.group_event).all()]))
    logging.debug("student:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.student).all()]))
    logging.debug("pearson_event:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.pearson_event).all()]))
    logging.debug("teacher:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.teacher).all()]))
    logging.debug("feedback:")
    logging.debug("\n" + "\n".join([str(row) for row in session.query(db.feedback).all()]))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    engine = create_engine('sqlite:///sai.db', echo=False)
    db = DBRequests(engine)
    # debug_output(db)
    db.add_group("332", "astromsu@", "Nastya")
    db.add_group("201", "2astromsu@", "Nastya2")
    db.add_teacher("Ivanov", "example@email.com")
    db.add_event("event1", datetime(2021, 3, 1), True, "Ivanov")
    db.add_event("event2", datetime(2021, 3, 1), True, "Ivanov")
    db.add_group_event("332", "event1")
    db.add_group_event("332", "event2")
    db.add_event("event3", datetime(2021, 3, 1), True, "Ivanov")
    db.add_student("ADMIN", environ["ADMIN_ID"], "332", "admin")

    # db.add_student("levochka", "dffddf", "332", "all")
    # student = db.get_student(nickname="levochka")
    bot = SAIBot(environ["API_TOKEN"], db, environ["ADMIN_TELEGRAM"])
    bot.start_polling()
    # db.add_feedback(student, "tllktlrkl", "ererer")
    # gen = db.feedbacks_generator(5, is_approved=False)
    # feed1 = next(gen)[0][0]
    # feed2 = feed1
    # print(feed1)
    # db.delete_feedback(feed1)
    # db.delete_student(student)
    # gen2 = db.feedbacks_generator(5, is_approved=False)
    # feee3 = next(gen2)[0][0]
