import argparse

from sendto3dsmax import send


class ArgsNamespace(argparse.Namespace):
    files: list[str]
    pid: int | None = None
    timeout: float = 60


def main() -> None:
    parser = argparse.ArgumentParser(description="Send script to 3ds Max listener.")
    parser.add_argument("file", nargs="+", help="Path to script file (.ms/.py)")
    parser.add_argument(
        "-p", "--pid", type=int, default=None, help="Process ID of 3ds Max"
    )
    parser.add_argument(
        "-t", "--timeout", type=float, default=60, help="Timeout in seconds"
    )
    args = parser.parse_args(namespace=ArgsNamespace())
    send(pid=args.pid, files=args.files, timeout=args.timeout)


if __name__ == "__main__":
    main()
