#!/usr/bin/env python3
from pathlib import PurePath, Path
from typing import List, Dict, Union, Iterator, NamedTuple, Any, Sequence, Optional
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

    def raw(self) -> Json:
        f = max(self.sources)
        # TODO FIXME merge them properly?
        with f.open() as fo:
            return json.load(fo)

    def saved(self) -> Iterator[Save]:
        for s in self.raw()['saved']:
            created = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
            # TODO need permalink
            # url = get_some(s, 'link_permalink', 'url') # this was original url...
            title = s.get('link_title', s.get('title')); assert title is not None
            yield Save(
                created=created,
                title=title,
                sid=s['id'],
                json=s,
            )
        # default sort order seems to redurn in the reverse order of 'save time', so it's good
        # TODO assert for that?

    # TODO add other things, e.g. upvotes/comments etc


# TODO hmm. apparently decompressing takes quite a bit of time...


def demo(dal: DAL):
    print("Saved posts:")
    saved = list(dal.saved())

    for s in saved:
        print(s.created, s.url, s.title)
    # TODO some pandas?

    from collections import Counter
    c = Counter([s.subreddit for s in saved])
    from pprint import pprint
    print("Your most saved subreddits:")
    pprint(c.most_common(5))


if __name__ == '__main__':
    import dal_helper
    dal_helper.main(DAL=DAL, demo=demo)
