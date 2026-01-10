"""Tests for rule_config module."""

from unittest.mock import patch

from pbir_utils.rule_config import (
    RuleSpec,
    RulesConfig,
    load_rules,
    find_user_rules,
    _merge_configs,
)


class TestRuleSpec:
    """Tests for RuleSpec dataclass."""

    def test_from_definition_minimal(self):
        """Test creating RuleSpec from minimal definition (None)."""
        spec = RuleSpec.from_definition("remove_unused_bookmarks", None)
        assert spec.id == "remove_unused_bookmarks"
        assert spec.severity == "warning"
        assert spec.expression is None
        assert spec.is_expression_rule is False

    def test_from_definition_empty_dict(self):
        """Test creating RuleSpec from empty dict."""
        spec = RuleSpec.from_definition("remove_unused_measures", {})
        assert spec.id == "remove_unused_measures"
        assert spec.severity == "warning"
        assert spec.is_expression_rule is False

    def test_from_definition_expression_rule(self):
        """Test creating RuleSpec from expression rule definition."""
        spec = RuleSpec.from_definition(
            "reduce_pages",
            {
                "severity": "info",
                "expression": "len(pages) <= max_pages",
                "scope": "report",
                "params": {"max_pages": 10},
            },
        )
        assert spec.id == "reduce_pages"
        assert spec.severity == "info"
        assert spec.expression == "len(pages) <= max_pages"
        assert spec.scope == "report"
        assert spec.params == {"max_pages": 10}
        assert spec.is_expression_rule is True

    def test_display_name_uses_description_if_present(self):
        """Test display_name property returns description when set."""
        spec = RuleSpec(id="test_rule", description="Test Rule Display Name")
        assert spec.display_name == "Test Rule Display Name"

    def test_display_name_fallback_to_id(self):
        """Test display_name property falls back to id formatted as title."""
        spec = RuleSpec(id="test_rule")
        assert spec.display_name == "Test Rule"


class TestRulesConfig:
    """Tests for RulesConfig dataclass."""

    def test_default_values(self):
        """Test default property values."""
        config = RulesConfig(rules=[RuleSpec(id="test")], options={})
        assert config.fail_on_warning is False

    def test_fail_on_warning_from_options(self):
        """Test fail_on_warning from options."""
        config = RulesConfig(
            rules=[RuleSpec(id="test")],
            options={"fail_on_warning": True},
        )
        assert config.fail_on_warning is True

    def test_get_rule_ids(self):
        """Test get_rule_ids method."""
        config = RulesConfig(
            rules=[RuleSpec(id="a"), RuleSpec(id="b"), RuleSpec(id="c")],
        )
        assert config.get_rule_ids() == ["a", "b", "c"]


class TestFindUserRules:
    """Tests for find_user_rules."""

    def test_no_config_found(self, tmp_path):
        """Test when no config file exists."""
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_rules(str(tmp_path))
        assert result is None

    def test_cwd_config(self, tmp_path):
        """Test finding config in current working directory."""
        config_path = tmp_path / "pbir-rules.yaml"
        config_path.write_text("rules:\n  - remove_unused_bookmarks")

        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_rules()

        assert result == config_path

    def test_report_path_config(self, tmp_path):
        """Test finding config in report path."""
        report_path = tmp_path / "MyReport.Report"
        report_path.mkdir()
        config_path = report_path / "pbir-rules.yaml"
        config_path.write_text("rules:\n  - reduce_pages")

        # CWD has no config
        with patch("pathlib.Path.cwd", return_value=tmp_path):
            result = find_user_rules(str(report_path))

        assert result == config_path


class TestMergeConfigs:
    """Tests for _merge_configs function."""

    def test_empty_user_uses_defaults(self):
        """Test that empty user config uses all defaults."""
        default = {
            "definitions": {
                "rule_a": {"severity": "warning"},
            },
            "rules": ["rule_a"],
        }
        user = {}

        config = _merge_configs(default, user)
        assert config.get_rule_ids() == ["rule_a"]
        assert "rule_a" in config.definitions

    def test_user_rules_replace_defaults(self):
        """Test that user rules list replaces default list."""
        default = {
            "definitions": {
                "rule_a": {"severity": "warning"},
                "rule_b": {"severity": "info"},
            },
            "rules": ["rule_a", "rule_b"],
        }
        user = {
            "rules": ["rule_b"],
        }

        config = _merge_configs(default, user)
        assert config.get_rule_ids() == ["rule_b"]

    def test_include_adds_rules(self):
        """Test that include adds rules to defaults."""
        default = {
            "definitions": {
                "rule_a": {},
                "rule_b": {},
            },
            "rules": ["rule_a"],
        }
        user = {
            "include": ["rule_b"],
        }

        config = _merge_configs(default, user)
        assert "rule_a" in config.get_rule_ids()
        assert "rule_b" in config.get_rule_ids()

    def test_exclude_removes_rules(self):
        """Test that exclude removes rules from defaults."""
        default = {
            "definitions": {
                "rule_a": {},
                "rule_b": {},
            },
            "rules": ["rule_a", "rule_b"],
        }
        user = {
            "exclude": ["rule_a"],
        }

        config = _merge_configs(default, user)
        assert "rule_a" not in config.get_rule_ids()
        assert "rule_b" in config.get_rule_ids()

    def test_user_definitions_override_defaults(self):
        """Test that user definitions override default definitions."""
        default = {
            "definitions": {
                "reduce_pages": {
                    "params": {"max_pages": 10},
                },
            },
            "rules": ["reduce_pages"],
        }
        user = {
            "definitions": {
                "reduce_pages": {
                    "params": {"max_pages": 5},
                },
            },
        }

        config = _merge_configs(default, user)
        rule = config.definitions["reduce_pages"]
        assert rule.params["max_pages"] == 5

    def test_options_merge(self):
        """Test that options are merged."""
        default = {
            "definitions": {},
            "rules": [],
            "options": {"fail_on_warning": False},
        }
        user = {
            "options": {"fail_on_warning": True},
        }

        config = _merge_configs(default, user)
        assert config.fail_on_warning is True


class TestLoadRules:
    """Tests for load_rules function."""

    def test_loads_default_config(self):
        """Test that load_rules loads default config when no user config."""
        with patch("pbir_utils.rule_config.find_user_rules", return_value=None):
            config = load_rules()

        # Should have default expression rules (no sanitizer actions in rules.yaml)
        assert len(config.rules) > 0
        # Check for an expression rule, not a sanitizer action
        assert "reduce_pages" in config.get_rule_ids()

    def test_raises_on_missing_explicit_config(self, tmp_path):
        """Test that explicit config path raises if not found."""
        import pytest

        with pytest.raises(FileNotFoundError):
            load_rules(config_path=tmp_path / "nonexistent.yaml")

    def test_loads_explicit_config(self, tmp_path):
        """Test loading from explicit config path."""
        config_path = tmp_path / "custom-rules.yaml"
        config_path.write_text(
            """
definitions:
  custom_rule:
    severity: error
    expression: "len(pages) <= 5"
    scope: report
rules:
  - custom_rule
"""
        )

        config = load_rules(config_path=config_path)
        assert "custom_rule" in config.get_rule_ids()
        assert config.definitions["custom_rule"].severity == "error"
