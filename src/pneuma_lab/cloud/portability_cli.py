"""Warning-free module entry point for the receipt portability gate."""

from .portability import main


if __name__ == "__main__":
    raise SystemExit(main())
