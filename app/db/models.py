from sqlalchemy import Column, Integer, String, Text, Enum
from app.db.database import Base

class Volunteer(Base):
    __tablename__ = "volunteers" 

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(50), nullable=True)
    about_me = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    volunteer_interests = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    availability = Column(String(255), nullable=True)

class Need(Base):
    __tablename__ = "needs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    required_tasks = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    num_volunteers_needed = Column(Integer, nullable=False)
    format = Column(Enum('in-person', 'virtual', name='need_format'), nullable=False)
    location_details = Column(Text, nullable=True)
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50), nullable=True)