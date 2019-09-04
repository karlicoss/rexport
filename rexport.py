#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
from typing import NamedTuple, List, Dict

# pip install praw
import praw # type: ignore
from praw.models import Redditor, Subreddit, Submission, Comment, Multireddit # type: ignore


class RedditData(NamedTuple):
    profile: Dict
    multireddits: List[Dict]
    subreddits: List[Dict]
    saved: List[Dict]
    upvoted: List[Dict]
    downvoted: List[Dict]
    comments: List[Dict]
    submissions: List[Dict]


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
        )
        return rb._asdict()


AUTH_PARAMS = ['username', 'password', 'client_id', 'client_secret']

def get_json(**params):
    return Exporter(**params).export()


def main():
    p = argparse.ArgumentParser("Tool to export your personal reddit data")
    p.add_argument('--secrets', type=Path, required=False, help=f'.py file containing {", ".join(AUTH_PARAMS)} variables')
    p.add_argument('path', type=Path, nargs='?', help='Optional path to backup, otherwise will be printed to stdout')
    gr = p.add_argument_group('API parameters')
    for param in AUTH_PARAMS:
        gr.add_argument('--' + param, type=str)
    args = p.parse_args()

    secrets_file = args.secrets
    if secrets_file is not None:
        obj = {} # type: ignore
        exec(secrets_file.read_text(), {}, obj)
    else:
        obj = vars(args)

    kwargs = {k: obj[k] for k in AUTH_PARAMS}
    j = get_json(**kwargs)
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
