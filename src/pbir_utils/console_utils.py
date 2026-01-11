import os
import re
import sys
from contextlib import contextmanager
from queue import Queue
import logging


# Global logger
logger = logging.getLogger(__name__)


class ConsoleUtils:
    """
    Utility class for handling console output with ANSI colors.
    Respects NO_COLOR and FORCE_COLOR environment variables.

    Supports broadcasting messages to SSE queues for UI streaming.
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
        self._suppress_external = False  # Suppresses external SSE broadcasts
        self._internal_queues: list[Queue] = []  # For internal capture (rule_engine)
        self._external_queues: list[Queue] = []  # For SSE streaming (API)

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

    def _strip_ansi(self, text: str) -> str:
        """Strip ANSI escape codes from text for SSE broadcasts."""
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def _broadcast(self, msg_type: str, message: str) -> None:
        """Broadcast message to all connected queues."""
        # Strip ANSI codes for HTML display
        clean_message = self._strip_ansi(message)
        msg = {"type": msg_type, "message": clean_message}

        # Internal queues always receive (for capture_output in rule_engine)
        for q in self._internal_queues:
            try:
                q.put_nowait(msg)
            except Exception:  # nosec B110
                pass

        # External queues (SSE) are suppressed during suppress_all()
        if not self._suppress_external:
            for q in self._external_queues:
                try:
                    q.put_nowait(msg)
                except Exception:  # nosec B110
                    pass

    @contextmanager
    def capture_output(self):
        """
        Internal capture for collecting messages (e.g., for violation details).
        These queues receive messages even during suppress_all().
        """
        q: Queue = Queue()
        self._internal_queues.append(q)
        try:
            yield q
        finally:
            self._internal_queues.remove(q)

    @contextmanager
    def stream_output(self):
        """
        External SSE streaming output.
        These queues are silenced during suppress_all() so SSE matches CLI.
        """
        q: Queue = Queue()
        self._external_queues.append(q)
        try:
            yield q
        finally:
            self._external_queues.remove(q)

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
        self._broadcast("heading", message)

    @contextmanager
    def suppress_heading(self):
        """Context manager to temporarily suppress heading output."""
        self._suppress_heading_output = True
        try:
            yield
        finally:
            self._suppress_heading_output = False

    @contextmanager
    def suppress_all(self):
        """
        Suppress console output (stdout/stderr) and external SSE broadcasts.
        Internal capture queues still receive messages for violation collection.
        """
        import io

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        self._suppress_external = True
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self._suppress_external = False

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
        self._broadcast("action", message)

    def print_success(self, message: str):
        """Prints a success message."""
        print(f"{self._format('[OK]', self.GREEN, self.BOLD)} {message}")
        self._broadcast("success", message)

    def print_warning(self, message: str):
        """Prints a warning message."""
        print(f"{self._format('Warning:', self.YELLOW, self.BOLD)} {message}")
        self._broadcast("warning", message)

    def print_error(self, message: str):
        """Prints an error message."""
        print(
            f"{self._format('Error:', self.RED, self.BOLD)} {message}", file=sys.stderr
        )
        self._broadcast("error", message)

    def print_info(self, message: str):
        """Prints a general info message."""
        print(f"{self._format('[INFO]', self.BLUE)} {message}")
        self._broadcast("info", message)

    def print_dry_run(self, message: str):
        """Prints a dry run message."""
        print(f"{self._format('[DRY RUN]', self.YELLOW)} {message}")
        self._broadcast("dry_run", message)

    def print_step(self, message: str):
        """Prints a step within an action."""
        print(f"  • {message}")
        self._broadcast("step", message)

    def print_separator(self):
        """Prints a separator line."""
        print(self._format("-" * 60, self.WHITE, self.DIM))

    def print_cleared(self, message: str):
        """Prints a cleared message."""
        print(f"{self._format('[Cleared]', self.GREEN, self.BOLD)} {message}")
        self._broadcast("cleared", message)

    def print_pass(self, message: str):
        """Prints a pass message (green checkmark)."""
        print(f"{self._format('✓', self.GREEN)} {message}")
        self._broadcast("pass", message)

    def print(self, message: str):
        """Prints a plain message."""
        print(message)
        self._broadcast("message", message)


# Global instance
console = ConsoleUtils()
