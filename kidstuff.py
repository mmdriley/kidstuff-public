#! /usr/bin/env python3

import click

from sync.cli import sync as sync_command
from tinybeans.cli import tb as tinybeans_command
from transparentclassroom.cli import tc as transparentclassroom_command


@click.group()
def kidstuff():
    pass


kidstuff.add_command(sync_command)
kidstuff.add_command(tinybeans_command)
kidstuff.add_command(transparentclassroom_command)

if __name__ == '__main__':
    kidstuff()
