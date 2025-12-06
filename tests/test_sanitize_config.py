"""Tests for sanitize_config module."""

from unittest.mock import patch


from pbir_utils.sanitize_config import (
    ActionSpec,
    SanitizeConfig,
    load_config,
    find_user_config,
    get_default_config_path,
    _merge_configs,
)


class TestActionSpec:
    """Tests for ActionSpec dataclass."""

    def test_from_definition_implicit(self):
        """Test creating ActionSpec from implicit definition (empty dict)."""
        spec = ActionSpec.from_definition("remove_unused_measures", {})
        assert spec.name == "remove_unused_measures"
        assert spec.func_name == "remove_unused_measures"
        assert spec.params == {}

    def test_from_definition_explicit(self):
        """Test creating ActionSpec from explicit definition with implementation."""
        spec = ActionSpec.from_definition(
            "hide_tooltip_pages",
            {
                "implementation": "hide_pages_by_type",
                "params": {"page_type": "Tooltip"},
            },
        )
        assert spec.name == "hide_tooltip_pages"
        assert spec.func_name == "hide_pages_by_type"
        assert spec.params == {"page_type": "Tooltip"}

    def test_from_definition_none(self):
        """Test creating ActionSpec from None definition (same as implicit)."""
        spec = ActionSpec.from_definition("cleanup_invalid_bookmarks", None)
        assert spec.name == "cleanup_invalid_bookmarks"
        assert spec.func_name == "cleanup_invalid_bookmarks"


class TestSanitizeConfig:
    """Tests for SanitizeConfig dataclass."""

    def test_default_values(self):
        """Test default property values."""
        config = SanitizeConfig(actions=[ActionSpec("test", "test")], options={})
        assert config.dry_run is False
        assert config.summary is False

    def test_options_override(self):
        """Test that options override defaults."""
        config = SanitizeConfig(
            actions=[ActionSpec("test", "test")],
            options={"dry_run": True, "summary": True},
        )
        assert config.dry_run is True
        assert config.summary is True

    def test_get_action_names(self):
        """Test get_action_names method."""
        config = SanitizeConfig(
            actions=[ActionSpec("a", "a"), ActionSpec("b", "b")], options={}
        )
        assert config.get_action_names() == ["a", "b"]

    def test_get_additional_actions(self):
        """Test get_additional_actions method."""
        config = SanitizeConfig(
            actions=[ActionSpec("a", "a")],
            definitions={"a": ActionSpec("a", "a"), "b": ActionSpec("b", "b")},
            options={},
        )
        assert config.get_additional_actions() == ["b"]


class TestFindUserConfig:
    """Tests for find_user_config."""

    def test_no_config_found(self, tmp_path):
        """Test when no config file exists."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_config(str(tmp_path))
        assert result is None

    def test_cwd_config(self, tmp_path):
        """Test finding config in current working directory."""
        config_path = tmp_path / "pbir-sanitize.yaml"
        config_path.write_text("actions:\\n  - test_action")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_config()

        assert result == config_path

    def test_report_path_config(self, tmp_path):
        """Test finding config in report folder."""
        report_path = tmp_path / "report"
        report_path.mkdir()
        config_path = report_path / "pbir-sanitize.yaml"
        config_path.write_text("actions:\\n  - test_action")

        cwd = tmp_path / "different"
        cwd.mkdir()

        with patch("pathlib.Path.cwd", return_value=cwd):
            result = find_user_config(str(report_path))

        assert result == config_path


class TestGetDefaultConfigPath:
    """Tests for get_default_config_path."""

    def test_returns_path(self):
        """Test that default config path is returned."""
        path = get_default_config_path()
        assert path.name == "sanitize.yaml"
        assert "defaults" in str(path)

    def test_default_exists(self):
        """Test that default config file exists."""
        path = get_default_config_path()
        assert path.exists()


class TestMergeConfigs:
    """Tests for _merge_configs."""

    def test_definitions_merge(self):
        """Test that definitions are merged correctly."""
        default = {
            "definitions": {"action1": {}, "action2": {}},
            "actions": ["action1", "action2"],
            "options": {},
        }
        user = {
            "definitions": {
                "action1": {"implementation": "custom_func", "params": {"key": "value"}}
            }
        }

        config = _merge_configs(default, user)

        # action1 should have custom implementation
        action1 = config.definitions["action1"]
        assert action1.func_name == "custom_func"
        assert action1.params == {"key": "value"}

        # action2 should have default (implicit) implementation
        action2 = config.definitions["action2"]
        assert action2.func_name == "action2"

    def test_user_actions_replace(self):
        """Test that user actions list replaces defaults."""
        default = {
            "definitions": {"a": {}, "b": {}, "c": {}},
            "actions": ["a", "b"],
            "options": {},
        }
        user = {"actions": ["c"]}

        config = _merge_configs(default, user)

        action_names = [a.name for a in config.actions]
        assert action_names == ["c"]

    def test_user_include(self):
        """Test that include appends to actions."""
        default = {
            "definitions": {"a": {}, "b": {}},
            "actions": ["a"],
            "options": {},
        }
        user = {"include": ["b"]}

        config = _merge_configs(default, user)

        action_names = [a.name for a in config.actions]
        assert "a" in action_names
        assert "b" in action_names

    def test_user_exclude(self):
        """Test that exclude removes actions."""
        default = {
            "definitions": {"action1": {}, "action2": {}, "action3": {}},
            "actions": ["action1", "action2", "action3"],
            "options": {},
        }
        user = {"exclude": ["action2"]}

        config = _merge_configs(default, user)

        action_names = [a.name for a in config.actions]
        assert "action1" in action_names
        assert "action2" not in action_names
        assert "action3" in action_names


class TestLoadConfig:
    """Tests for load_config."""

    def test_load_default_only(self, tmp_path):
        """Test loading only default config when no user config exists."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            config = load_config(report_path=str(tmp_path))

        assert len(config.actions) > 0
        assert config.dry_run is False

    def test_load_explicit_path(self, tmp_path):
        """Test loading config from explicit path."""
        config_file = tmp_path / "custom.yaml"
        config_file.write_text(
            """
definitions:
  set_page_size:
    implementation: set_page_size
    params:
      width: 1920
actions:
  - set_page_size
options:
  dry_run: true
"""
        )

        config = load_config(config_path=str(config_file))

        # Check custom action
        set_page = next(a for a in config.actions if a.name == "set_page_size")
        assert set_page.params == {"width": 1920}
        assert config.dry_run is True
