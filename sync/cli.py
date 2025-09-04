from datetime import datetime

import click

import tinybeans.apiclient as tbclient
import transparentclassroom.apiclient as tcclient
import transparentclassroom.postfunctions as tcposts
from . import postsync


@click.group()
def sync():
    """Sync from TransparentClassroom to Tinybeans"""
    pass


@sync.command()
@click.option('--tinybeans-journal', type=str)
@click.argument('tc_post_ids', nargs=-1, type=click.INT)
def copy_posts_by_id(tinybeans_journal: str | None,
                     tc_post_ids: tuple[int, ...]):
    tc = tcclient.default_client()
    tb = tbclient.default_client().journal(tinybeans_journal)

    print(postsync.IMPORT_SESSION_ID)

    matching_children = postsync.find_matching_children(tc, tb)

    for id in tc_post_ids:
        postsync.copy_one_post(tc, tb, matching_children, id)


@sync.command()
@click.option('--since', type=click.DateTime(['%Y-%m-%d']), required=True)
@click.option('--until', type=click.DateTime(['%Y-%m-%d']), required=True)
@click.option('--tinybeans-journal', type=str)
def copy_posts_in_range(since: datetime, until: datetime,
                        tinybeans_journal: str | None):
    tc = tcclient.default_client()
    tb = tbclient.default_client().journal(tinybeans_journal)

    print(postsync.IMPORT_SESSION_ID)

    matching_children = postsync.find_matching_children(tc, tb)
    tc_posts = tcposts.filter_by_date(tc.all_child_posts(), since, until)

    for post in tc_posts:
        postsync.copy_one_post(tc, tb, matching_children, post)


@sync.command()
@click.option('--tinybeans-journal', type=str)
def show_matching_children(tinybeans_journal: str | None):
    tc = tcclient.default_client()
    tb = tbclient.default_client().journal(tinybeans_journal)
    for c in postsync.find_matching_children(tc, tb):
        print(f'{c.first_name} {c.last_name}\tTC:{c.tc_id}\tTB:{c.tb_id}')
