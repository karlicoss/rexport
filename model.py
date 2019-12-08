#!/usr/bin/env python3
from pathlib import PurePath, Path
from typing import List, Dict, Union, Iterable, Iterator, NamedTuple, Any, Sequence, Optional
import json
from functools import lru_cache
from collections import OrderedDict
from pathlib import Path
import re
from datetime import datetime
from multiprocessing import Pool
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



class Model:
    def __init__(self, sources: Sequence[PathIsh]) -> None:
        pathify = lambda s: s if isinstance(s, Path) else Path(s)
        self.sources = list(map(pathify, sources))

    def raw(self) -> Json:
        f = max(self.sources)
        # TODO merge them properly?
        with f.open() as fo:
            return json.load(fo)

    def saved(self) -> List[Save]:
        def it():
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
        return list(it())

    # TODO add other things, e.g. upvotes/comments etc


# TODO hmm. apparently decompressing takes quite a bit of time...

# TODO heep this
def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def main():
    # TODO FIXME could benefit from some common code here
    # for unpacking
    # for get_files like in my. package

    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('--path', type=Path, required=True)
    args = p.parse_args()
    model = Model([args.path])
    for s in model.saved():
        print(s)


if __name__ == '__main__':
    main()
