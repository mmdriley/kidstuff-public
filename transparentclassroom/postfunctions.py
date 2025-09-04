from collections.abc import Iterable
from datetime import datetime
import html5lib
import re

from . import apitypes


def tagged_child_ids(post_html: str) -> list[int]:
    root = html5lib.parseFragment(post_html, namespaceHTMLElements=False)

    ids: list[int] = []
    for el in root:
        if el.tag != 'a' or el.get('class') != 'child-link':
            continue
        m = re.fullmatch(r'/s/\d+/children/(\d+)', el.get('href'))
        assert m is not None, 'child-link with unexpected href'
        ids.append(int(m.group(1)))

    return ids


def all_class_post_confidence(post_html: str) -> int:
    root = html5lib.parseFragment(post_html, namespaceHTMLElements=False)

    # All-class posts have an automatically-expanded set of tags that lists
    # every child in the class, sorted alphabetically and separated by spaces.
    # Sometimes the teacher will notice someone is missing and remove a name,
    # leaving behind extra whitespace.
    #
    # To define our "confidence" a post is for the whole class, we look for
    # runs of tagged children separated by whitespace, and look for the
    # longest freestanding run that is also sorted.

    def runs_of_names():
        this_run = []

        # Iterate over elements in the post looking for tagged children.
        # Look for the places where we know a run must end:
        #  - we see an element that isn't a tagged child
        #  - we see the next element is separated from this one by something
        #    other than whitespace
        # In either case, yield the current run and start with an empty one.
        for el in root:
            if el.tag == 'a' and el.get('class') == 'child-link':
                this_run.append(el.text)

                if not el.tail or el.tail.isspace():
                    continue

            # The most recent run is over -- it either ended with this element
            # or the previous one. Yield it and start a new empty run. For
            # simplicity we allow yielding the empty list.
            yield this_run
            this_run = []

        # Yield the names for the last run.
        yield this_run

    # Find the length of the longest *sorted* run of names.
    return max([len(r) for r in runs_of_names() if r == sorted(r)], default=0)


# both endpoints are inclusive
def filter_by_date(posts: Iterable[apitypes.Post], since: datetime | None,
                   until: datetime | None) -> Iterable[apitypes.Post]:
    for p in posts:
        post_date = p.date_as_datetime

        if since is not None and post_date < since:
            break
        if until is not None and post_date > until:
            continue

        yield p
