from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator, Sequence
from concurrent.futures import Executor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path

import hpikit.cli.dal as cli
import koncurrent
from hpikit.datetime import AwareDateTime, aware
from hpikit.json import Json, loads
from hpikit.paths import as_paths
from kloggy import get_logger
from kloggy.progress import progress

logger = get_logger(__name__)


Sid = str


# TODO quite a bit of duplication... use dataclasses + mixin?
@dataclass
class Save:
    created: AwareDateTime
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
    def created(self) -> AwareDateTime:
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
    def created(self) -> AwareDateTime:
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
    def created(self) -> AwareDateTime:
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
    bb: str | None = raw.get('body', None)
    st: str | None = raw.get('selftext', None)
    if bb is not None and st is not None:
        raise RuntimeError(f'wtf, both body and selftext are not None: {bb}; {st}')
    res = bb or st
    assert res is not None, f'both body and selftext are None? {raw=}'
    return res


def make_dt(ts: float) -> AwareDateTime:
    return aware(datetime.fromtimestamp(ts, tz=UTC))


def _process_path(path: Path, *, what: str) -> list[Json]:
    """
    Helper function to process one file -- needs to be on the top level in case ProcessPoolExecutor is used.
    """
    return loads(path.read_bytes())[what]


class DAL:
    def __init__(self, sources: Sequence[Path | str]) -> None:
        self.sources = as_paths(sources)

        # where to parse the files -- None means koncurrent's shared default, serial unless configured otherwise
        # set these before iterating to override, e.g. dal.executor = ThreadPoolExecutor(4)
        self.executor: Executor | None = None
        self.buffersize: int | None = None  # None: twice the executor's number of workers, or 1 when running serially

    # not sure how useful it is, but keeping for compatibility
    def raw(self):
        for f in self.sources:
            yield f, loads(f.read_bytes())

    def _raw_json(self, *, what: str) -> Iterator[Json | Exception]:
        process = partial(_process_path, what=what)
        with koncurrent.map_results(
            process, self.sources, executor=self.executor, buffersize=self.buffersize
        ) as results:
            # Track results as they are consumed, so queued executor work doesn't advance the bar prematurely.
            # Log each path before waiting for its result, including before parsing in serial mode.
            files = progress(self.sources, logger=logger, desc=f'{__name__}[{what}]', unit='files')
            for path, result in zip(files, results, strict=True):
                if isinstance(result, Exception):
                    result.add_note(f'^ while processing {path}')
                    yield result
                    continue
                # default sort order seems to return in the reverse order of 'save time', which makes sense to preserve
                # TODO reversing should probably be responsibility of HPI?
                yield from result

    def _accumulate(self, *, what: str, key: str = 'id') -> Iterator[Json | Exception]:
        emitted: set[str] = set()
        # todo use unique_everseen?
        for raw in self._raw_json(what=what):
            if isinstance(raw, Exception):
                yield raw
                continue
            eid = raw[key]
            if eid in emitted:
                continue
            emitted.add(eid)
            yield raw

    def saved(self) -> Iterator[Save | Exception]:
        for s in self._accumulate(what='saved'):
            if isinstance(s, Exception):
                yield s
                continue
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

    def comments(self) -> Iterator[Comment | Exception]:
        # TODO makes sense to update them perhaps?
        for raw in self._accumulate(what='comments'):
            if isinstance(raw, Exception):
                yield raw
                continue
            yield Comment(raw)

    def submissions(self) -> Iterator[Submission | Exception]:
        # TODO for submissions, makes sense to update (e.g. for upvotes)
        for raw in self._accumulate(what='submissions'):
            if isinstance(raw, Exception):
                yield raw
                continue
            yield Submission(raw)

    def upvoted(self) -> Iterator[Upvote | Exception]:
        for raw in self._accumulate(what='upvoted'):
            if isinstance(raw, Exception):
                yield raw
                continue
            yield Upvote(raw)

    def subreddits(self) -> Iterator[Subreddit | Exception]:
        for raw in self._accumulate(what='subreddits'):
            if isinstance(raw, Exception):
                yield raw
                continue
            yield Subreddit(raw)

    def multireddits(self) -> Iterator[Multireddit | Exception]:
        for raw in self._accumulate(what='multireddits', key='path'):
            if isinstance(raw, Exception):
                yield raw
                continue
            yield Multireddit(raw)

    def profile(self) -> Profile:
        # meh.. doesn't really conform to the rest of data which are iterables
        last = max(self.sources)
        j = loads(last.read_bytes())
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
        if isinstance(s, Exception):
            logger.error(s, exc_info=s)
            continue
        print(s.created, s.url)
        sep = '\n |  '
        body = sep + sep.join(s.text.splitlines())
        print(body)
        print()
    # TODO some pandas?

    from collections import Counter

    c: Counter[str] = Counter()
    for saved in dal.saved():
        if isinstance(saved, Exception):
            logger.error(saved, exc_info=saved)
            continue
        c[saved.subreddit] += 1
    from pprint import pprint

    print("Your most saved subreddits:")
    pprint(c.most_common(5))


if __name__ == '__main__':
    cli.main(DAL=DAL, demo=demo)
