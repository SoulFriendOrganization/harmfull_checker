from sqlalchemy import Column, String, Integer, SmallInteger, Boolean, Date, DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from database.connection import Base, engine

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    age = Column(SmallInteger, nullable=False)

class UserAuth(Base):
    __tablename__ = "user_auths"
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

class Moods(Base):
    __tablename__ = "moods"
    id = Column(SmallInteger, primary_key=True)
    name = Column(String, nullable=False)

class DailyMood(Base):
    __tablename__ = "daily_moods"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    date = Column(Date, nullable=False, default=func.current_date)
    mood_level = Column(SmallInteger, ForeignKey('moods.id'))
    notes = Column(String)
    created_at = Column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint('user_id', 'date'),)

class Quiz(Base):
    __tablename__ = "quizzes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    title = Column(String(255), nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=func.now())

class Question(Base):
    __tablename__ = "questions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey('quizzes.id', ondelete='CASCADE'))
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)  # e.g., 'multiple_choice', 'true_false'
    possible_answers = Column(JSONB, nullable=False)
    correct_answer = Column(JSONB, nullable=False)

class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    quiz_id = Column(UUID(as_uuid=True), ForeignKey('quizzes.id', ondelete='CASCADE'))
    attempted_at = Column(DateTime, default=func.now())
    expired_at = Column(DateTime, server_default=func.now() + text("interval '20 minutes'"))
    is_completed = Column(Boolean, default=False)
    score = Column(Integer)
    points_earned = Column(Integer)

class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id = Column(UUID(as_uuid=True), ForeignKey('quiz_attempts.id', ondelete='CASCADE'))
    question_id = Column(UUID(as_uuid=True), ForeignKey('questions.id', ondelete='CASCADE'))
    user_answer = Column(JSONB)
    is_correct = Column(Boolean)

class DailyScore(Base):
    __tablename__ = "daily_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    date = Column(Date, nullable=False)
    score = Column(Integer, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'date'),)

class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    user_preferences = Column(JSONB)
    

class UserCollection(Base):
    __tablename__ = "user_collections"
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True)
    score = Column(Integer, nullable=False)
    point_earned = Column(Integer, nullable=False)
    user_condition_summary = Column(JSONB, nullable=False)
    num_quiz_attempt = Column(Integer, default=0)

Base.metadata.create_all(engine)