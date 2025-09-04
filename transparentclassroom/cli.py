from datetime import datetime
import json

from apischema import serialize
import click

from . import apiclient
from htmlfunctions import text_from_html
from . import postfunctions


@click.group()
def tc():
    """Transparent Classroom"""
    pass


@tc.command()
def info():
    """Show details of logged-in user"""
    c = apiclient.default_client()

    u = c.user_info
    print(
        f'Logged in as {u.first_name} {u.last_name} ({u.email})\n'
        f'  User ID:   {u.id}\n'
        f'  School ID: {u.school_id}')

    print()

    children = c.my_children()
    print(f'Found {len(children)} children')
    for child in children:
        assert len(child.current_classroom_ids) == 1
        print(f'- {child.first_name} {child.last_name}\n'
                f'    Child ID:     {child.id}\n'
                f'    Classroom ID: {child.current_classroom_ids[0]}')


@tc.command()
@click.option('--since', type=click.DateTime(['%Y-%m-%d']))
@click.option('--until', type=click.DateTime(['%Y-%m-%d']))
@click.argument('ids', nargs=-1, type=click.INT)
def posts(since: datetime | None, until: datetime | None, ids: tuple[int, ...]):
    """List posts for all children, newest first"""

    c = apiclient.default_client()
    if len(ids) > 0:
        posts = c.posts_by_id(ids)
    else:
        posts = c.all_child_posts()

    if since is not None or until is not None:
        posts = postfunctions.filter_by_date(posts, since, until)

    first = True
    for p in posts:
        if not first:
            print()
        first = False
        print(json.dumps(serialize(p), indent=2))
        print('tagged children: ', postfunctions.tagged_child_ids(p.html))
        print('class post score: ',
              postfunctions.all_class_post_confidence(p.html))
        print('plaintext: ', text_from_html(p.html))


if __name__ == '__main__':
    tc()
