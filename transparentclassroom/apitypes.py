from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from apischema import validator

# Response from `authenticate.json`
@dataclass
class UserInfo:
    id: int

    school_id: int

    first_name: str
    last_name: str
    email: str

    api_token: str


# One child from `classroom/nnn/children.json`
@dataclass(kw_only=True)
class Child:
    id: int

    current_classroom_ids: list[int]
    parent_ids: list[int]

    first_name: str
    last_name: str
    birth_date: str
    gender: str

    program: str
    notes: str | None = None

    profile_photo: str  # url


# One post from `posts.json`
@dataclass
class Post:
    id: int
    created_at: str = field()

    classroom_id: int

    author: str
    date: str = field()

    html: str
    normalized_text: str

    # these are missing for text-only posts
    photo_url: str | None = None
    medium_photo_url: str | None = None
    large_photo_url: str | None = None
    original_photo_url: str | None = None

    @property
    def date_as_datetime(self) -> datetime:
        return datetime.strptime(self.date, '%Y-%m-%d')

    @property
    def created_at_as_datetime(self) -> datetime:
        # ISO 8601
        return datetime.strptime(self.created_at, '%Y-%m-%dT%H:%M:%S.%f%z')

    @validator(date)
    def check_date_format(self):
        self.date_as_datetime

    @validator(created_at)
    def check_created_at_format(self):
        self.created_at_as_datetime
