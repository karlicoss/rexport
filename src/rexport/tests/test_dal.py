import json
from pathlib import Path

import pytest

from ..dal import DAL


@pytest.mark.parametrize('what', ['saved', 'comments', 'submissions', 'upvoted', 'subreddits', 'multireddits'])
def test_collections_continue_after_bad_file(tmp_path: Path, what: str) -> None:
    rows = [{'id': key, 'path': key, 'created_utc': 0, 'title': key} for key in ['a', 'b', 'c']]
    first = tmp_path / 'first.json'
    first.write_text(json.dumps({what: rows[:2]}))
    broken = tmp_path / 'broken.json'
    broken.write_text('{')
    last = tmp_path / 'last.json'
    last.write_text(json.dumps({what: rows[1:]}))

    [a, b, error, c] = getattr(DAL([first, broken, last]), what)()
    assert isinstance(error, Exception)
    assert [x.raw for x in (a, b, c)] == rows
