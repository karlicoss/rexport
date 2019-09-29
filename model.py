#!/usr/bin/env python3
from pathlib import Path
from typing import List, Dict, Union, Iterable, Iterator, NamedTuple, Any, Sequence
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


PathIsh = Union[str, Path]
Json = Dict[str, Any]


Sid = str

class Save(NamedTuple):
    created: datetime
    title: str
    sid: Sid
    json: Any = None
    # TODO ugh. not sure how to support this in cachew... could try serializing dicts of simple types automatically.. but json can't be properly typed
    # TODO why would json be none?

    def __hash__(self):
        return hash(self.sid)

    @property
    def url(self) -> str:
        # pylint: disable=unsubscriptable-object
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
        assert self.json is not None
        # pylint: disable=unsubscriptable-object
        return self.json['subreddit']['display_name']



class Model:
    def __init__(self, sources: Sequence[PathIsh]) -> None:
        self.sources = list(map(Path, sources))

    def raw(self) -> Json:
        f = max(self.sources)
        with f.open() as fo:
            return json.load(fo)
        # from kython import kompress # TODO FIXME
        # with kompress.open(f) as fo:
        #     return json.load(fo)

    def saved(self) -> List[Save]:
        def it():
            for s in self.raw()['saved']:
                created = pytz.utc.localize(datetime.utcfromtimestamp(s['created_utc']))
                # TODO need permalink
                # url = get_some(s, 'link_permalink', 'url') # this was original url...
                title = s.get('link_title', s)['title']
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

