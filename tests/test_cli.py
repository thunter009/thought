import pytest
from click.testing import CliRunner

from thought.cli import cli


def test_cli_help():
    """
    Integration Test: thought --help
    """
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "--help",
        ],
    )

    assert (
        "\n  --help                          Show this message and exit.\n"
        in result.output
    )
    assert result.exit_code == 0
