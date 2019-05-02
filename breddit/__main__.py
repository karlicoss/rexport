import datetime
import os
import sys
from pprint import pprint
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import logging


from breddit import Backuper, get_logger

import reddit_secrets as config # type: ignore


from kython.klogging import setup_logzero
from kython.misc import import_file
from kython import kompress

BPATH = Path("/L/backups/reddit")


def get_last():
    backups = BPATH.glob('*.json.xz') # TODO FIX xz... how to ignore .bleanser files?
    lastf = max(backups, default=None)
    return lastf


def fetch_latest():
    logger = get_logger()
    logger.info("retrieving latest data from Reddit")

    backuper = Backuper(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        username=config.USERNAME,
        password=config.PASSWORD,
    )
    return backuper.backup()


def main():
    logger = get_logger()
    setup_logzero(logger, level=logging.DEBUG, cronlevel=logging.WARNING)

    previous = get_last()

    latest_js = fetch_latest()

    if previous is not None: # ugh. indentation looks very ugly
        with TemporaryDirectory() as td:
            tdir = Path(td)
            latest = tdir / 'latest.json'
            with latest.open('w') as fo:
                json.dump(latest_js, fo, ensure_ascii=False, indent=1)

            # bleanser = import_file('/L/zzz_syncthing/coding/bleanser/reddit.py')
            bleanser = import_file('/L/zzz_syncthing/soft/stable/bleanser/reddit.py')
            norm = bleanser.RedditNormaliser()
            setup_logzero(norm.logger, level=logging.DEBUG)
            comp = norm.diff_with(previous, latest, cmd=norm.cleanup(), tdir=tdir)
            logger.info('comparison result: %s', comp.cmp)
            if comp.cmp == bleanser.CmpResult.SAME: # TODO maybe need to take both into account?
                logger.info('backups are same.. exiting')
                return
            else:
                logger.debug('diff: %s', comp.diff)

    ctime = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
    curpath = BPATH / f"reddit-{ctime}.json.xz"

    logger.info('saving to %s', curpath)
    with kompress.open(curpath, 'wb') as fo:
        fo.write(json.dumps(latest_js, ensure_ascii=False, indent=1).encode('utf8'))

if __name__ == '__main__':
    main()
