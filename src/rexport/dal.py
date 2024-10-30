from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator, Sequence
from concurrent.futures import Executor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .exporthelpers import dal_helper, logging_helper
from .exporthelpers.dal_helper import Json, PathIsh, datetime_aware, pathify
from .utils import DummyFuture, json_items_as_list

logger = logging_helper.make_logger(__name__)


Sid = str


# TODO quite a bit of duplication... use dataclasses + mixin?
@dataclass
class Save:
    created: datetime_aware
    title: str
    raw: Json

    def __hash__(self):
        return hash(self.sid)

    @property
    def id(self) -> str:
        return self.raw['id']

    # keep here for backwards compatability
    @property
    def sid(self) -> Sid:
        return self.id

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return get_text(self.raw)

    @property
    def subreddit(self) -> str:
        return self.raw['subreddit']['display_name']


@dataclass
class Comment:
    raw: Json

    @property
    def id(self) -> str:
        return self.raw['id']

    @property
    def created(self) -> datetime_aware:
        return make_dt(self.raw['created_utc'])

    @property
    def url(self) -> str:
        return reddit(self.raw['permalink'])

    @property
    def text(self) -> str:
        return self.raw['body']


@dataclass
class Submission:
    raw: Json

    @property
    def id(self) -> str:
        return self.raw['id']

    @property
    def created(self) -> datetime_aware:
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


@dataclass
class Upvote:
    raw: Json

    @property
    def id(self) -> str:
        return self.raw['id']

    @property
    def created(self) -> datetime_aware:
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


@dataclass
class Subreddit:
    raw: Json

    @property
    def id(self) -> str:
        return self.raw['id']

    @property
    def url(self) -> str:
        return reddit(self.raw['url'])

    @property
    def title(self) -> str:
        return self.raw['title']


@dataclass
class Multireddit:
    raw: Json

    @property
    def path(self) -> str:
        # multireddits don't have an id? so it kinda serves as such..
        return self.raw['path']

    @property
    def name(self) -> str:
        return self.raw['name']

    @property
    def subreddits(self) -> Sequence[str]:
        # ugh. subreddits in multireddit list don't have all the other fields like id and title..
        return tuple(r['_path'] for r in self.raw['subreddits'])


@dataclass
class Profile:
    raw: Json

    @property
    def id(self) -> str:
        return self.raw['id']

    @property
    def url(self) -> str:
        return reddit(self.raw['subreddit']['url'])

    @property
    def name(self) -> str:
        return self.raw['name']

    @property
    def comment_karma(self) -> int:
        return self.raw['comment_karma']

    @property
    def link_karma(self) -> int:
        return self.raw['link_karma']

    @property
    def total_karma(self) -> int:
        return self.raw['total_karma']


def reddit(suffix: str) -> str:
    return 'https://reddit.com' + suffix


def get_text(raw: Json) -> str:
    bb = raw.get('body', None)
    st = raw.get('selftext', None)
    if bb is not None and st is not None:
        raise RuntimeError(f'wtf, both body and selftext are not None: {bb}; {st}')
    return bb or st


def make_dt(ts: float) -> datetime_aware:
    return datetime.fromtimestamp(ts, tz=timezone.utc)


class DAL:
    def __init__(self, sources: Sequence[PathIsh], *, cpu_pool: Executor | None = None) -> None:
        self.sources = list(map(pathify, sources))
        self.cpu_pool = cpu_pool
        self.enlighten = logging_helper.get_enlighten()

    # not sure how useful it is, but keeping for compatibility
    def raw(self):
        for f in self.sources:
            with f.open() as fo:
                yield f, json.load(fo)

    def _raw_json(self, *, what: str) -> Iterator[Json]:
        progress_bar = self.enlighten.counter(total=len(self.sources), desc=f'{__name__}[{what}]', unit='files')

        cpu_pool = self.cpu_pool

        futures = []
        for path in self.sources:
            # TODO maybe if enlighten is used, this should be debug instead? so logging isn't too verbose
            logger.info(f'processing {path}')

            if cpu_pool is not None:
                future = cpu_pool.submit(json_items_as_list, path, what)
            else:
                future = DummyFuture(json_items_as_list, path, what)

            futures.append(future)

        for f in futures:
            res = f.result()
            progress_bar.update()

            # default sort order seems to return in the reverse order of 'save time', which makes sense to preserve
            # TODO reversing should probably be responsibility of HPI?
            yield from reversed(res)

    def _accumulate(self, *, what: str, key: str = 'id') -> Iterator[Json]:
        emitted: set[str] = set()
        # todo use unique_everseen?
        for raw in self._raw_json(what=what):
            eid = raw[key]
            if eid in emitted:
                continue
            emitted.add(eid)
            yield raw

    def saved(self) -> Iterator[Save]:
        for s in self._accumulate(what='saved'):
            created = make_dt(s['created_utc'])
            # TODO need permalink
            # url = get_some(s, 'link_permalink', 'url') # this was original url...
            title = s.get('link_title', s.get('title'))
            assert title is not None, s
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

    def subreddits(self) -> Iterator[Subreddit]:
        for raw in self._accumulate(what='subreddits'):
            yield Subreddit(raw)

    def multireddits(self) -> Iterator[Multireddit]:
        for raw in self._accumulate(what='multireddits', key='path'):
            yield Multireddit(raw)

    def profile(self) -> Profile:
        # meh.. doesn't really conform to the rest of data which are iterables
        last = max(self.sources)
        with last.open() as fo:
            j = json.load(fo)
            return Profile(j['profile'])


@contextlib.contextmanager
def _test_data():
    tdata = Path(__file__).absolute().parent.parent.parent / 'testdata'

    def get(what: str):
        [subreddits_file] = tdata.rglob(what)
        for x in json.loads(subreddits_file.read_text())['data']['children']:
            yield x['data']

    # todo use more data from this repo
    j = {
        'subreddits': list(get('subreddit/list.json')),
        'comments': list(get('user/comments.json')),
    }

    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as td:
        tdir = Path(td)
        jfile = tdir / 'data.json'
        jfile.write_text(json.dumps(j))
        yield [jfile]


def test() -> None:
    with _test_data() as files:
        dal = DAL(files)

        subs = list(dal._accumulate(what='subreddits'))
        assert len(subs) == 3

        assert len(list(dal.comments())) > 0


def demo(dal: DAL) -> None:
    print("Your comments:")
    for s in dal.comments():
        print(s.created, s.url)
        sep = '\n |  '
        body = sep + sep.join(s.text.splitlines())
        print(body)
        print()
    # TODO some pandas?

    from collections import Counter

    c = Counter([s.subreddit for s in dal.saved()])
    from pprint import pprint

    print("Your most saved subreddits:")
    pprint(c.most_common(5))


if __name__ == '__main__':
    dal_helper.main(DAL=DAL, demo=demo)
