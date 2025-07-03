from pydantic import BaseModel, EmailStr
from typing import Optional, Literal

# --- Volunteer Schemas ---
class VolunteerBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    about_me: Optional[str] = None
    skills: Optional[str] = None
    volunteer_interests: Optional[str] = None
    location: Optional[str] = None
    availability: Optional[str] = None

class VolunteerCreate(VolunteerBase):
    pass

class Volunteer(VolunteerBase):
    id: int

    class Config:
        from_attributes = True

# --- Need Schemas ---
class NeedBase(BaseModel):
    title: str
    description: str
    required_tasks: Optional[str] = None
    required_skills: Optional[str] = None
    num_volunteers_needed: int
    format: Literal["in-person", "virtual"]
    location_details: Optional[str] = None
    contact_name: str
    contact_email: EmailStr
    contact_phone: Optional[str] = None

class NeedCreate(NeedBase):
    pass

class Need(NeedBase):
    id: int

    class Config:
        from_attributes = True