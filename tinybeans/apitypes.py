from dataclasses import dataclass, field
from typing import Literal


@dataclass
class User:
    id: int

    timestamp: int
    lastUpdatedTimestamp: int

    fullName: str
    firstName: str
    lastName: str

    hasMemoriesAccess: bool


@dataclass
class UserWithEmail(User):
    username: str
    emailAddress: str


# POST https://tinybeans.com/api/1/authenticate
# request body (JSON): username, password, clientId
@dataclass
class AuthenticateResponse:
    status: str
    user: UserWithEmail
    accessToken: str  # usually guid-shaped


@dataclass
class Child:
    id: int

    timestamp: int
    lastUpdatedTimestamp: int

    firstName: str
    lastName: str
    fullName: str

    gender: str
    dob: str
    user: User


@dataclass
class Journal:
    id: int

    timestamp: int

    title: str

    user: User  # owner
    children: list[Child] = field(default_factory=list)


# https://tinybeans.com/api/1/journals
@dataclass
class ListJournalsResponse:
    status: str
    journals: list[Journal]


# https://tinybeans.com/api/1/journals/123
# 123 = journal id
@dataclass
class GetJournalResponse:
    status: str
    journal: Journal


@dataclass
class Comment:
    id: int
    entryId: int

    URL: str

    timestamp: int
    lastUpdatedTimestamp: int

    user: User

    details: str
    repliesCount: int


@dataclass
class ChildId:
    childId: int


@dataclass
class Blobs:
    o: str
    o2: str
    t: str
    s: str
    s2: str
    m: str
    l: str
    p: str


# https://github.com/mmdriley/kidstuff/blob/0e6e75ef8c3568a56cba7c7f4ed133ec892ab0d4/websites/tinybeans/tinybeans-frontend/models/entry.js#L2
@dataclass(kw_only=True)
class Entry:
    id: int
    journalId: int
    userId: int

    URL: str

    timestamp: int
    lastUpdatedTimestamp: int
    pinnedTimestamp: int | None = None

    year: int
    month: int
    day: int

    caption: str

    privateMode: bool
    uuid: str
    clientRef: str | None = None
    type: Literal['TEXT', 'PHOTO']
    blobs: Blobs
    sortOrder: int | None = None

    # when showing *one* entry we get full info
    # when listing entries or searching we just get childId
    # and the field is missing when no children are tagged
    # TODO: reflect this with more overrides of the `Entry` type
    children: list[Child] | list[ChildId] | None = None

    # these are present for videos
    attachmentType: Literal['VIDEO'] | None = None
    attachmentUrl: str | None = None
    attachmentUrl_mp4: str | None = None
    attachmentUrl_webm: str | None = None


@dataclass
class EntryWithComments(Entry):
    totalCommentsCount: int
    comments: list[Comment] = field(default_factory=list)


# https://tinybeans.com/api/1/journals/123/entries
# 123 = journal id
# query params: year, month, day
@dataclass
class ListEntriesResponse:
    status: str
    entries: list[EntryWithComments] = field(default_factory=list)


# https://tinybeans.com/api/1/entries/123/uuid/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
# 123 = entry id
# aaa = entry guid
@dataclass
class GetEntryResponse:
    status: str
    entry: EntryWithComments


# https://tinybeans.com/api/1/journals/123/search
# 123 = journal id
# query params: term, sort, page, length
# - sort: 'DA' (date-ascending) or 'DD' (date-descending)
@dataclass
class SearchResponse:
    status: str
    count: int
    entries: list[Entry] = field(default_factory=list)


# the fields of Entry above populated on create
# TODO: bring this into some hierarchy with Entry?
@dataclass
class EntryForCreate:
    year: int
    month: int
    day: int

    caption: str

    children: list[int] = field(default_factory=list)
    pets: list[int] = field(default_factory=list)

    # Name of uploaded photo to include with this post
    # webapp uses UUIDv4 + extension of uploaded file
    # absent for text-only posts
    remoteFileName: str | None = None

    privateMode: bool | None = None


@dataclass
class CreateEntryResponse:
    status: str
    entry: Entry


# fields of Entry sent for update, see:
# https://github.com/mmdriley/kidstuff/blob/7d9748c324058df145ee3fddec929d2a9fbd0512/websites/tinybeans/tinybeans-frontend/services/tinybeans-backend.js#L251-L265
@dataclass
class EntryForUpdate:
    year: int
    month: int
    day: int
    
    caption: str

    # milliseconds since epoch, see:
    # https://github.com/mmdriley/kidstuff/blob/7d9748c324058df145ee3fddec929d2a9fbd0512/websites/tinybeans/tinybeans-frontend/components/entry-component.js#L427
    pinnedTimestamp: int

    children: list[int]
