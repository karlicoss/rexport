#!/bin/bash

cd "$(this_dir)" || exit

. ~/bash_ci

ci_run mypy breddit
ci_run pylint -E breddit

ci_report_errors
