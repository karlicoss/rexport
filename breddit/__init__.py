from kython import JSONType

import praw # type: ignore
from praw.models import Redditor, Subreddit, Submission, Comment, Multireddit # type: ignore

from typing import NamedTuple, List, Dict

def get_logger():
    import logging
    return logging.getLogger('reddit-backup')

class RedditBackup(NamedTuple):
    profile: Dict
    subreddits: List[Dict]
    multireddits: List[Dict]
    upvoted: List[Dict]
    downvoted: List[Dict]
    saved: List[Dict]
    comments: List[Dict]
    submissions: List[Dict]
    version: int = 1


def cleanup(d):
    del d['_reddit']
    return d

def expand(d):
    if isinstance(d, (str, float, int, bool, type(None))):
        return d

    if isinstance(d, list):
        return [expand(x) for x in d]

    if isinstance(d, dict):
        return {k: expand(v) for k, v in d.items()}

    if isinstance(d, Redditor): # TODO eh, hopefully it can't go into infinite loop...
        return expand(vars(d))

    if isinstance(d, Subreddit):
        return expand(vars(d))

    if isinstance(d, Multireddit):
        return expand(vars(d))

    if isinstance(d, Submission):
        return expand(vars(d)) # TODO carefully, not sure we need all of it...

    if isinstance(d, Comment):
        return expand(vars(d)) # TODO carefully, not sure we need all of it...

    if isinstance(d, praw.Reddit):
        return None

    raise RuntimeError(f"Unexpected type: {type(d)}")


class Backuper():
    def __init__(self, *args, **kwargs):
        self.r = praw.Reddit(user_agent="1111", *args, **kwargs)

    def _redditor(self):
        return self.r.redditor('karlicoss') # TODO extract from config?

    def extract_subreddits(self) -> List[Dict]:
        return [expand(i) for i in self.r.user.subreddits(limit=None)]

    def extract_multireddits(self) -> List[Dict]:
        return [expand(i) for i in self.r.user.multireddits()]

    def extract_profile(self) -> Dict:
        return expand(self.r.user.me())

    def _extract_redditor_stuff(self, thing: str) -> List[Dict]:
        return [expand(i) for i in getattr(self._redditor(), thing)(limit=None)]

    def extract_upvoted(self) -> List[Dict]:
        return self._extract_redditor_stuff('upvoted')

    def extract_downvoted(self) -> List[Dict]:
        return self._extract_redditor_stuff('downvoted')

    def extract_comments(self) -> List[Dict]:
        return [expand(i) for i in self._redditor().comments.new(limit=None)]

    def extract_saved(self) -> List[Dict]:
        return self._extract_redditor_stuff('saved')

    def extract_submissions(self) -> List[Dict]:
        return [expand(i) for i in self._redditor().submissions.new(limit=None)]

    def backup(self) -> RedditBackup:
        rb = RedditBackup(
            subreddits=self.extract_subreddits(),
            multireddits=self.extract_multireddits(),
            profile=self.extract_profile(),
            upvoted=self.extract_upvoted(),
            downvoted=self.extract_downvoted(),
            saved=self.extract_saved(),
            submissions=self.extract_submissions(),
            comments=self.extract_comments(),
        )
        return rb

