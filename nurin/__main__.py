from nurin.cli import cli


def main() -> None:
    return cli(auto_envvar_prefix="NURIN")


if __name__ == "__main__":  # pragma: no cover
    main()
