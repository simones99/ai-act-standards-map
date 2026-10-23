from aasm import __version__
from aasm.cli import main


def test_version_flag_prints_version(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"aasm {__version__}"


def test_check_command_exit_code(curated_ok, curated_copy, capsys):
    assert main(["check", "--curated", str(curated_ok)]) == 0
    (curated_copy / "deadlines.csv").unlink()
    assert main(["check", "--curated", str(curated_copy)]) == 1
    assert "deadlines.csv: missing" in capsys.readouterr().out
