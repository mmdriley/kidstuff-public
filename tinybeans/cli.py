from dataclasses import dataclass
from datetime import datetime
import pprint
from typing import Protocol

import click
from colors import bold, underline

from . import apiclient
from . import apitypes


@click.group()
def tb():
    """Tinybeans"""
    pass


@tb.command()
def list_journals():
    c = apiclient.default_client()
    journals = c.get_journals()

    for j in journals:
        pprint.pprint(j)


@tb.command()
@click.option('--journal', type=str, default=None)
def print_journal_details(journal: str | None):
    c = apiclient.default_client()
    j = c.journal(journal).get_details()

    class Nameable(Protocol):
        fullName: str
        firstName: str
        lastName: str

    def format_name(a: Nameable):
        return f'{a.fullName} ({a.lastName}, {a.firstName})'

    print(bold(j.title))
    print(f'owned by {format_name(j.user)}')
    print('Children:')
    for c in j.children:
        print(f'- {format_name(c)} [{underline(c.id)}]')
        print(f'  {c.gender}, dob {c.dob}')
    else:
        print(f'  No children')


@dataclass
class Interval:
    year: int
    month: int
    day: int | None


def parse_interval(interval: str) -> Interval | None:
    try:
        d = datetime.strptime(interval, '%Y-%m-%d')
        return Interval(d.year, d.month, d.day)
    except ValueError:
        pass

    try:
        d = datetime.strptime(interval, '%Y-%m')
        return Interval(d.year, d.month, None)
    except ValueError:
        pass

    return None


def short_caption(caption: str) -> str:
    return caption.replace('\n', '')[:50]


def print_cover(entries: list[apitypes.EntryWithComments]):
    if len(entries) == 0:
        print(f'cover photo: NONE (no entries)')
        return

    # is there a pinned entry?
    max_pinned_timestamp = -1
    pin_index: int | None = None
    for i, e in enumerate(entries):
        if e.pinnedTimestamp is None:
            continue
        if e.pinnedTimestamp > max_pinned_timestamp:
            pin_index = i
            max_pinned_timestamp = e.pinnedTimestamp
    
    if pin_index is not None:
        pinned = entries[pin_index]
        print(f'cover entry: index {pin_index} ({pinned.id})')
        print(f'\t{short_caption(pinned.caption)}')
        print(f'cover entry reason: pinned')
        return
    
    # what did the server return first?
    print(f'cover entry: index 0 ({entries[0].id})')
    print(f'\t{short_caption(entries[0].caption)}')
    print(f'cover entry reason: server sort')


@tb.command()
@click.option('--journal', type=str, default=None)
@click.argument('interval')
def get_entries(journal: str | None, interval: str):
    ymd = parse_interval(interval)
    if ymd is None:
        print('expected YYYY-MM or YYYY-MM-DD')
        return

    c = apiclient.default_client()
    j = c.journal(journal)

    entries = j.get_entries(ymd.year, ymd.month, ymd.day)

    if len(entries) == 0:
        print('no entries in that interval')
        return

    pprint.pprint(entries)

    if ymd.day is not None:
        print_cover(entries)


@tb.command()
@click.option('--journal', type=str, default=None)
@click.argument('keywords')
def search(journal: str | None, keywords: str):
    c = apiclient.default_client()
    r = c.journal(journal).search(keywords)

    for e in r:
        print(e.caption)


if __name__ == '__main__':
    tb()
