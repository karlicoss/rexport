#!/usr/bin/env python3
from pathlib import PurePath, Path
from typing import List, Dict, Union, Iterator, NamedTuple, Any, Sequence, Optional, Set
import json
from pathlib import Path
from datetime import datetime
import logging

import pytz


def get_logger():
    return logging.getLogger('rexport')


PathIsh = Union[str, PurePath]
Json = Dict[str, Any]


Sid = str

class Save(NamedTuple):
    created: datetime
    title: str
    sid: Sid
    json: Json

    def __hash__(self):
        return hash(self.sid)

    @property
    def url(self) -> str:
        pl = self.json['permalink']
        return reddit(pl)

    @property
    def text(self) -> str:
        bb = self.json.get('body', None)
        st = self.json.get('selftext', None)
        if bb is not None and st is not None:
            raise RuntimeError(f'wtf, both body and selftext are not None: {bb}; {st}')
        return bb or st

    @property
    def subreddit(self) -> str:
        return self.json['subreddit']['display_name']


def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


class DAL:
    def __init__(self, sources: Sequence[PathIsh]) -> None:
        pathify = lambda s: s if isinstance(s, Path) else Path(s)
        self.sources = list(map(pathify, sources))


    def raw(self):
        for f in sorted(self.sources):
            with f.open() as fo:
                yield f, json.load(fo)


    def saved(self) -> Iterator[Save]:
        logger = get_logger()
        emitted: Set[Sid] = set()
        for f, r in self.raw():
            # default sort order seems to return in the reverse order of 'save time', which makes sense to preserve
            saved = list(reversed(r['saved']))
            chunk = len(saved)
            uniq = 0
            for s in saved:
                sid = s['id']
                if sid in emitted:
                    continue
                uniq += 1

                created = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
                # TODO need permalink
                # url = get_some(s, 'link_permalink', 'url') # this was original url...
                title = s.get('link_title', s.get('title')); assert title is not None
                yield Save(
                    created=created,
                    title=title,
                    sid=sid,
                    json=s,
                )
                emitted.add(sid)
            logger.debug('finished processing %s: %4d/%4d new saves; total: %d', f, uniq, chunk, len(emitted))

    # TODO add other things, e.g. upvotes/comments etc


def demo(dal: DAL):
    print("Saved posts:")
    for s in dal.saved():
        print(s.created, s.url, s.title)
    # TODO some pandas?

    from collections import Counter
    saved = list(dal.saved())
    c = Counter([s.subreddit for s in saved])
    from pprint import pprint
    print("Your most saved subreddits:")
    pprint(c.most_common(5))


if __name__ == '__main__':
    import dal_helper
    dal_helper.main(DAL=DAL, demo=demo)
