from breddit import Backuper, get_logger

import reddit_secrets as config

import datetime
import os
import sys
from pprint import pprint

from kython import JSONType, json_dump_pretty

import logging
from kython.logging import setup_logzero

logger = get_logger()
setup_logzero(logger, level=logging.INFO)

BPATH = "/L/backups/reddit"

def compare(path, a, b):
    ignored = [
        '.score',
        '.ups',
        '.subscribers',
        '.subreddit_subscribers',
        '.num_comments',
    ]
    if any(path.endswith(i) for i in ignored):
        logger.info(f"Ignoring path {path}")
        return True
    if a == b:
        return True
    alleq = True
    if isinstance(a, (int, float, bool, type(None), str)):
        logger.warning(f"at path {path}: {a} != {b}")
        alleq = False
    elif isinstance(a, list) or isinstance(b, list):
        if a is None or b is None or len(a) != len(b):
            alleq = False
        else:
            for i in range(len(a)):
                if not compare(path + f"[]", a[i], b[i]):
                    alleq = False
    else: # dict??
        ka = set(a.keys())
        kb = set(b.keys())
        if ka != kb:
            alleq = False
        else:
            for k in ka:
                if not compare(path + f".{k}", a[k], b[k]):
                    alleq = False
    return alleq

# TODO mode to force backup? not sure if useful...
# TODO handle deletion of keys?
def load_last():
    import os
    lastf = max([f for f in os.listdir(BPATH) if f.endswith('.json')], default=None)
    if lastf is None:
        return None
    from kython import json_load
    lpath = os.path.join(BPATH, lastf)
    logger.info(f"loading last from {lpath}")
    with open(lpath, 'r') as fo:
        return json_load(fo)


def main():
    backuper = Backuper(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        username=config.USERNAME,
        password=config.PASSWORD,
    )
    logger.info("Retrieving reddit data...")
    backup = backuper.backup()
    cur = backup._asdict()
    ctime = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    curname = os.path.join(BPATH, f"reddit-{ctime}.json")

    last = load_last()
    if last is not None:
        logger.info("comparing with last backup...")
        res = compare('', last, cur)
        if res:
            logger.info("matched against old backup...skipping")
            cur = None
        else:
            logger.info("did not match")

    if cur is not None:
        logger.info(f"saving to {curname}")
        with open(curname, 'w') as fo:
            json_dump_pretty(fo, cur)

if __name__ == '__main__':
    main()
