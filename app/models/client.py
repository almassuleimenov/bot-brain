from sqlalchemy import Column, Integer, BigInteger, String, Boolean, Text
from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True)
    name = Column(String, nullable=True)
    budget = Column(String, nullable=True)
    is_vip = Column(Boolean, default=False)
    context = Column(Text, default="")
