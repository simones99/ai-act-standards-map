from aasm import __version__
from aasm.cli import main


def test_version_flag_prints_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"aasm {__version__}"
