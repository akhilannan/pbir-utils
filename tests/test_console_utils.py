"""Tests for console_utils module."""

from unittest.mock import patch

from pbir_utils.console_utils import ConsoleUtils


class TestConsoleUtils:
    """Tests for ConsoleUtils class."""

    def test_init_should_use_colors_when_force_color(self):
        """Test that colors are enabled when FORCE_COLOR is set."""
        with patch.dict("os.environ", {"FORCE_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            assert console.use_colors is True

    def test_init_should_not_use_colors_when_no_color(self):
        """Test that colors are disabled when NO_COLOR is set."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            assert console.use_colors is False

    def test_no_color_takes_precedence_over_force_color(self):
        """Test that NO_COLOR takes precedence over FORCE_COLOR."""
        with patch.dict(
            "os.environ", {"NO_COLOR": "1", "FORCE_COLOR": "1"}, clear=False
        ):
            console = ConsoleUtils()
            assert console.use_colors is False

    def test_format_with_colors_disabled(self):
        """Test that _format returns plain text when colors are disabled."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            result = console._format("test", console.RED, console.BOLD)
            assert result == "test"

    def test_format_with_colors_enabled(self):
        """Test that _format includes ANSI codes when colors are enabled."""
        with patch.dict("os.environ", {"FORCE_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            result = console._format("test", console.RED, console.BOLD)
            assert console.BOLD in result
            assert console.RED in result
            assert console.RESET in result
            assert "test" in result

    def test_print_heading(self, capsys):
        """Test print_heading outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_heading("Test Heading")
            captured = capsys.readouterr()
            assert "Test Heading" in captured.out
            assert "-" * len("Test Heading") in captured.out

    def test_print_action_heading_dry_run(self, capsys):
        """Test print_action_heading with dry_run=True."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_action_heading("Test Action", dry_run=True)
            captured = capsys.readouterr()
            assert "Action: Test Action (Dry Run)" in captured.out

    def test_print_action_heading_no_dry_run(self, capsys):
        """Test print_action_heading with dry_run=False."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_action_heading("Test Action", dry_run=False)
            captured = capsys.readouterr()
            assert "Action: Test Action" in captured.out
            assert "(Dry Run)" not in captured.out

    def test_print_success(self, capsys):
        """Test print_success outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_success("Operation completed")
            captured = capsys.readouterr()
            assert "[OK]" in captured.out
            assert "Operation completed" in captured.out

    def test_print_warning(self, capsys):
        """Test print_warning outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_warning("Something might be wrong")
            captured = capsys.readouterr()
            assert "Warning:" in captured.out
            assert "Something might be wrong" in captured.out

    def test_print_error(self, capsys):
        """Test print_error outputs to stderr."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_error("Something went wrong")
            captured = capsys.readouterr()
            assert "Error:" in captured.err
            assert "Something went wrong" in captured.err

    def test_print_info(self, capsys):
        """Test print_info outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_info("Informational message")
            captured = capsys.readouterr()
            assert "[INFO]" in captured.out
            assert "Informational message" in captured.out

    def test_print_dry_run(self, capsys):
        """Test print_dry_run outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_dry_run("Would make changes")
            captured = capsys.readouterr()
            assert "[DRY RUN]" in captured.out
            assert "Would make changes" in captured.out

    def test_print_step(self, capsys):
        """Test print_step outputs with bullet."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_step("Step description")
            captured = capsys.readouterr()
            assert "•" in captured.out
            assert "Step description" in captured.out

    def test_print_separator(self, capsys):
        """Test print_separator outputs dashes."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_separator()
            captured = capsys.readouterr()
            assert "-" * 60 in captured.out

    def test_print_action(self, capsys):
        """Test print_action outputs expected format."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()
            console.print_action("Doing something")
            captured = capsys.readouterr()
            assert "Action:" in captured.out
            assert "Doing something" in captured.out

    def test_suppress_heading_context_manager(self, capsys):
        """Test that suppress_heading context manager suppresses headings."""
        with patch.dict("os.environ", {"NO_COLOR": "1"}, clear=False):
            console = ConsoleUtils()

            # Heading should print normally outside the context
            console.print_heading("Before Suppression")
            captured = capsys.readouterr()
            assert "Before Suppression" in captured.out

            # Heading should be suppressed inside the context
            with console.suppress_heading():
                console.print_heading("Suppressed Heading")
                captured = capsys.readouterr()
                assert "Suppressed Heading" not in captured.out

            # Heading should print normally after the context exits
            console.print_heading("After Suppression")
            captured = capsys.readouterr()
            assert "After Suppression" in captured.out
