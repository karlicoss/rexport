#!/usr/bin/env python3
import argparse
from pathlib import Path

import breddit


def main():
    params = ['username', 'password', 'client_id', 'client_secret']
    p = argparse.ArgumentParser("Tool to export your personal reddit data")
    p.add_argument('--secrets', type=Path, required=False, help=f'.py file containing {", ".join(params)} variables')
    gr = p.add_argument_group('API parameters')
    for param in params:
        gr.add_argument('--' + param, type=str)
    args = p.parse_args()

    secrets_file = args.secrets
    if secrets_file is not None:
        obj = {} # type: ignore
        exec(secrets_file.read_text(), {}, obj)
    else:
        obj = args
    kwargs = {k: obj[k] for k in params}

    exporter = breddit.Exporter(**kwargs)
    json = exporter.export()

    # TODO support automatic compression?
    print(json.keys()) # TODO --debug?


if __name__ == '__main__':
    main()

# ./run --secrets path-to-secrets.py
