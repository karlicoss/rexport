import argparse
from typing import Sequence
from pathlib import Path


def setup_parser(parser: argparse.ArgumentParser, params: Sequence[str]):
    class ReadParamsAction(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            secrets_file = values
            obj = {} # type: ignore

            # we control the file with secrets so exec is fine
            exec(secrets_file.read_text(), {}, obj)

            for p in params:
                setattr(namespace, p, obj[p])

    parser.add_argument(
        '--secrets',
        type=Path,
        action=ReadParamsAction,
        required=False,
        help=f'.py file containing {", ".join(params)} variables',
    )
    gr = parser.add_argument_group('API parameters')
    for param in params:
        gr.add_argument('--' + param, type=str)

    parser.add_argument(
        'path',
        type=Path,
        nargs='?',
        help='Optional path to backup, otherwise will be printed to stdout',
    )



# TODO need other function to extract path? not sure what would be the proper way..
# TODO construct a callback?
