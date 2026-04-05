from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class ProfileIn(BaseModel):
    age: int = Field(ge=10, le=120)
    height_cm: float = Field(ge=50, le=300)
    weight_kg: float = Field(ge=20, le=500)
    target_weight_kg: float = Field(ge=20, le=500)
    sex: str = Field(pattern="^(male|female)$")
    activity_level: str = Field(default="moderate", pattern="^(sedentary|light|moderate|active|very_active)$")


class ProfileOut(ProfileIn):
    updated_at: str


class WeightEntry(BaseModel):
    date: str
    weight_kg: float = Field(ge=20, le=500)


class WorkoutIn(BaseModel):
    date: str
    raw_text: str = ""
    duration_minutes: int = Field(ge=0, le=1440)
    intensity: Optional[str] = Field(default=None, pattern="^(low|medium|high)$")
    steps: Optional[int] = Field(default=None, ge=0)


class WorkoutOut(BaseModel):
    id: int
    date: str
    raw_text: Optional[str]
    workout_type: Optional[str]
    duration_minutes: Optional[int]
    intensity: Optional[str]
    steps: Optional[int]
    estimated_calories_burned: Optional[int]
    structured_info: Optional[str]


class MealLogIn(BaseModel):
    date: str
    dishes: str
    second_serving: bool = False
    bread: bool = False
    notes: Optional[str] = None


class MealLogOut(BaseModel):
    id: int
    date: str
    dishes: str
    second_serving: bool
    bread: bool
    notes: Optional[str]
    total_estimated_calories: Optional[int]
    created_at: str


class DishCatalogEntry(BaseModel):
    normalized_name: str
    estimated_calories_per_serving: int
    category: Optional[str] = None
    confidence: str = "estimated"
    notes: Optional[str] = None
