import os
import sys
from contextlib import contextmanager


class ConsoleUtils:
    """
    Utility class for handling console output with ANSI colors.
    Respects NO_COLOR and FORCE_COLOR environment variables.
    """

    # ANSI Color Codes
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    def __init__(self):
        self.use_colors = self._should_use_colors()
        self._suppress_heading_output = False

    def _should_use_colors(self) -> bool:
        """
        Determine if colors should be used based on environment and TTY.
        """
        # 1. Respect NO_COLOR (https://no-color.org/)
        if os.environ.get("NO_COLOR"):
            return False

        # 2. Respect FORCE_COLOR
        if os.environ.get("FORCE_COLOR"):
            return True

        # 3. Check if stdout is a TTY
        # Azure DevOps and other CI systems might not be TTYs but often support colors.
        # Users can use FORCE_COLOR=1 in CI if detection fails.
        is_a_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

        # Windows 10/11 usually supports ANSI codes in the terminal now.
        # For older Windows or specific environments, colorama might be needed,
        # but we are sticking to standard ANSI for now as per plan.
        return is_a_tty

    def _format(self, text: str, color: str = "", style: str = "") -> str:
        if not self.use_colors:
            return text
        return f"{style}{color}{text}{self.RESET}"

    def print_heading(self, message: str):
        """Prints a bold, colored heading."""
        if self._suppress_heading_output:
            return
        print(f"\n{self._format(message, self.CYAN, self.BOLD)}")
        print(self._format("-" * len(message), self.CYAN, self.DIM))

    @contextmanager
    def suppress_heading(self):
        """Context manager to temporarily suppress heading output."""
        self._suppress_heading_output = True
        try:
            yield
        finally:
            self._suppress_heading_output = False

    def print_action_heading(self, action_name: str, dry_run: bool = False):
        """
        Prints a standardized action heading with optional dry run indicator.

        Args:
            action_name: Name of the action being performed.
            dry_run: Whether this is a dry run.
        """
        suffix = " (Dry Run)" if dry_run else ""
        self.print_heading(f"Action: {action_name}{suffix}")

    def print_action(self, message: str):
        """Prints an action message."""
        print(f"{self._format('Action:', self.BLUE, self.BOLD)} {message}")

    def print_success(self, message: str):
        """Prints a success message."""
        print(f"{self._format('[OK]', self.GREEN, self.BOLD)} {message}")

    def print_warning(self, message: str):
        """Prints a warning message."""
        print(f"{self._format('Warning:', self.YELLOW, self.BOLD)} {message}")

    def print_error(self, message: str):
        """Prints an error message."""
        print(
            f"{self._format('Error:', self.RED, self.BOLD)} {message}", file=sys.stderr
        )

    def print_info(self, message: str):
        """Prints a general info message."""
        print(f"{self._format('[INFO]', self.BLUE)} {message}")

    def print_dry_run(self, message: str):
        """Prints a dry run message."""
        print(f"{self._format('[DRY RUN]', self.YELLOW)} {message}")

    def print_step(self, message: str):
        """Prints a step within an action."""
        print(f"  • {message}")

    def print_separator(self):
        """Prints a separator line."""
        print(self._format("-" * 60, self.WHITE, self.DIM))

    def print_cleared(self, message: str):
        """Prints a cleared message."""
        print(f"{self._format('[Cleared]', self.GREEN, self.BOLD)} {message}")


# Global instance
console = ConsoleUtils()
