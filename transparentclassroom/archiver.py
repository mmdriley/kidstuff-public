#!/usr/bin/env python3

import argparse
import asyncio
from collections import Counter
import datetime
import functools
import json
import os
import pathlib
import sqlite3
import sys
from typing import Iterator, List
import urllib.parse

import apischema
from apischema import serialize
import dotenv
import requests

from . import apitypes
from .download import DownloadItem, download_urls
from . import apiclient as TC
from .postfunctions import all_class_post_confidence


SCRIPT_START_TIME = datetime.datetime.now(
    datetime.timezone.utc).isoformat(timespec='milliseconds')


# Use a sentinel a little past the "minimum" date so that callers can still do
# date math on it, e.g. subtract 7 days.
LOW_DATE_SENTINEL = '0100-01-01'


deserialize = functools.partial(apischema.deserialize,
                                additional_properties=True)


# TODO: announcements have photos too


# Return the most recent created_at date of a post in the database.
# If no posts exist, returns a sentinel that compares less than any real date.
def newest_post_created_at(db: sqlite3.Connection) -> str:
    r = db.execute("""
        SELECT MAX(DATE(JSON_EXTRACT(post_json, '$.created_at'))) AS newest_post_date
        FROM Posts
        """).fetchone()
    return r['newest_post_date'] or LOW_DATE_SENTINEL


def trim_url(url: str) -> str:
    parsed_url = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    for p in ['X-Amz-Algorithm',
              'X-Amz-Credential',
              'X-Amz-Date',
              'X-Amz-Expires',
              'X-Amz-SignedHeaders',
              'X-Amz-Signature']:
        if p in query_params:
            del query_params[p]
    return urllib.parse.urlunparse(parsed_url._replace(
        query=urllib.parse.urlencode(query_params, doseq=True)))


def retrieve_school_posts(db: sqlite3.Connection, not_before_date: str = LOW_DATE_SENTINEL):
    for p in TC.default_client().all_child_posts():
        if p.date < not_before_date:
            break

        # TODO: is it better to trim up these URLs or remove them entirely?
        # either way the URL is useless for *downloading*.
        # 
        # TODO 2: actually the stripped URLs work for downloading as of this
        # writing.
        for f in ['photo_url',
                  'medium_photo_url',
                  'large_photo_url',
                  'original_photo_url']:
            s = getattr(p, f)
            if s is not None:
                setattr(p, f, trim_url(s))

        db.execute("""
            INSERT INTO Posts (post_json, first_seen, last_seen)
            VALUES (:post_json, :now, :now)
            ON CONFLICT(post_json) DO UPDATE
            SET last_seen = :now
            """, {
            # sort keys for canonical representation
            'post_json': json.dumps(serialize(p, exclude_none=True), sort_keys=True),
            'now': SCRIPT_START_TIME,
        })

    r = db.execute("""
            SELECT SUM(first_seen = :now) AS new_this_run
            FROM Posts
            """, {
        'now': SCRIPT_START_TIME,
    }).fetchone()
    print(f'{r["new_this_run"]} posts added')
    print()


def all_posts(db: sqlite3.Connection) -> Iterator[apitypes.Post]:
    # TODO: handle potential duplicate versions by ID
    c = db.execute("""
        SELECT post_json
        FROM Posts
        ORDER BY
            JSON_EXTRACT(post_json, '$.date') DESC,
            JSON_EXTRACT(post_json, '$.created_at') DESC
    """)

    for r in c:
        yield deserialize(apitypes.Post, json.loads(r['post_json']))


async def download_post_photos(posts: Iterator[apitypes.Post], target_path: pathlib.Path):
    download_items = []

    for p in posts:
        # skip text-only posts
        if not p.photo_url or not p.original_photo_url:
            continue

        # TODO: is `id` unique enough here or should I include namespacing, e.g. photo{id}
        # actually, will probably solve this by downloading into different *directories*

        download_items += [
            DownloadItem(f'{p.id}', p.photo_url),
            DownloadItem(f'{p.id}_original', p.original_photo_url),
        ]

    await download_urls(download_items, target_path)


def download_announcements(s: requests.Session, school_id: int, base_path: pathlib.Path):
    announcements = []
    params = {}

    while True:
        r = s.get(
            f'{TC.API_BASE}/s/{school_id}/frontend/announcements.json', params=params)
        r.raise_for_status()

        announcements += r.json()['data']

        # When we run out of pages, the last response is:
        # {"data":[],"pagination":{"next":null}}
        next = r.json()['pagination']['next']
        if next is None:
            break
        print(next)
        params['page'] = next

    with base_path.joinpath('announcements.json').open('w') as f:
        json.dump(announcements, f, indent=2)


def parse_announcements(announcements):
    for a in announcements:
        assert a['type'] == 'Announcement'

        assert 'data' in a
        d = a['data']

        assert 'id' in d
        assert 'createdAt' in d
        assert 'title' in d
        assert 'body' in d
        assert 'attachments' in d

        assert 'author' in d
        assert 'id' in d['author']
        assert 'name' in d['author']

        assert 'subject' in d
        assert 'id' in d['subject']
        assert 'type' in d['subject']
        assert 'name' in d['subject']
        assert d['subject']['type'] in ['Classroom', 'School']

        for att in d['attachments']:
            assert att['type'] == 'Attachment'
            assert 'data' in att
            att_d = att['data']
            assert 'name' in att_d
            assert 'id' in att_d
            assert 'url' in att_d
            assert 'size' in att_d

    print(f'{len(announcements)} announcements')


def db_init(path: pathlib.Path) -> sqlite3.Connection:
    db_conn = sqlite3.connect(path, isolation_level='IMMEDIATE')
    db_conn.row_factory = sqlite3.Row

    db_conn.executescript("""
        CREATE TABLE IF NOT EXISTS Posts (
            post_json TEXT NOT NULL UNIQUE,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS Announcements (
            announcement_json NOT NULL UNIQUE,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
    """)

    return db_conn


async def main(args):
    dotenv.load_dotenv()

    base_path = pathlib.Path('TransparentClassroomArchive').resolve()
    base_path.mkdir(exist_ok=True)

    db = db_init(base_path.joinpath('posts.sqlite'))

    # Announcements!
    # tc = tc_client()
    # download_announcements(tc.session, tc.school_id(), base_path)

    # with base_path.joinpath('announcements.json').open('r') as f:
    #     announcements = json.load(f)
    #     parse_announcements(announcements)
    # sys.exit(1)

    if args.no_update_posts:
        print('Not retrieving posts')
    else:
        tc = TC.default_client()

        # Download posts. Assume we already have all posts >7d earlier than the
        # newest `created_at` value we've previously seen.
        #
        # We set the threshold using `created_at` instead of `date` to avoid any
        # potential problem with future-dated posts. Post authors set `date`;
        # the server sets `created_at`. We assume the server always uses a
        # reasonable value, though we never compare it to this machine's clock
        # (which is why we shy away from using `last_seen`).
        old_post_margin = datetime.timedelta(days=7)
        posts_not_before = datetime.date.fromisoformat(
            newest_post_created_at(db)) - old_post_margin
        retrieve_school_posts(db, not_before_date=str(posts_not_before))
        db.commit()

    # await download_post_photos(all_posts(db), base_path.joinpath('photos'))


    lls = []
    for p in all_posts(db):
        c = all_class_post_confidence(p.html)
        # if c == 9 and p['classroom_id'] == 1141:
        #     print(json.dumps(p, indent=2))
        lls.append((p.classroom_id, c))
        # if c == 8:
        #     print(p['html'])
    
    for k, v in Counter(lls).items():
        print(f'{k[0]},{k[1]},{v}')

    db.commit()
    db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-update-posts', action='store_true')
    asyncio.run(main(parser.parse_args()))
