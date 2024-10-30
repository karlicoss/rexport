import json
from typing import NamedTuple

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
from .exporthelpers.logging_helper import make_logger, setup_logger

logger = make_logger(__name__)


class RedditData(NamedTuple):
    # fmt: off
    profile     : Json
    multireddits: list[Json]
    subreddits  : list[Json]
    saved       : list[Json]
    upvoted     : list[Json]
    downvoted   : list[Json]
    comments    : list[Json]
    submissions : list[Json]
    inbox       : list[Json]
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


def _extract(from_, **kwargs) -> list[dict]:
    logger.info('fetching %s', from_)
    return jsonify(list(from_(**kwargs)))


class Exporter:
    def __init__(self, *args, **kwargs) -> None:
        self.api = praw.Reddit(user_agent="rexport", *args, **kwargs)  # noqa: B026

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
        return rb._asdict()

    def export(self) -> Json:
        # keeping for backwards compatibility
        return self.export_json()


def get_json(**params) -> Json:
    return Exporter(**params).export_json()


def main() -> None:
    # https://praw.readthedocs.io/en/latest/getting_started/logging.html
    setup_logger('prawcore', level='INFO')  # debug can be useful during development

    parser = make_parser()
    args = parser.parse_args()

    params = args.params
    dumper = args.dumper

    j = get_json(**params)
    js = json.dumps(j, ensure_ascii=False, indent=1)
    dumper(js)


def make_parser():
    from .exporthelpers.export_helper import Parser, setup_parser

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
    return parser


if __name__ == '__main__':
    main()
