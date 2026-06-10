import argparse
import sys
from .server import run


def main():
    parser = argparse.ArgumentParser(
        prog="mdserve",
        description="A beautiful local file server with Markdown rendering",
    )
    parser.add_argument(
        "port",
        nargs="?",
        type=int,
        default=2112,
        help="Port to listen on (default: 2112)",
    )
    parser.add_argument(
        "--bind", "-b",
        default="",
        metavar="ADDRESS",
        help="Bind address (default: all interfaces)",
    )
    args = parser.parse_args()
    run(args.port, args.bind)


if __name__ == "__main__":
    main()
