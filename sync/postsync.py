from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import secrets
import shutil
import tempfile

import requests

from htmlfunctions import text_from_html
from tinybeans.apiclient import TinybeansJournal
from tinybeans.upload_picture import upload_picture_file
import tinybeans.apitypes as tbtypes
from transparentclassroom.apiclient import TransparentClassroomClient
import transparentclassroom.apitypes as tctypes
import transparentclassroom.postfunctions as tcposts
from urlfunctions import url_suffix


@dataclass
class MatchingChild:
    first_name: str
    last_name: str

    tc_id: int
    tb_id: int


IMPORT_SESSION_ID = secrets.token_hex(3)


def url_for_tinybeans_entry(p: tbtypes.Entry) -> str:
    # URL field is for API use, not for browsing
    return f'https://tinybeans.com/app/#/main/entries/{p.id}/{p.uuid}'


def find_matching_children(tc: TransparentClassroomClient,
                           tb: TinybeansJournal) -> list[MatchingChild]:
    tc_children = tc.my_children()
    tb_children = tb.get_details().children

    matches = []
    for tcc in tc_children:
        for tbb in tb_children:
            # if this turns out to be too exacting, we could look at DOB
            if tbb.firstName == tcc.first_name and tbb.lastName == tcc.last_name:
                matches.append(MatchingChild(
                    first_name=tbb.firstName,
                    last_name=tbb.lastName,
                    tc_id=tcc.id,
                    tb_id=tbb.id))

    return matches


def copy_one_post(tc: TransparentClassroomClient, tb: TinybeansJournal,
                  matching_children: list[MatchingChild],
                  tc_post_or_id: tctypes.Post | int):
    match tc_post_or_id:
        case int(tc_post_id): pass
        case tctypes.Post(id=tc_post_id): pass

    # skip posts already sync'd
    existing_posts = tb.search(f'post.{tc_post_id}')
    match existing_posts:
        case [existing_tb_post]:
            print(f'SKIPPING {tc_post_id}, already posted:')
            print(f'  {url_for_tinybeans_entry(existing_tb_post)}')
            return

    # assign tc_post
    match tc_post_or_id:
        case tctypes.Post() as tc_post: pass
        case int():
            match tc.posts_by_id([tc_post_id]):
                case [tc_post]: pass
                case _: raise KeyError(f'post {tc_post_id} not found')

    # skip posts without photos
    if tc_post.photo_url is None:
        print(f'SKIPPING {tc_post_id} with no picture')
        return

    # skip class photo posts
    class_photo_score = tcposts.all_class_post_confidence(tc_post.html)
    if class_photo_score > 3:
        print(f'SKIPPING {tc_post_id}, '
              f'suspected class post (score {class_photo_score})')
        return

    tc_post_date = datetime.strptime(tc_post.date, '%Y-%m-%d')

    # Make sure the day has a pinned entry so we don't change the cover.

    tb_entries_for_day = tb.get_entries(tc_post_date.year,
                                        tc_post_date.month,
                                        tc_post_date.day)
    
    # If there are *any* posts and none are already pinned, choose the one
    # the server returned first (which is being used as the cover) to pin,
    # unless it's a post *we* created in which case we leave things alone.
    # That last case will occur if e.g. we partially ran on a day where no
    # other photos have been added yet.
    if len(tb_entries_for_day) > 0:
        if all([e.pinnedTimestamp is None for e in tb_entries_for_day]):
            maybe_pin = tb_entries_for_day[0]
            if maybe_pin.caption.find('tctbimport.') == -1:
                tb.pin_entry(maybe_pin)

    caption = text_from_html(tc_post.html)
    caption += (f'\n\n(post.{tc_post_id}, '
                f'tctbimport.{IMPORT_SESSION_ID})')

    new_tb_entry = tbtypes.EntryForCreate(
        year=tc_post_date.year,
        month=tc_post_date.month,
        day=tc_post_date.day,

        caption=caption,
    )

    if tc_post.original_photo_url:
        url = tc_post.original_photo_url

        with tempfile.NamedTemporaryFile(suffix=url_suffix(url)) as picture_file:
            # download original photo to temp file ...
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                shutil.copyfileobj(r.raw, picture_file)
            
            # ... and upload it to Tinybeans
            new_tb_entry.remoteFileName = upload_picture_file(Path(
                picture_file.name))

    tagged_children = tcposts.tagged_child_ids(tc_post.html)
    relevant_children: list[MatchingChild] = []
    for c in matching_children:
        if c.tc_id in tagged_children:
            relevant_children.append(c)
    
    # every TC post has at least one child we know tagged, or we wouldn't
    # be seeing it.
    assert len(relevant_children) > 0, "couldn't match tagged child"

    new_tb_entry.children = [c.tb_id for c in relevant_children]

    added_tb_entry = tb.create_entry(new_tb_entry)

    print(url_for_tinybeans_entry(added_tb_entry))
