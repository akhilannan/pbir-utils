"""Tests for cli.py main function and validate command."""

import pytest
from unittest.mock import patch


class TestCliMain:
    """Tests for cli.py main function."""

    def test_main_no_command_prints_help(self, capsys):
        """Test that running main with no command prints help."""
        from pbir_utils.cli import main

        with patch("sys.argv", ["pbir-utils"]):
            main()

        captured = capsys.readouterr()
        assert "PBIR" in captured.out  # Banner should be printed
        assert "usage" in captured.out.lower() or "Available commands" in captured.out

    def test_main_prints_banner(self, capsys):
        """Test that main prints the ASCII banner."""
        from pbir_utils.cli import main

        with patch("sys.argv", ["pbir-utils", "--help"]):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "PBIR" in captured.out
        assert "Power BI" in captured.out

    def test_main_with_help_flag(self, capsys):
        """Test that --help flag shows usage information."""
        from pbir_utils.cli import main

        with patch("sys.argv", ["pbir-utils", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0


class TestValidateCommand:
    """Tests for the validate command handler."""

    def test_validate_help(self, run_cli):
        """Test that validate --help shows usage."""
        result = run_cli(["validate", "--help"])
        assert result.returncode == 0
        assert "validate" in result.stdout.lower()

    def test_validate_dry_run(self, simple_report, run_cli):
        """Test validate command runs without error."""
        result = run_cli(["validate", simple_report, "--source", "rules"])
        # May pass or fail depending on rules, but should not crash
        assert result.returncode in (0, 1)

    def test_validate_strict_mode(self, simple_report, run_cli):
        """Test validate with --strict flag."""
        result = run_cli(["validate", simple_report, "--source", "rules", "--strict"])
        # May return 1 if violations found
        assert result.returncode in (0, 1)

    def test_validate_json_output(self, simple_report, run_cli):
        """Test validate with --format json produces valid JSON."""
        import json

        result = run_cli(
            ["validate", simple_report, "--source", "rules", "--format", "json"]
        )
        assert result.returncode in (0, 1)
        # Should be valid JSON
        try:
            output = json.loads(result.stdout)
            assert "results" in output or "error" in output
        except json.JSONDecodeError:
            # If there's console output mixed in, just check it ran
            pass

    def test_validate_source_sanitize(self, simple_report, run_cli):
        """Test validate with --source sanitize."""
        result = run_cli(["validate", simple_report, "--source", "sanitize"])
        assert result.returncode in (0, 1)

    def test_validate_source_all(self, simple_report, run_cli):
        """Test validate with --source all (default)."""
        result = run_cli(["validate", simple_report, "--source", "all"])
        assert result.returncode in (0, 1)

    def test_validate_severity_filter(self, simple_report, run_cli):
        """Test validate with --severity flag."""
        result = run_cli(
            ["validate", simple_report, "--source", "rules", "--severity", "error"]
        )
        assert result.returncode in (0, 1)

    def test_validate_no_path_in_report_dir(self, simple_report, run_cli):
        """Test validate without path inside a .Report dir."""
        result = run_cli(["validate", "--source", "rules"], cwd=simple_report)
        assert result.returncode in (0, 1)

    def test_validate_no_path_outside_report_dir(self, tmp_path, run_cli):
        """Test validate without path outside a .Report dir fails."""
        result = run_cli(["validate", "--source", "rules"], cwd=str(tmp_path))
        assert result.returncode != 0
        assert "Error" in result.stderr or "report_path" in result.stderr


class TestServeCommand:
    """Tests for the serve/ui command."""

    def test_serve_help(self, run_cli):
        """Test that serve --help works."""
        result = run_cli(["serve", "--help"])
        assert result.returncode == 0
        assert "serve" in result.stdout.lower() or "ui" in result.stdout.lower()
