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

    def test_from_string(self):
        """Test creating ActionSpec from string."""
        spec = ActionSpec.from_config("remove_unused_measures")
        assert spec.name == "remove_unused_measures"
        assert spec.params == {}

    def test_from_dict_simple(self):
        """Test creating ActionSpec from dict without params."""
        spec = ActionSpec.from_config({"name": "remove_unused_measures"})
        assert spec.name == "remove_unused_measures"
        assert spec.params == {}

    def test_from_dict_with_params(self):
        """Test creating ActionSpec from dict with params."""
        spec = ActionSpec.from_config(
            {"name": "set_page_size", "params": {"width": 1920, "height": 1080}}
        )
        assert spec.name == "set_page_size"
        assert spec.params == {"width": 1920, "height": 1080}


class TestSanitizeConfig:
    """Tests for SanitizeConfig dataclass."""

    def test_default_values(self):
        """Test default property values."""
        config = SanitizeConfig(actions=[ActionSpec("test")], options={})
        assert config.dry_run is False
        assert config.summary is False

    def test_options_override(self):
        """Test that options override defaults."""
        config = SanitizeConfig(
            actions=[ActionSpec("test")], options={"dry_run": True, "summary": True}
        )
        assert config.dry_run is True
        assert config.summary is True


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
        config_path.write_text("actions:\n  - test_action")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_config()

        assert result == config_path

    def test_report_path_config(self, tmp_path):
        """Test finding config in report folder."""
        report_path = tmp_path / "report"
        report_path.mkdir()
        config_path = report_path / "pbir-sanitize.yaml"
        config_path.write_text("actions:\n  - test_action")

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

    def test_user_override(self):
        """Test that user config overrides defaults."""
        default = {"actions": ["action1", "action2"], "options": {"dry_run": False}}
        user = {
            "actions": [{"name": "action1", "params": {"key": "value"}}],
            "options": {"dry_run": True},
        }

        config = _merge_configs(default, user)

        # action1 should have params
        action1 = next(a for a in config.actions if a.name == "action1")
        assert action1.params == {"key": "value"}

        # dry_run should be True
        assert config.dry_run is True

    def test_user_exclude(self):
        """Test that exclude removes actions."""
        default = {"actions": ["action1", "action2", "action3"], "options": {}}
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
actions:
  - name: set_page_size
    params:
      width: 1920
options:
  dry_run: true
"""
        )

        config = load_config(config_path=str(config_file))

        # Check custom action
        set_page = next(a for a in config.actions if a.name == "set_page_size")
        assert set_page.params == {"width": 1920}
        assert config.dry_run is True
