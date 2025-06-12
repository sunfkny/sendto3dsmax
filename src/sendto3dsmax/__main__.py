import argparse

from sendto3dsmax import send


class ArgsNamespace(argparse.Namespace):
    file: str


def main() -> None:
    parser = argparse.ArgumentParser(description="Send script to 3ds Max listener.")
    parser.add_argument("file", nargs="?", help="Path to script file (.ms/.py)")
    args = parser.parse_args(namespace=ArgsNamespace())

    send(args.file)


if __name__ == "__main__":
    main()
