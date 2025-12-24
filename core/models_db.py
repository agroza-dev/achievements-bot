from sqlalchemy import ARRAY, Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Reaction(Base):
    __tablename__ = 'reactions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(Integer, nullable=False)
    message_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    language_code = Column(String(10), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    new_reactions = Column(ARRAY(String), nullable=True)  # Store emojis as array
    old_reactions = Column(ARRAY(String), nullable=True)  # Store emojis as array
    action = Column(String(20), nullable=False)  # 'added', 'removed', 'updated', 'unchanged', 'unknown'
