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

# TODO quite a bit of duplication... use dataclasses + mixin?
class Save(NamedTuple):
    created: datetime
    title: str
    raw: Json

    def __hash__(self):
        return hash(self.sid)

    @property
    def sid(self) -> Sid:
        return self.raw['id']

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return get_text(self.raw)

    @property
    def subreddit(self) -> str:
        return self.raw['subreddit']['display_name']


class Comment(NamedTuple):
    raw: Json

    @property
    def created(self) -> datetime:
        return make_dt(self.raw['created_utc'])

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return self.raw['body']


class Submission(NamedTuple):
    raw: Json

    @property
    def created(self) -> datetime:
        return make_dt(self.raw['created_utc'])

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return get_text(self.raw)

    @property
    def title(self) -> str:
        return self.raw['title']


class Upvote(NamedTuple):
    raw: Json

    @property
    def created(self) -> datetime:
        return make_dt(self.raw['created_utc'])

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return get_text(self.raw)

    @property
    def title(self) -> str:
        return self.raw['title']


def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def get_text(raw: Json) -> str:
    bb = raw.get('body', None)
    st = raw.get('selftext', None)
    if bb is not None and st is not None:
        raise RuntimeError(f'wtf, both body and selftext are not None: {bb}; {st}')
    return bb or st


def make_dt(ts: float) -> datetime:
    return pytz.utc.localize(datetime.utcfromtimestamp(ts))


class DAL:
    def __init__(self, sources: Sequence[PathIsh]) -> None:
        pathify = lambda s: s if isinstance(s, Path) else Path(s)
        self.sources = list(map(pathify, sources))


    def raw(self):
        for f in sorted(self.sources):
            with f.open() as fo:
                yield f, json.load(fo)


    def _accumulate(self, *, what: str) -> Iterator[Json]:
        logger = get_logger()
        emitted: Set[str] = set()
        for f, r in self.raw():
            # default sort order seems to return in the reverse order of 'save time', which makes sense to preserve
            # TODO careful, perhaps accept sort_by or something?
            raws = list(reversed(r[what]))
            chunk = len(raws)
            uniq = 0
            for raw in raws:
                eid = raw['id']
                if eid in emitted:
                    continue
                uniq += 1

                yield raw
                emitted.add(eid)
            logger.debug('%8s: finished processing %s: %4d/%4d new; total: %d', what, f, uniq, chunk, len(emitted))


    def saved(self) -> Iterator[Save]:
        for s in self._accumulate(what='saved'):
            created = make_dt(s['created_utc'])
            # TODO need permalink
            # url = get_some(s, 'link_permalink', 'url') # this was original url...
            title = s.get('link_title', s.get('title')); assert title is not None
            yield Save(
                created=created,
                title=title,
                raw=s,
            )


    def comments(self) -> Iterator[Comment]:
        # TODO makes sense to update them perhaps?
        for raw in self._accumulate(what='comments'):
            yield Comment(raw)


    def submissions(self) -> Iterator[Submission]:
        # TODO for submissions, makes sense to update (e.g. for upvotes)
        for raw in self._accumulate(what='submissions'):
            yield Submission(raw)


    def upvoted(self) -> Iterator[Upvote]:
        for raw in self._accumulate(what='upvoted'):
            yield Upvote(raw)



def demo(dal: DAL):
    print("Your comments:")
    for s in dal.comments():
        print(s.created, s.url)
        sep = '\n |  '
        body = sep + sep.join(s.text.splitlines())
        print(body) # TOD ??
        print()
    # TODO some pandas?

    from collections import Counter
    c = Counter([s.subreddit for s in dal.saved()])
    from pprint import pprint
    print("Your most saved subreddits:")
    pprint(c.most_common(5))


if __name__ == '__main__':
    import dal_helper
    dal_helper.main(DAL=DAL, demo=demo)
