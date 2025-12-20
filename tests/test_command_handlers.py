"""Unit tests for CLI command handlers."""

import argparse
from unittest.mock import patch, MagicMock
import pytest

from pbir_utils.commands.sanitize import handle as handle_sanitize
from pbir_utils.commands.filters import (
    handle_update_filters,
    handle_sort_filters,
    handle_configure_filter_pane,
    handle_clear_filters,
)
from pbir_utils.commands.visualize import handle as handle_visualize


class TestSanitizeHandler:
    """Tests for the sanitize command handler."""

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.sanitize_config.load_config")
    @patch("pbir_utils.pbir_report_sanitizer.sanitize_powerbi_report")
    def test_handle_sanitize_basic(self, mock_sanitize, mock_load_config, mock_resolve):
        """Test basic sanitization handler flow."""
        mock_resolve.return_value = "dummy/path"
        mock_config = MagicMock()
        mock_config.definitions = {"action1": MagicMock()}
        mock_config.get_action_names.return_value = ["action1"]
        mock_load_config.return_value = mock_config

        args = argparse.Namespace(
            report_path="dummy/path",
            config=None,
            actions=None,
            exclude=None,
            include=None,
            dry_run=True,
            summary=False,
        )

        handle_sanitize(args)

        mock_resolve.assert_called_with("dummy/path")
        mock_load_config.assert_called()
        mock_sanitize.assert_called_once()

        # Verify call arguments
        call_args = mock_sanitize.call_args
        assert call_args[0][0] == "dummy/path"
        run_config = call_args[1]["config"]
        assert run_config.options["dry_run"] is True

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.sanitize_config.load_config")
    @patch("pbir_utils.pbir_report_sanitizer.sanitize_powerbi_report")
    @patch("pbir_utils.commands.sanitize.console")
    def test_handle_sanitize_with_actions(
        self, mock_console, mock_sanitize, mock_load_config, mock_resolve
    ):
        """Test sanitization handler with specific actions."""
        from pbir_utils.sanitize_config import ActionSpec

        mock_resolve.return_value = "dummy/path"
        mock_config = MagicMock()
        mock_config.definitions = {
            "a1": ActionSpec(name="a1", implementation="a1"),
            "a2": ActionSpec(name="a2", implementation="a2"),
        }
        mock_load_config.return_value = mock_config

        args = argparse.Namespace(
            report_path="dummy/path",
            config=None,
            actions=["a1", "unknown"],
            exclude=None,
            include=None,
            dry_run=False,
            summary=True,
        )

        handle_sanitize(args)

        mock_console.print_warning.assert_called_with(
            "Unknown action 'unknown' will be skipped."
        )
        mock_sanitize.assert_called_once()
        run_config = mock_sanitize.call_args[1]["config"]
        assert [a.name for a in run_config.actions] == ["a1"]

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.sanitize_config.load_config")
    @patch("pbir_utils.pbir_report_sanitizer.sanitize_powerbi_report")
    def test_handle_sanitize_exclude_include(
        self, mock_sanitize, mock_load_config, mock_resolve
    ):
        """Test sanitization handler with exclude and include."""
        from pbir_utils.sanitize_config import ActionSpec

        mock_resolve.return_value = "dummy/path"
        mock_config = MagicMock()
        mock_config.definitions = {
            "a1": ActionSpec(name="a1"),
            "a2": ActionSpec(name="a2"),
            "a3": ActionSpec(name="a3"),
        }
        mock_config.get_action_names.return_value = ["a1", "a2"]
        mock_load_config.return_value = mock_config

        args = argparse.Namespace(
            report_path="dummy/path",
            config=None,
            actions=None,
            exclude=["a1"],
            include=["a3"],
            dry_run=False,
            summary=False,
        )

        handle_sanitize(args)

        run_config = mock_sanitize.call_args[1]["config"]
        action_names = [a.name for a in run_config.actions]
        assert "a1" not in action_names
        assert "a2" in action_names
        assert "a3" in action_names

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.sanitize_config.load_config")
    @patch("pbir_utils.commands.sanitize.console")
    @patch("sys.exit")
    def test_handle_sanitize_invalid_config(
        self, mock_exit, mock_console, mock_load_config, mock_resolve
    ):
        """Test sanitization handler with invalid config file."""
        mock_resolve.return_value = "path"
        mock_load_config.side_effect = Exception("Invalid YAML")

        args = argparse.Namespace(
            report_path="path",
            config="invalid.yaml",
            actions=None,
            exclude=None,
            include=None,
            dry_run=False,
            summary=False,
        )

        with pytest.raises(Exception):
            handle_sanitize(args)


class TestFiltersHandlers:
    """Tests for filter-related command handlers."""

    @patch("pbir_utils.filter_utils.update_report_filters")
    @patch("pbir_utils.commands.filters.parse_json_arg")
    def test_handle_update_filters(self, mock_parse_json, mock_update):
        """Test update-filters handler."""
        mock_parse_json.return_value = [{"Table": "T1"}]
        args = argparse.Namespace(
            report_path="path",
            filters="json",
            reports=["R1"],
            dry_run=True,
            summary=True,
        )

        handle_update_filters(args)

        mock_update.assert_called_once_with(
            "path",
            filters=[{"Table": "T1"}],
            reports=["R1"],
            dry_run=True,
            summary=True,
        )

    @patch("pbir_utils.filter_utils.sort_report_filters")
    def test_handle_sort_filters(self, mock_sort):
        """Test sort-filters handler."""
        args = argparse.Namespace(
            report_path="path",
            reports=None,
            sort_order="Ascending",
            custom_order=["C1"],
            dry_run=False,
            summary=False,
        )

        handle_sort_filters(args)

        mock_sort.assert_called_once_with(
            "path",
            reports=None,
            sort_order="Ascending",
            custom_order=["C1"],
            dry_run=False,
            summary=False,
        )

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.filter_utils.configure_filter_pane")
    def test_handle_configure_filter_pane(self, mock_config, mock_resolve):
        """Test configure-filter-pane handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="input/path",
            visible=False,
            expanded=True,
            dry_run=True,
            summary=False,
        )

        handle_configure_filter_pane(args)

        mock_config.assert_called_once_with(
            "resolved/path", visible=False, expanded=True, dry_run=True, summary=False
        )

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.filter_utils.clear_filters")
    def test_handle_clear_filters(self, mock_clear, mock_resolve):
        """Test clear-filters handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="path",
            page="Page 1",
            visual=True,
            table=["T1"],
            column=None,
            field=None,
            dry_run=False,
            summary=True,
        )

        handle_clear_filters(args)

        mock_clear.assert_called_once_with(
            "resolved/path",
            show_page_filters=False,
            show_visual_filters=True,
            target_page="Page 1",
            target_visual=None,
            include_tables=["T1"],
            include_columns=None,
            include_fields=None,
            dry_run=False,
            summary=True,
        )

    @patch("pbir_utils.common.resolve_report_path")
    @patch("sys.exit")
    def test_handle_clear_filters_invalid_path(self, mock_exit, mock_resolve):
        """Test clear-filters handler with invalid report path."""
        mock_resolve.side_effect = SystemExit(1)
        args = argparse.Namespace(
            report_path="invalid",
            page=None,
            visual=None,
            table=None,
            column=None,
            field=None,
            dry_run=False,
            summary=False,
        )

        with pytest.raises(SystemExit):
            handle_clear_filters(args)


class TestMeasuresHandlers:
    """Tests for measure-related command handlers."""

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.pbir_measure_utils.remove_measures")
    def test_handle_remove_measures(self, mock_remove, mock_resolve):
        """Test remove-measures handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="path",
            measure_names=["M1"],
            check_visual_usage=False,
            dry_run=True,
            summary=False,
        )

        from pbir_utils.commands.measures import handle_remove_measures

        handle_remove_measures(args)

        mock_remove.assert_called_once_with(
            "resolved/path",
            measure_names=["M1"],
            check_visual_usage=False,
            dry_run=True,
            summary=False,
        )

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.pbir_measure_utils.generate_measure_dependencies_report")
    def test_handle_measure_dependencies(self, mock_gen, mock_resolve):
        """Test measure-dependencies handler."""
        mock_resolve.return_value = "resolved/path"
        mock_gen.return_value = "report content"
        args = argparse.Namespace(
            report_path="path", measure_names=None, include_visual_ids=True
        )

        from pbir_utils.commands.measures import handle_measure_dependencies

        with patch("builtins.print") as mock_print:
            handle_measure_dependencies(args)
            mock_print.assert_called_with("report content")

        mock_gen.assert_called_once_with(
            "resolved/path", measure_names=None, include_visual_ids=True
        )


class TestPagesHandlers:
    """Tests for page-related command handlers."""

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.page_utils.set_page_display_option")
    def test_handle_set_display_option(self, mock_set, mock_resolve):
        """Test set-display-option handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="path",
            option="FitToWidth",
            page="Trends",
            dry_run=False,
            summary=True,
        )

        from pbir_utils.commands.pages import handle_set_display_option

        handle_set_display_option(args)

        mock_set.assert_called_once_with(
            "resolved/path",
            display_option="FitToWidth",
            page="Trends",
            dry_run=False,
            summary=True,
        )


class TestInteractionsHandlers:
    """Tests for interaction-related command handlers."""

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.visual_interactions_utils.disable_visual_interactions")
    def test_handle_interactions(self, mock_disable, mock_resolve):
        """Test disable-interactions handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="path",
            pages=["P1"],
            source_visual_ids=None,
            source_visual_types=["slicer"],
            target_visual_ids=None,
            target_visual_types=None,
            update_type="Insert",
            dry_run=True,
            summary=False,
        )

        from pbir_utils.commands.interactions import handle as handle_interactions

        handle_interactions(args)

        mock_disable.assert_called_once_with(
            "resolved/path",
            pages=["P1"],
            source_visual_ids=None,
            source_visual_types=["slicer"],
            target_visual_ids=None,
            target_visual_types=None,
            update_type="Insert",
            dry_run=True,
            summary=False,
        )


class TestOtherHandlers:
    """Tests for other command handlers (batch-update, extract-metadata)."""

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.pbir_processor.batch_update_pbir_project")
    def test_handle_batch_update(self, mock_batch, mock_resolve):
        """Test batch-update handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            directory_path="path", csv_path="map.csv", dry_run=False, summary=True
        )

        from pbir_utils.commands.batch_update import handle as handle_batch

        handle_batch(args)

        mock_batch.assert_called_once_with("path", "map.csv", dry_run=False)

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.pbir_processor.batch_update_pbir_project")
    @patch(
        "pbir_utils.commands.batch_update.add_dry_run_arg"
    )  # Just to have another mock
    def test_handle_batch_update_invalid_csv(self, mock_arg, mock_batch, mock_resolve):
        """Test batch-update handler behavior with missing CSV."""
        mock_resolve.return_value = "path"
        mock_batch.side_effect = FileNotFoundError("map.csv not found")
        args = argparse.Namespace(
            directory_path="path", csv_path="map.csv", dry_run=False, summary=False
        )

        from pbir_utils.commands.batch_update import handle as handle_batch

        with pytest.raises(FileNotFoundError):
            handle_batch(args)

    @patch("pbir_utils.common.resolve_report_path")
    @patch("pbir_utils.metadata_extractor.export_pbir_metadata_to_csv")
    def test_handle_extract_metadata(self, mock_export, mock_resolve):
        """Test extract-metadata handler."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(args=["path", "out.csv"], filters=None)

        from pbir_utils.commands.extract_metadata import handle as handle_extract

        handle_extract(args)

        mock_export.assert_called_once_with("path", "out.csv", filters=None)

    @patch("pbir_utils.commands.extract_metadata.console")
    @patch("sys.exit")
    def test_handle_extract_metadata_no_args(self, mock_exit, mock_console):
        """Test extract-metadata handler with no arguments."""
        args = argparse.Namespace(args=[], filters=None)
        from pbir_utils.commands.extract_metadata import handle as handle_extract

        handle_extract(args)
        mock_console.print_error.assert_called_with("Output path required.")
        mock_exit.assert_called_with(1)


class TestVisualizeHandler:
    """Tests for the visualize command handler."""

    @patch("pbir_utils.commands.visualize.resolve_report_path")
    @patch("pbir_utils.report_wireframe_visualizer.display_report_wireframes")
    def test_handle_visualize(self, mock_display, mock_resolve):
        """Test visualize handler flow."""
        mock_resolve.return_value = "resolved/path"
        args = argparse.Namespace(
            report_path="path",
            pages=["P1"],
            visual_types=None,
            visual_ids=None,
            show_hidden=True,
        )

        handle_visualize(args)

        mock_resolve.assert_called_with("path")
        mock_display.assert_called_once_with(
            "resolved/path",
            pages=["P1"],
            visual_types=None,
            visual_ids=None,
            show_hidden=True,
        )
