#!/usr/bin/env python3
from datetime import datetime, timezone
import json
from pathlib import Path
from types import new_class
from typing import NamedTuple, List, Dict, Optional

import praw  # type: ignore[import-untyped]
from praw.models import (  # type: ignore[import-untyped]
    Comment,
    Message,
    Multireddit,
    PollData,
    PollOption,
    Redditor,
    Submission,
    Subreddit,
    UserSubreddit,
)

from .exporthelpers.export_helper import Json
from .exporthelpers.logging_helper import setup_logger, make_logger


logger = make_logger(__name__)


class RedditData(NamedTuple):
    # fmt: off
    profile     : Json
    multireddits: List[Json]
    subreddits  : List[Json]
    saved       : List[Json]
    upvoted     : List[Json]
    downvoted   : List[Json]
    comments    : List[Json]
    submissions : List[Json]
    inbox       : List[Json]
    # fmt: on


def ignore_item(key: str, value) -> bool:
    if callable(value):
        return True

    if key.startswith('__'):
        return True

    if key in {
        'body_html',
        'selftext_html',
        'description_html',
        'preview',
    }:
        return True

    return False


# sadly praw doesn't keep raw json data :( https://github.com/praw-dev/praw/issues/830
def jsonify(d):
    if isinstance(d, (str, float, int, bool, type(None))):
        return d

    if isinstance(d, list):
        return [jsonify(x) for x in d]

    if isinstance(d, dict):
        return {k: jsonify(v) for k, v in d.items() if not ignore_item(k, v)}

    # fmt: off
    if isinstance(d, (
            Redditor,
            Subreddit,
            Multireddit,
            Submission,
            Comment,
            Message,
            PollData,
            PollOption,
            UserSubreddit,
    )): # TODO eh, hopefully it can't go into infinite loop...
        return jsonify(vars(d))
    # fmt: on

    if isinstance(d, praw.Reddit):
        return None

    raise RuntimeError(f"Unexpected type: {type(d)}")


def _extract(from_, **kwargs) -> List[Dict]:
    logger.info('fetching %s', from_)
    return jsonify(list(from_(**kwargs)))


class Exporter:
    def __init__(self, *args, previous: Optional[Path] = None, **kwargs) -> None:
        self.api = praw.Reddit(user_agent="rexport", *args, **kwargs)
        if previous is not None:
            from kompress import CPath  # type: ignore[import-not-found]
            prev = CPath(previous)
            self.prev_json = json.loads(prev.read_text())
        else:
            self.prev_json = None

    @property
    def _me(self):
        return self.api.user.me()

    def extract_profile(self) -> Json:
        return jsonify(self._me)

    def export_json(self) -> Json:
        rb = RedditData(
            # fmt: off
            profile     =self.extract_profile(),
            multireddits=_extract(self.api.user.multireddits), # weird, multireddits has no limit
            subreddits  =_extract(self.api.user.subreddits, limit=None),
            saved       =_extract(self._me.saved          , limit=None),
            upvoted     =_extract(self._me.upvoted        , limit=None),
            downvoted   =_extract(self._me.downvoted      , limit=None),
            comments    =_extract(self._me.comments.new   , limit=None),
            submissions =_extract(self._me.submissions.new, limit=None),
            inbox       =_extract(self.api.inbox.all      , limit=None),
            # fmt: on
        )
        res_dict = rb._asdict()
        self._populate_first_exported(res_dict)
        return res_dict

    def _populate_first_exported(self, res_dict) -> None:
        """
        Basically reddit api doesn't return the date when entry was added
        (e.g. actual time you've upvoted/downvoted/saved item etc)

        So this is an attempt to at least infer it by comparing with a previous export

        """
        prev_json = self.prev_json
        if prev_json is None:
            return res_dict

        now_ms_utc = datetime.utcnow().timestamp()

        # otherwise populate with a guess for the time when entry was added
        for k, v in res_dict.items():
            if not isinstance(v, list):
                continue

            prev_by_id = {x.get('id'): x for x in prev_json[k]}
            for item in v:
                iid = item.get('id')
                if iid is None:
                    # just in case, defensive
                    continue

                prev_item = prev_by_id.get(iid)
                FIRST_EXPORTED_KEY = 'rexport_first_exported_utc'
                first_exported_utc: float

                if prev_item is None:
                    # we haven't seen it previously, so assuming it was just added
                    first_exported_utc = now_ms_utc
                    item[FIRST_EXPORTED_KEY] = first_exported_utc
                else:
                    prev_first_exported = prev_item.get(FIRST_EXPORTED_KEY)
                    if prev_first_exported is not None:
                        # if the item was in previous export and already was exported before, need to copy the timestamp
                        first_exported_utc = prev_first_exported
                        item[FIRST_EXPORTED_KEY] = first_exported_utc
                    else:
                        # we've seen item before, but it doesn't have the rexport timestamp...
                        # not much we can do really, best to keep it intact
                        pass

    def export(self) -> Json:
        # keeping for backwards compatibility
        return self.export_json()


def get_json(**kwargs) -> Json:
    return Exporter(**kwargs).export_json()


def main() -> None:
    # https://praw.readthedocs.io/en/latest/getting_started/logging.html
    setup_logger('prawcore', level='INFO')  # debug can be useful during development

    parser = make_parser()
    args = parser.parse_args()

    params = args.params
    dumper = args.dumper
    previous = args.previous

    j = get_json(**params, previous=previous)
    js = json.dumps(j, ensure_ascii=False, indent=1)
    dumper(js)


def make_parser():
    from .exporthelpers.export_helper import setup_parser, Parser

    parser = Parser('Export your personal Reddit data: saves, upvotes, submissions etc. as JSON.')
    setup_parser(
        parser=parser,
        params=[
            'username',
            'password',
            'client_id',
            'client_secret',
        ],
        extra_usage='''
You can also import ~export.py~ as a module and call ~get_json~ function directly to get raw JSON.
        ''',
    )
    parser.add_argument('--previous', type=Path, required=False, help="Experimental argument to guess the timestamp when item was saved/upvoted etc.")
    return parser


if __name__ == '__main__':
    main()
