from dataclasses import dataclass
from typing import Optional
from datetime import date

@dataclass
class CreatePatientDTO:
    full_name: str
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class PatientDTO:
    id: str
    full_name: str
    birth_date: Optional[date]
    gender: Optional[str]
    diagnosis: Optional[str]
    is_active: bool
