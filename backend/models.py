from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    api_key = Column(String)
    api_secret = Column(String)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    symbol = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime)
    type = Column(String)  # buy/sell