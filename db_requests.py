from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import or_
import datetime
import logging


def debug_output(db):
    logging.debug("\n\nTABLES:")
    session = db.session
    logging.debug("group:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.group).all()]
    ))
    logging.debug("event:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.event).all()]
    ))
    logging.debug("group_event:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.group_event).all()]
    ))
    logging.debug("student:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.student).all()]
    ))
    logging.debug("pearson_event:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.pearson_event).all()]
    ))
    logging.debug("teacher:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.teacher).all()]
    ))
    logging.debug("feedback:")
    logging.debug("\n" + "\n".join(
        [str(row) for row in session.query(db.feedback).all()]
    ))


class DBRequests:
    def __init__(self, engine):
        self.engine = engine
        base = declarative_base()

        class Teacher(base):
            __tablename__ = "teachers"

            id = Column(Integer, primary_key=True)
            name = Column(String)
            email = Column(String)

            def __str__(self):
                return "Teacher(id={}, name={}, email={})".format(
                    self.id, self.name, self.email
                )

        class Event(base):
            __tablename__ = 'events'

            id = Column(Integer, primary_key=True)
            name = Column(String)
            date = Column(DateTime)
            is_regular = Column(Boolean)
            teacher_id = Column(Integer, ForeignKey("teachers.id"))

            teacher = relationship("Teacher", back_populates="events")

            def __str__(self):
                return (
                    "Event(id={}, name={}, date={},"
                    " is_regular={}, teacher_id={})")\
                    .format(
                    self.id, self.name, self.date, self.is_regular,
                    self.teacher_id
                )

        class Group(base):
            __tablename__ = 'groups'

            id = Column(Integer, primary_key=True)
            name = Column(String)
            email = Column(String)
            monitor = Column(String)

            def __str__(self):
                return (
                    "Group(id={}, name={}, email={},"
                    " monitor={})")\
                    .format(
                    self.id, self.name, self.email, self.monitor,
                )

        class GroupEvent(base):
            __tablename__ = "group_events"

            id = Column(Integer, primary_key=True)
            group_id = Column(Integer, ForeignKey('groups.id'))
            event_id = Column(Integer, ForeignKey('events.id'))

            group = relationship("Group", back_populates="group_events")
            event = relationship("Event", back_populates="group_events")

            def __str__(self):
                return (
                    "GroupEvent(id={}, group_id={}, event_id={},"
                    ")")\
                    .format(
                    self.id, self.group_id, self.event_id,
                )

        class Student(base):
            __tablename__ = "students"

            id = Column(Integer, primary_key=True)
            nickname = Column(String)
            telegram_id = Column(String)
            group_id = Column(Integer, ForeignKey('groups.id'))
            permissions = Column(String)

            group = relationship("Group", back_populates="students")

            def __str__(self):
                return (
                    "Student(id={}, nickname={}, telegram_id={},"
                    " group_id={}, permission={})")\
                    .format(
                    self.id, self.nickname, self.telegram_id, self.group_id,
                    self.permissions
                )

        class PearsonEvent(base):
            __tablename__ = "pearson_events"

            id = Column(Integer, primary_key=True)
            student_id = Column(Integer, ForeignKey('students.id'))
            event_id = Column(Integer, ForeignKey('events.id'))

            student = relationship("Student", back_populates="pearson_events")
            event = relationship("Event", back_populates="pearson_events")

            def __str__(self):
                return (
                    "PearsonEvent(id={}, student_id={}, event_id={},"
                    ")")\
                    .format(
                    self.id, self.student_id, self.event_id
                )

        class Feedback(base):
            __tablename__ = "feedbacks"

            id = Column(Integer, primary_key=True)
            title = Column(String)
            student_id = Column(Integer, ForeignKey('students.id'))
            text = Column(String)
            date = Column(DateTime)
            is_approved = Column(Boolean)
            anonymously = Column(Boolean)
            votes = Column(Integer)

            student = relationship("Student", back_populates="student_feedbacks")

            def __str__(self):
                return (
                    "Feedback(id={}, title={}, student_id={},,"
                    " text={}, date={}, is_approved={},"
                    " anonymously = {}, votes = {})") \
                    .format(
                    self.id, self.title, self.student_id,
                    self.text, self.date, self.is_approved,
                    self.anonymously, self.votes
                )

        class FeedbackEvent(base):
            __tablename__ = "feedback_events"

            id = Column(Integer, primary_key=True)
            feedback_id = Column(Integer, ForeignKey('feedbacks.id'))
            event_id = Column(Integer, ForeignKey('events.id'))

            feedback = relationship("Feedback", back_populates="feedback_events")
            event = relationship("Event", back_populates="event_feedbacks")

            def __str__(self):
                return (
                    "FeedbackEvent(id={}, feedback_id={},,"
                    " event_id={})") \
                    .format(
                    self.id, self.feedback_id, self.event_id
                )

        class FeedbackTeacher(base):
            __tablename__ = "feedback_teachers"

            id = Column(Integer, primary_key=True)
            feedback_id = Column(Integer, ForeignKey('feedbacks.id'))
            teacher_id = Column(Integer, ForeignKey('teachers.id'))

            feedback = relationship("Feedback", back_populates="feedback_teachers")
            teacher = relationship("Teacher", back_populates="teacher_feedbacks")

            def __str__(self):
                return (
                    "FeedbackTeacher(id={}, feedback_id={},,"
                    " event_id={})") \
                    .format(
                    self.id, self.feedback_id, self.teacher_id
                )

        self.group = Group
        self.event = Event
        self.group_event = GroupEvent
        self.student = Student
        self.pearson_event = PearsonEvent
        self.teacher = Teacher
        self.feedback = Feedback
        self.feedback_event = FeedbackEvent
        self.feedback_teacher = FeedbackTeacher

        self.group.group_events = relationship(
            "GroupEvent", order_by=GroupEvent.id, back_populates="group",
            cascade="all, delete, delete-orphan"
        )
        self.group.students = relationship(
            "Student", order_by=Student.id, back_populates="group",
            cascade="all, delete, delete-orphan"
        )
        self.event.group_events = relationship(
            "GroupEvent", order_by=GroupEvent.id, back_populates="event",
            cascade="all, delete, delete-orphan"
        )
        self.event.pearson_events = relationship(
            "PearsonEvent", order_by=PearsonEvent.id, back_populates="event",
            cascade="all, delete, delete-orphan"
        )
        self.event.event_feedbacks = relationship(
            "FeedbackEvent", order_by=FeedbackEvent.id, back_populates="event",
            cascade="all, delete, delete-orphan"
        )
        self.student.pearson_events = relationship(
            "PearsonEvent", order_by=PearsonEvent.id,
            back_populates="student",
            cascade="all, delete, delete-orphan"
        )
        self.student.student_feedbacks = relationship(
            "Feedback", order_by=Feedback.id,
            back_populates="student",
            cascade="all, delete, delete-orphan"
        )
        self.teacher.events = relationship(
            "Event", order_by=Event.id, back_populates="teacher",
            cascade="all, delete, delete-orphan"
        )
        self.teacher.teacher_feedbacks = relationship(
            "FeedbackTeacher", order_by=FeedbackTeacher.id,
            back_populates="teacher",
            cascade="all, delete, delete-orphan"
        )
        self.feedback.feedback_events = relationship(
            "FeedbackEvent", order_by=FeedbackEvent.id,
            back_populates="feedback",
            cascade="all, delete, delete-orphan"
        )
        self.feedback.feedback_teachers = relationship(
            "FeedbackTeacher", order_by=FeedbackTeacher.id,
            back_populates="feedback",
            cascade="all, delete, delete-orphan"
        )
        base.metadata.create_all(engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        # self.session.expire_on_commit = False

        try:
            self.get_group("DEFAULT")
            logging.info("group DEFAULT exists")
        except RuntimeError:
            logging.info("Adding group DEFAULT")
            self.add_group("DEFAULT", "example@example.com", "developer")

    def add_group(self, name, email, monitor):
        if self.session.query(self.group).filter(
                self.group.name == name
        ).first() is not None:
            raise RuntimeError("group {} exists".format(name))

        rows = [
            self.group(
                name=name, email=email, monitor=monitor
            )
        ]
        self.session.add_all(rows)
        self.session.commit()

    def get_group(self, name):
        group = self.session.query(self.group).filter(
                self.group.name == name
        ).first()
        if group is None:
            raise RuntimeError("group {} doesn't exists".format(name))
        return group

    def delete_group(self, group):
        self.session.delete(group)
        self.session.commit()

    def update_group(self, new_group):
        self.session.commit()

    def list_groups(self):
        result = [
            row.name for row in self.session.query(self.group).all()
        ]
        result.remove("DEFAULT")
        return result

    def add_teacher(self, name, email):
        if self.session.query(self.teacher).filter(
                self.teacher.name == name
        ).first() is not None:
            raise RuntimeError("teacher {} exists".format(name))

        rows = [
            self.teacher(
                name=name,
                email=email
            )
        ]
        self.session.add_all(rows)
        self.session.commit()

    def get_teacher(self, name):
        teacher = self.session.query(self.teacher).filter(
            self.teacher.name == name
        ).first()
        if teacher is None:
            raise RuntimeError("teacher {} doesn't exists".format(name))
        return teacher

    def delete_teacher(self, teacher):
        self.session.delete(teacher)
        self.session.commit()

    def update_teacher(self, new_teacher):
        self.session.commit()

    def get_teacher_name_list(self):
        return [
            row.name for row in self.session.query(self.teacher).all()
        ]

    def add_event(self, name, date, is_regular, teacher_name):
        if self.session.query(self.event).filter(
                self.event.name == name
        ).first() is not None:
            raise RuntimeError("event {} exists".format(name))

        teacher = self.session.query(self.teacher).filter(
            self.teacher.name == teacher_name
        ).first()

        if teacher is None:
            raise RuntimeError(
                "teacher {} doesn't exists".format(teacher_name)
            )

        teacher.events.append(self.event(
            name=name, teacher_id=teacher.id, date=date,
            is_regular=is_regular
        ))
        self.session.commit()

    def get_event(self, name):
        event = self.session.query(self.event).filter(
                self.event.name == name
        ).first()
        if event is None:
            raise RuntimeError("event {} doesn't exists".format(name))
        return event

    def get_event_name_list(self):
        return [row.name for row in self.session.query(self.event).all()]

    def delete_event(self, event):
        self.session.delete(event)
        self.session.commit()

    def update_event(self, new_event):
        self.session.commit()

    def add_student(self, nickname, telegram_id, group_name, permissions):
        if self.session.query(self.student).filter(
                self.student.nickname == nickname
        ).first() is not None:
            raise RuntimeError("student {} exists".format(nickname))
        if self.session.query(self.student).filter(
                self.student.telegram_id == telegram_id
        ).first() is not None:
            raise RuntimeError("telegram user {} exists".format(telegram_id))

        group = self.session.query(self.group).filter(
            self.group.name == group_name
        ).first()

        if group is None:
            raise RuntimeError("group {} doesn't exists".format(group_name))

        group.students.append(self.student(
            nickname=nickname, group_id=group.id,
            telegram_id=telegram_id, permissions=permissions
        ))
        self.session.commit()

    def get_student(self, **kwargs):
        if "nickname" in kwargs:
            nickname = kwargs["nickname"]
            student = self.session.query(self.student).filter(
                    self.student.nickname == nickname
            ).first()
            if student is None:
                raise RuntimeError(
                    "student {} doesn't exists".format(nickname)
                )
            return student
        if "telegram_id" in kwargs:
            telegram_id = kwargs["telegram_id"]
            student = self.session.query(self.student).filter(
                    self.student.telegram_id == telegram_id
            ).first()
            if student is None:
                raise RuntimeError(
                    "telegram user {} doesn't exists".format(telegram_id)
                )
            return student

    def delete_student(self, student):
        self.session.delete(student)
        self.session.commit()

    def update_student(self, new_student):
        self.session.commit()

    def list_students_names(self, **kwargs):
        query = self.session.query(self.student)
        if "permissions" in kwargs:
            query = query.filter(
                self.student.permissions == kwargs["permissions"]
            )
        return [
            row.nickname for row in query.all()
        ]

    def add_pearson_event(self, student_telegram_id, event_name):
        student = self.session.query(self.student).filter(
            self.student.telegram_id == student_telegram_id
        ).first()
        event = self.session.query(self.event).filter(
            self.event.name == event_name
        ).first()

        if student is None:
            raise RuntimeError(
                "student {} doesn't exists".format(student_telegram_id)
            )
        if event is None:
            raise RuntimeError("event {} doesn't exists".format(event_name))

        if self.session.query(self.pearson_event).filter(
                self.pearson_event.student_id == student.id,
                self.pearson_event.event_id == event.id
        ).first() is not None:
            raise RuntimeError(
                "pearson event ({}, {}) exists".format(
                    student_telegram_id, event_name
                )
            )

        pe = self.pearson_event()
        pe.event = event
        student.pearson_events.append(pe)
        self.session.commit()

    def delete_pearson_event(self, student, event):
        pe = self.session.query(self.pearson_event).filter(
                self.pearson_event.student_id == student.id,
                self.pearson_event.event_id == event.id
        ).first()
        if pe is None:
            raise RuntimeError(
                "pearson event ({}, {}) doesn't exists".format(
                    student.telegram_id, event.name
                )
            )
        self.session.delete(pe)
        self.session.commit()

    def add_group_event(self, group_name, event_name):
        group = self.session.query(self.group).filter(
            self.group.name == group_name
        ).first()
        event = self.session.query(self.event).filter(
            self.event.name == event_name
        ).first()

        if group is None:
            raise RuntimeError("group {} doesn't exists".format(group_name))
        if event is None:
            raise RuntimeError("event {} doesn't exists".format(event_name))

        if self.session.query(self.group_event).filter(
                self.group_event.group_id == group.id,
                self.group_event.event_id == event.id
        ).first() is not None:
            raise RuntimeError(
                "group event ({}, {}) exists".format(
                    group_name, event_name
                )
            )

        pe = self.group_event()
        pe.event = event
        group.group_events.append(pe)
        self.session.commit()

    def delete_group_event(self, group, event):
        ge = self.session.query(self.group_event).filter(
                self.group_event.group_id == group.id,
                self.group_event.event_id == event.id
        ).first()
        if ge is None:
            raise RuntimeError(
                "group event ({}, {}) doesn't exists".format(
                    group.name, event.name
                )
            )
        self.session.delete(ge)
        self.session.commit()

    def is_group_event(self, student, event):
        return self.session.query(self.group_event).filter(
            self.group_event.group_id == student.group.id,
            self.group_event.event_id == event.id
        ).first() is not None

    def group_event_list(self, group):
        return [
            row.event.name for row in self.session.query(
                self.group_event
            ).filter(self.group_event.group_id == group.id)
        ]

    def get_student_events(self, student):
        query = self.session.query(self.event).outerjoin(
            self.pearson_event, self.pearson_event.event_id == self.event.id
        ).outerjoin(
            self.group_event, self.group_event.event_id == self.event.id
        ).filter(
            or_(
                student.group.id == self.group_event.group_id,
                student.id == self.pearson_event.student_id
            )
        )
        # print([row.name for row in query.all()])
        return [row.name for row in query.all()]

    def get_available_events_for_student(self, student):
        se = self.get_student_events(student)
        for event in self.session.query(self.event):
            if event.name not in se:
                yield event.name

    def get_feedback(self, title):
        feedback = self.session.query(self.feedback).filter(
            self.feedback.title == title
        ).first()
        if feedback is None:
            raise RuntimeError("title {} doesn't exists".format(title))
        return feedback

    def add_feedback(self, student, title, text, anonymously, **kwargs):
        if self.session.query(self.feedback).filter(
                self.feedback.title == title
        ).first() is not None:
            raise RuntimeError("title {} exists".format(title))
        feedback = self.feedback(
            student_id=student.id,
            title=title,
            text=text,
            date=datetime.datetime.now(),
            is_approved=False,
            anonymously=anonymously,
            votes=0
        )
        if "teacher" in kwargs:
            feedback_teacher = self.feedback_teacher()
            feedback_teacher.teacher = kwargs['teacher']
            feedback.feedback_teachers.append(feedback_teacher)
        if 'event' in kwargs:
            feedback_event = self.feedback_event()
            feedback_event.event = kwargs['event']
            feedback.feedback_events.append(feedback_event)
        self.session.add(feedback)
        self.session.commit()

    def delete_feedback(self, feedback):
        self.session.delete(feedback)
        self.session.commit()

    def approve_feedback(self, feedback):
        feedback.is_approved = True
        self.session.commit()

    def update_feedback(self, new_feedback):
        self.session.commit()

    def feedbacks_generator(self, batch_num, **kwargs):
        batch = []
        query = self.session.query(
            self.feedback, self.event, self.teacher, self.student
        ).join(self.student, self.feedback.student_id == self.student.id)
        query = query.outerjoin(
            self.feedback_teacher,
            self.feedback.id == self.feedback_teacher.feedback_id
        )
        query = query.outerjoin(
            self.teacher, self.feedback_teacher.teacher_id == self.teacher.id
        )
        query = query.outerjoin(
            self.feedback_event,
            self.feedback.id == self.feedback_event.feedback_id
        )
        query = query.outerjoin(
            self.event, self.feedback_event.event_id == self.event.id
        )
        if "student" in kwargs:
            query = query.filter(
                self.feedback.student_id == kwargs["student"].id
            )
        if "is_approved" in kwargs:
            query = query.filter(
                self.feedback.is_approved == kwargs["is_approved"]
            )
        for row in query.all():
            batch.append(row)
            if len(batch) == batch_num:
                yield batch
                batch = []
        if len(batch):
            yield batch
