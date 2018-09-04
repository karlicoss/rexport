from kython import JSONType

import praw # type: ignore

from typing import NamedTuple, List, Dict

class RedditBackup(NamedTuple):
    subreddits: List[JSONType]


class Backuper():
    def __init__(self, *args, **kwargs):
        self.r = praw.Reddit(user_agent="1111", *args, **kwargs)

    def extract_subreddits(self):
        def _iter():
            for i in self.r.user.subreddits(limit=None):
                sr = vars(i)
                del sr['_reddit']
                yield sr
        return list(_iter())

    def backup(self) -> RedditBackup:
        rb = RedditBackup(
            subreddits=self.extract_subreddits(),
        )
        return rb

