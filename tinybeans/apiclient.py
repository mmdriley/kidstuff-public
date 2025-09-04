from datetime import datetime
from functools import partial
import os
from typing import cast, Literal

import apischema
import dotenv
import requests

from . import apitypes
from . import websiteconfig


deserialize = partial(apischema.deserialize, additional_properties=True)
serialize = partial(apischema.serialize, exclude_none=True)


dotenv.load_dotenv()


class TinybeansClient:
    session: requests.Session
    journal_id: int

    def __init__(self, username: str, password: str):
        self.session = requests.Session()

        access_token = self._get_access_token(username, password)
        self.session.headers['authorization'] = access_token

    # returns: access token, an opaque string that happens to be GUID-shaped
    def _get_access_token(self, username: str, password: str) -> str:
        r = self.session.post(
            'https://tinybeans.com/api/1/authenticate',
            json={
                'username': username,
                'password': password,

                # provide client ID from webapp
                # if this is absent, we get "Unauthorised Client"
                'clientId': websiteconfig.client_id,
            })
        r.raise_for_status()

        o = deserialize(apitypes.AuthenticateResponse, r.json())
        assert(o.status == 'ok')
        return o.accessToken

    def get_journals(self) -> list[apitypes.Journal]:
        r = self.session.get('https://tinybeans.com/api/1/journals')
        r.raise_for_status()

        o = deserialize(apitypes.ListJournalsResponse, r.json())
        assert(o.status == 'ok')

        return o.journals
    
    def journal(self, journal_ref: str | int | None) -> 'TinybeansJournal':
        def parses_as_int(s: str):
            try:
                int(s)
                return True
            except ValueError:
                return False

        if journal_ref is None:
            journal_ref = os.getenv('TINYBEANS_DEFAULT_JOURNAL', None)

        match journal_ref:
            case None:
                journal_id = self.get_journals()[0].id
            case int(journal_id): pass
            case str(journal_id_str) if parses_as_int(journal_id_str):
                journal_id = int(journal_id_str)
            case str(journal_title):
                for j in self.get_journals():
                    if j.title == journal_title:
                        journal_id = j.id
                        break
                else:  # runs if loop ends normally, i.e. no "break"
                    raise ValueError('no journal with that name')
            
        return TinybeansJournal(self, journal_id)


class TinybeansJournal:
    client: TinybeansClient
    journal_id: int

    def __init__(self, client: TinybeansClient, journal_id: int):
        self.client = client
        self.journal_id = journal_id

    def get_details(self) -> apitypes.Journal:
        r = self.client.session.get(
            f'https://tinybeans.com/api/1/journals/{self.journal_id}')
        r.raise_for_status()

        o = deserialize(apitypes.GetJournalResponse, r.json())
        assert(o.status == 'ok')

        return o.journal

    def get_entries(self, year: int, month: int, day: int | None = None
                    ) -> list[apitypes.EntryWithComments]:
        r = self.client.session.get(
            f'https://tinybeans.com/api/1/journals/{self.journal_id}/entries',
            params={
                'year': year,
                'month': month,
            } | ({} if day is None else {
                'day': day,
            }))
        r.raise_for_status()

        o = deserialize(apitypes.ListEntriesResponse, r.json())
        assert(o.status == 'ok')

        if len(o.entries) > 0 and day is not None:
            entries = o.entries

            # Check we have the right idea for how entries are sorted within a
            # day. At last check, unless there's a pinned entry, the webapp just
            # uses the first entry returned by the server as the day's cover;
            # the server, in turn, manages the sort order to choose the "right"
            # cover. Elsewhere we rely on knowing which picture gets picked, so
            # we have these checks here to surprise us if the order changes.

            def sort_key(e: apitypes.Entry):
                # Entries are sorted by sortOrder ascending, where present,
                # or else by descending timestamp. It's possible for some
                # entries in a day to have sortOrder and others not to.
                return (e.sortOrder if e.sortOrder is not None else -1,
                        -e.timestamp)
            assert(entries == sorted(entries, key=sort_key))

        return o.entries

    # sort orders:
    #   'DD' -- date descending
    #   'DA' -- date ascending
    # the webapp hardwires results_per_page to 72
    def search(self, keywords: str, sort_order: Literal['DD', 'DA']  = 'DD',
               page: int = 1, results_per_page: int = 10
               ) -> list[apitypes.Entry]:

        r = self.client.session.get(
            f'https://tinybeans.com/api/1/journals/{self.journal_id}/search',
            params={
                'term': keywords,
                'sort': sort_order,
                'page': page,
                'length': results_per_page,
            })
        r.raise_for_status()

        o = deserialize(apitypes.SearchResponse, r.json())
        assert(o.status == 'ok')

        if o.entries is None:
            return []
        return o.entries

    # caller needs to upload any photo themselves and set remoteFileName
    def create_entry(self, entry: apitypes.EntryForCreate) -> apitypes.Entry:
        r = self.client.session.post(
            f'https://tinybeans.com/api/1/journals/{self.journal_id}/entries',
            json=serialize(entry))
        r.raise_for_status()

        o = deserialize(apitypes.CreateEntryResponse, r.json())
        assert(o.status == 'ok')

        return o.entry

    # TODO: maybe there should be an underlying update_entry API and this
    # should call it
    def pin_entry(self, entry: apitypes.Entry):
        def id_of(x: apitypes.Child | apitypes.ChildId) -> int:
            match x:
                case apitypes.Child(id=id): return id
                case apitypes.ChildId(childId=childId): return childId

        update_entry = apitypes.EntryForUpdate(
            year=entry.year,
            month=entry.month,
            day=entry.day,

            caption=entry.caption,

            pinnedTimestamp = int(datetime.now().timestamp() * 1000),

            children = [],
        )

        if entry.children is not None:
            update_entry.children = [id_of(c) for c in entry.children]

        r = self.client.session.post(
            f'https://tinybeans.com/api/1/journals/{self.journal_id}'
            f'/entries/{entry.id}',
            json=serialize(update_entry))
        r.raise_for_status()


def default_client():
    username = os.getenv('TINYBEANS_USERNAME')
    password = os.getenv('TINYBEANS_PASSWORD')
    assert username and password, 'set TINYBEANS_USERNAME and TINYBEANS_PASSWORD'

    return TinybeansClient(username, password)
