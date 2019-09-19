#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
from typing import NamedTuple, List, Dict

# pip install praw
import praw # type: ignore
from praw.models import Redditor, Subreddit, Submission, Comment, Multireddit, Message # type: ignore


class RedditData(NamedTuple):
    profile: Dict
    multireddits: List[Dict]
    subreddits: List[Dict]
    saved: List[Dict]
    upvoted: List[Dict]
    downvoted: List[Dict]
    comments: List[Dict]
    submissions: List[Dict]
    inbox: List[Dict]


IGNORED_KEYS = {
    'body_html',
    'selftext_html',
    'description_html',
    'preview',
}

# sadly praw doesn't keep raw json data :( https://github.com/praw-dev/praw/issues/830
def jsonify(d):
    if isinstance(d, (str, float, int, bool, type(None))):
        return d

    if isinstance(d, list):
        return [jsonify(x) for x in d]

    if isinstance(d, dict):
        return {k: jsonify(v) for k, v in d.items() if k not in IGNORED_KEYS}

    if isinstance(d, (
            Redditor,
            Subreddit,
            Multireddit,
            Submission,
            Comment,
            Message,
    )): # TODO eh, hopefully it can't go into infinite loop...
        return jsonify(vars(d))

    if isinstance(d, praw.Reddit):
        return None

    raise RuntimeError(f"Unexpected type: {type(d)}")


def _extract(from_, **kwargs) -> List[Dict]:
    return jsonify(list(from_(**kwargs)))


class Exporter:
    def __init__(self, *args, **kwargs):
        self.api = praw.Reddit(user_agent="rexport", *args, **kwargs)

    @property
    def _me(self):
        return self.api.user.me()

    def extract_profile(self) -> Dict:
        return jsonify(self._me)

    def export(self):
        rb = RedditData(
            profile     =self.extract_profile(),
            multireddits=_extract(self.api.user.multireddits), # weird, multireddits has no limit
            subreddits  =_extract(self.api.user.subreddits, limit=None),
            saved       =_extract(self._me.saved          , limit=None),
            upvoted     =_extract(self._me.upvoted        , limit=None),
            downvoted   =_extract(self._me.downvoted      , limit=None),
            comments    =_extract(self._me.comments.new   , limit=None),
            submissions =_extract(self._me.submissions.new, limit=None),
            inbox       =_extract(self.api.inbox.all      , limit=None),
        )
        return rb._asdict()


def get_json(**params):
    return Exporter(**params).export()


def main():
    from export_helper import setup_parser
    parser = argparse.ArgumentParser("Tool to export your personal reddit data")
    setup_parser(parser=parser, params=['username', 'password', 'client_id', 'client_secret'])
    args = parser.parse_args()

    params = args.params

    j = get_json(**params)
    def dump(fo):
        json.dump(j, fo, ensure_ascii=False, indent=1)

    if args.path is not None:
        with args.path.open('w') as fo:
            dump(fo)
        print(f'saved data to {args.path}', file=sys.stderr)
    else:
        dump(sys.stdout)

if __name__ == '__main__':
    main()
