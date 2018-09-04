from breddit import Backuper, get_logger

import reddit_secrets as config

import datetime
import os
import sys
from pprint import pprint

from kython import JSONType, json_dumps_pretty

import logging
from kython.logging import setup_logzero

logger = get_logger()

import lzma

BPATH = "/L/backups/reddit"

def compare(path, a, b):
    ignored = [
        '.score',
        '.ups',
        '.subscribers',
        '.subreddit_subscribers',
        '.num_comments',
        '_links_count',
    ]
    if any(path.endswith(i) for i in ignored):
        logger.info(f"ignoring path {path}")
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
    elif isinstance(a, dict) or isinstance(b, dict):
        ka = set(a.keys())
        kb = set(b.keys())
        if ka != kb:
            alleq = False
        else:
            for k in ka:
                if not compare(path + f".{k}", a[k], b[k]):
                    alleq = False
    else:
        raise RuntimeError(f"Type mismatch: {type(a)} vs {type(b)}")

    return alleq

# TODO mode to force backup? not sure if useful...
# TODO handle deletion of keys?
def load_last():
    import os
    lastf = max([f for f in os.listdir(BPATH) if f.endswith('.json.xz')], default=None)
    if lastf is None:
        return None
    import json
    lpath = os.path.join(BPATH, lastf)
    logger.info(f"loading last from {lpath}")
    with lzma.open(lpath, 'r') as fo:
        return json.loads(fo.read().decode('utf8'))


def main():
    setup_logzero(logger, level=logging.INFO)
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
    curname = os.path.join(BPATH, f"reddit-{ctime}.json.xz")

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
        with lzma.open(curname, 'w') as fo:
            fo.write(json_dumps_pretty(fo, cur, indent=1).encode('utf8'))

if __name__ == '__main__':
    main()
