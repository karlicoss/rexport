from typing import NamedTuple, List, Dict

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
        self.api = praw.Reddit(user_agent="1111", *args, **kwargs)

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
