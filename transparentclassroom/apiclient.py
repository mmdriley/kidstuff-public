from collections.abc import Iterable
import functools
import re
import os

import apischema
import requests

from . import apitypes


deserialize = functools.partial(apischema.deserialize, additional_properties=True)
API_BASE = 'https://www.transparentclassroom.com'

CHILD_ID_REGEX = re.compile(r'/s/\d+/children/(\d+)')
CLASSROOM_ID_REGEX = re.compile(r'/s/\d+/users\?classroom_id=(\d+)')

class TransparentClassroomClient:
    session: requests.Session
    user_info: apitypes.UserInfo

    def __init__(self, username: str, password: str):
        # Create a session that will have the right authentication header for
        # all requests. As an added bonus, using a session gets us connection
        # keep-alive.
        self.session = requests.Session()

        self.user_info = self._authenticate(username, password)
        self.session.headers.update({
            'X-TransparentClassroomToken': self.user_info.api_token,
        })

    def _authenticate(self, username: str, password: str) -> apitypes.UserInfo:
        r = self.session.get(
            f'{API_BASE}/api/v1/authenticate.json', auth=(username, password))
        r.raise_for_status()

        return deserialize(apitypes.UserInfo, r.json())

    @property
    def school_id(self) -> int:
        return self.user_info.school_id

    def my_children(self) -> list[apitypes.Child]:
        # This is a terrible hack, necessary after Transparent Classroom got
        # rid of their `my_subjects.json` endpoint.

        # Load the logged-in user's profile page, which:
        #   - includes links to each of their childrens' pages
        #   - is shown as part of the "Directory" view and has links to the other
        #     classrooms that the user has access to
        r = self.session.get(f'{API_BASE}/s/{self.school_id}/users/{self.user_info.id}')
        r.raise_for_status()

        # Get the child and classroom IDs, then load each classroom to figure out
        # which child(ren) are in it.
        child_ids = set(int(m[1]) for m in CHILD_ID_REGEX.finditer(r.text))
        classroom_ids = set(int(m[1]) for m in CLASSROOM_ID_REGEX.finditer(r.text))

        children = []

        for classroom_id in classroom_ids:
            all_children = self.children_in_classroom(classroom_id)
            children += [c for c in all_children if c.id in child_ids]

        # Check we found all the children.
        assert len(children) == len(child_ids)

        return children

    def children_in_classroom(self, classroom_id: int) -> list[apitypes.Child]:
        r = self.session.get(
            f'{API_BASE}/s/{self.school_id}/classrooms/{classroom_id}/children.json')
        r.raise_for_status()

        return deserialize(list[apitypes.Child], r.json())

    def all_child_posts_one_page(self, page: int) -> list[apitypes.Post]:
        # for just one child:
        # {API_BASE}/s/{school_id}/children/{child_id}/posts.json?page={page}
        r = self.session.get(
            f'{API_BASE}/s/{self.school_id}/posts.json?page={page}')
        r.raise_for_status()

        return deserialize(list[apitypes.Post], r.json())

    def all_child_posts(self) -> Iterable[apitypes.Post]:
        # Number of posts in a "full" page from `posts.json`.
        #
        # Derived empirically. It's also hardcoded in the mobile app and the
        # website: when they see fewer than 30 posts on a page, they stop
        # listing.
        #
        # The `posts.json` endpoint *seems* to accept a `per_page` argument, but
        # setting it to any value -- even the apparent default of 30 -- causes
        # it to return a 500 error.
        POSTS_PER_FULL_PAGE = 30

        page = 1
        prev_sort_key = None
        while True:
            page_of_posts = self.all_child_posts_one_page(page)
            assert len(page_of_posts) <= POSTS_PER_FULL_PAGE, (
                f'page has {len(page_of_posts)} posts, '
                f'expected no more than {POSTS_PER_FULL_PAGE}')

            for p in page_of_posts:
                sort_key = (p.date, p.created_at)
                if prev_sort_key:
                    # Check that posts come sorted the way we expect.
                    #
                    # We've seen a legitimate case of "equal". At that point
                    # there's no obvious guarantee of order, although it's
                    # empirically *not* by ID.
                    assert sort_key <= prev_sort_key
                prev_sort_key = sort_key

                yield p

            if len(page_of_posts) < POSTS_PER_FULL_PAGE:
                break

            page = page + 1

    def posts_by_id(self, ids: Iterable[int]) -> list[apitypes.Post]:
        r = self.session.get(
            f'{API_BASE}/s/{self.school_id}/posts.json',
            params={
                'ids[]': ids,
            })
        r.raise_for_status()

        return deserialize(list[apitypes.Post], r.json())


@functools.cache
def default_client() -> TransparentClassroomClient:
    username = os.getenv('TRANSPARENT_CLASSROOM_USERNAME')
    password = os.getenv('TRANSPARENT_CLASSROOM_PASSWORD')
    assert username and password, 'set TRANSPARENT_CLASSROOM_USERNAME and TRANSPARENT_CLASSROOM_PASSWORD'

    return TransparentClassroomClient(username, password)
