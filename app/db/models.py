# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

from sqlalchemy import Column, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class Volunteer(Base):
    __tablename__ = "volunteers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    about_me = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    volunteer_interests = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    availability = Column(String(255), nullable=True)
    is_active = Column(Integer, default=1)
    volunteer_matches = relationship("VolunteerNeedMatch", back_populates="volunteer", cascade="all, delete-orphan")


class Need(Base):
    __tablename__ = "needs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    required_tasks = Column(Text, nullable=True)
    required_skills = Column(Text, nullable=True)
    num_volunteers_needed = Column(Integer, nullable=False)
    format = Column(Enum("in-person", "virtual", name="need_format"), nullable=False)
    location_details = Column(Text, nullable=True)
    contact_name = Column(String(255), nullable=False)
    contact_email = Column(String(255), nullable=False)
    contact_phone = Column(String(50), nullable=True)
    owner_id = Column(Integer, ForeignKey("volunteers.id"), nullable=False)
    owner = relationship("Volunteer", back_populates=None)
    need_matches = relationship("VolunteerNeedMatch", back_populates="need", cascade="all, delete-orphan")


class VolunteerNeedMatch(Base):
    __tablename__ = "volunteer_need_matches"

    id = Column(Integer, primary_key=True, index=True)
    volunteer_id = Column(Integer, ForeignKey("volunteers.id"), nullable=False)
    need_id = Column(Integer, ForeignKey("needs.id"), nullable=False)
    match_details = Column(Text, nullable=False)
    volunteer = relationship("Volunteer", back_populates="volunteer_matches")
    need = relationship("Need", back_populates="need_matches")
