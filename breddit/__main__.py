from breddit import Backuper

import reddit_secrets as config

import sys
from pprint import pprint

from kython import JSONType, json_dump_pretty

def main():
    backuper = Backuper(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        username=config.USERNAME,
        password=config.PASSWORD,
    )
    backup = backuper.backup()
    json_dump_pretty(sys.stdout, backup._asdict())

if __name__ == '__main__':
    main()
