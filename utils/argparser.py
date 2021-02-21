from argparse import ArgumentParser

parser = ArgumentParser()

parser.add_argument(
    "-w","--workers",
    default=50,
    type=int,
    help="Determines the number of workers."
    )

parser.add_argument(
    "-d","--debug",
    action="store_const",
    const=True,
    default=False,
    help="Launches in debug mode if present."
    )

parser.add_argument(
    "-l","--log",
    default="INFO",
    choices=["DEBUG","INFO"],
    help="Sets the logging level."
)
