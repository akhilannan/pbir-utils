"""Tests for theme_utils module."""

import os
from unittest.mock import patch

from conftest import create_dummy_file
from pbir_utils.theme_utils import (
    set_theme,
    reset_hardcoded_colors,
)
from pbir_utils.common import load_json


class TestSetTheme:
    """Tests for set_theme."""

    def test_set_theme_creates_resource_packages(self, tmp_path):
        report_path = str(tmp_path)
        create_dummy_file(tmp_path, "definition/report.json", {})

        # Create a dummy theme file
        theme_path = os.path.join(tmp_path, "NewTheme.json")
        with open(theme_path, "w") as f:
            f.write('{"name": "NewTheme"}')

        with patch("builtins.print"):
            result = set_theme(report_path, theme_path)

        assert result is True

        # Verify report.json
        report_data = load_json(os.path.join(report_path, "definition/report.json"))
        assert report_data["themeCollection"]["customTheme"]["name"] == "NewTheme.json"

        pkgs = report_data["resourcePackages"]
        assert len(pkgs) == 1
        assert pkgs[0]["name"] == "RegisteredResources"
        assert len(pkgs[0]["items"]) == 1
        assert pkgs[0]["items"][0]["name"] == "NewTheme.json"

        # Verify file is copied
        copied_file = os.path.join(
            report_path, "StaticResources/RegisteredResources/NewTheme.json"
        )
        assert os.path.exists(copied_file)

    def test_set_theme_dry_run(self, tmp_path):
        report_path = str(tmp_path)
        create_dummy_file(tmp_path, "definition/report.json", {})

        theme_path = os.path.join(tmp_path, "NewTheme.json")
        with open(theme_path, "w") as f:
            f.write('{"name": "NewTheme"}')

        result = set_theme(report_path, theme_path, dry_run=True)
        assert result is True

        report_data = load_json(os.path.join(report_path, "definition/report.json"))
        assert "themeCollection" not in report_data
        copied_file = os.path.join(
            report_path, "StaticResources/RegisteredResources/NewTheme.json"
        )
        assert not os.path.exists(copied_file)

    def test_set_theme_relative_path(self, tmp_path):
        report_path = str(tmp_path)
        create_dummy_file(tmp_path, "definition/report.json", {})

        # Create a themes directory separate from the report
        themes_dir = tmp_path / "my_themes"
        themes_dir.mkdir()
        theme_path = themes_dir / "RelativeTheme.json"
        with open(theme_path, "w") as f:
            f.write('{"name": "RelativeTheme"}')

        with patch("builtins.print"):
            # Use relative path and config_dir to resolve it
            result = set_theme(
                report_path, "RelativeTheme.json", config_dir=str(themes_dir)
            )

        assert result is True

        # Verify file is copied from the resolved relative path
        copied_file = os.path.join(
            report_path, "StaticResources/RegisteredResources/RelativeTheme.json"
        )
        assert os.path.exists(copied_file)

    def test_set_theme_skips_when_content_matches(self, tmp_path):
        report_path = str(tmp_path)
        # Create report with existing theme
        report_data = {
            "themeCollection": {
                "customTheme": {"name": "MyTheme.json", "type": "RegisteredResources"}
            }
        }
        create_dummy_file(tmp_path, "definition/report.json", report_data)

        # Create the existing theme file in the report
        existing_theme_content = '{\n  "name": "MyTheme",\n  "color": "#FFFFFF"\n}'
        create_dummy_file(
            tmp_path,
            "StaticResources/RegisteredResources/MyTheme.json",
            existing_theme_content,
        )

        # Create the new (source) theme file with identical content (even if formatted differently)
        theme_path = os.path.join(tmp_path, "MyTheme.json")
        with open(theme_path, "w") as f:
            f.write('{"name": "MyTheme", "color": "#FFFFFF"}')

        with patch("pbir_utils.console_utils.console.print_info") as mock_info:
            result = set_theme(report_path, theme_path)

        # Should return False because content is identical
        assert result is False
        mock_info.assert_called_with(
            "Theme already matches existing — no changes needed."
        )

    def test_set_theme_removes_old_theme(self, tmp_path):
        report_path = str(tmp_path)
        # Create report with existing theme
        report_data = {
            "themeCollection": {
                "customTheme": {"name": "OldTheme.json", "type": "RegisteredResources"}
            }
        }
        create_dummy_file(tmp_path, "definition/report.json", report_data)

        # Create the old theme file
        old_theme_path = os.path.join(
            report_path, "StaticResources/RegisteredResources/OldTheme.json"
        )
        create_dummy_file(
            tmp_path,
            "StaticResources/RegisteredResources/OldTheme.json",
            '{"name": "OldTheme"}',
        )

        # Create the new theme file
        theme_path = os.path.join(tmp_path, "NewTheme.json")
        with open(theme_path, "w") as f:
            f.write('{"name": "NewTheme"}')

        with patch("builtins.print"):
            result = set_theme(report_path, theme_path)

        assert result is True

        # Verify old theme is removed
        assert not os.path.exists(old_theme_path)

        # Verify new theme is copied
        new_theme_path = os.path.join(
            report_path, "StaticResources/RegisteredResources/NewTheme.json"
        )
        assert os.path.exists(new_theme_path)

    def test_set_theme_applies_when_content_differs(self, tmp_path):
        report_path = str(tmp_path)
        # Create report with existing theme and custom version
        custom_version = {"visual": "1.9.9", "report": "2.9.9", "page": "1.9.9"}
        report_data = {
            "themeCollection": {
                "customTheme": {
                    "name": "MyTheme.json",
                    "type": "RegisteredResources",
                    "reportVersionAtImport": custom_version,
                }
            }
        }
        create_dummy_file(tmp_path, "definition/report.json", report_data)

        # Create the existing theme file in the report
        existing_theme_content = '{"name": "MyTheme", "color": "#000000"}'
        create_dummy_file(
            tmp_path,
            "StaticResources/RegisteredResources/MyTheme.json",
            existing_theme_content,
        )

        # Create the new (source) theme file with DIFFERENT content
        theme_path = os.path.join(tmp_path, "MyTheme.json")
        with open(theme_path, "w") as f:
            f.write('{"name": "MyTheme", "color": "#FFFFFF"}')

        with patch("builtins.print"):
            result = set_theme(report_path, theme_path)

        # Should return True because content differs
        assert result is True

        # Verify custom version was preserved
        updated_report_data = load_json(
            os.path.join(report_path, "definition/report.json")
        )
        updated_version = updated_report_data["themeCollection"]["customTheme"][
            "reportVersionAtImport"
        ]
        assert updated_version == {
            "visual": "1.9.9",
            "report": "2.9.9",
            "page": "1.9.9",
        }

    def test_set_theme_via_sanitizer_relative_path(self, tmp_path):
        """Test that set_theme works via sanitizer YAML with relative theme_path."""
        report_dir = tmp_path / "MyReport.Report"
        report_def = report_dir / "definition"
        report_def.mkdir(parents=True)
        create_dummy_file(report_dir, "definition/report.json", {})

        # Create a config dir with YAML and theme
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        themes_dir = config_dir / "themes"
        themes_dir.mkdir()
        theme_file = themes_dir / "Corporate.json"
        theme_file.write_text('{"name": "Corporate"}')

        yaml_content = """
definitions:
  set_theme:
    description: Apply standard corporate theme
    params:
      theme_path: "./themes/Corporate.json"

actions:
  - set_theme
"""
        yaml_file = config_dir / "pbir-sanitize.yaml"
        yaml_file.write_text(yaml_content)

        from pbir_utils.sanitize_config import load_config
        from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report

        cfg = load_config(config_path=str(yaml_file), report_path=str(report_dir))

        with patch("builtins.print"):
            results = sanitize_powerbi_report(str(report_dir), config=cfg)

        assert results.get("set_theme") is True
        copied_file = (
            report_dir / "StaticResources" / "RegisteredResources" / "Corporate.json"
        )
        assert copied_file.exists()

    def test_set_theme_backward_compat_preserves_config_dir(self, tmp_path):
        """Test backward-compat API preserves config_dir for relative path resolution."""
        report_dir = tmp_path / "MyReport.Report"
        report_def = report_dir / "definition"
        report_def.mkdir(parents=True)
        create_dummy_file(report_dir, "definition/report.json", {})

        # Place YAML with relative theme_path in report dir
        themes_dir = report_dir / "themes"
        themes_dir.mkdir()
        theme_file = themes_dir / "Corporate.json"
        theme_file.write_text('{"name": "Corporate"}')

        yaml_content = """
definitions:
  set_theme:
    description: Apply corp theme
    params:
      theme_path: "./themes/Corporate.json"

actions:
  - set_theme
"""
        (report_dir / "pbir-sanitize.yaml").write_text(yaml_content)

        from pbir_utils.pbir_report_sanitizer import sanitize_powerbi_report

        # Use backward-compat API with actions list. CWD is NOT the report dir,
        # so the only way this works is if config_dir from auto-discovered YAML
        # is preserved in the backward-compat path.
        with (
            patch("pathlib.Path.cwd", return_value=tmp_path),
            patch("builtins.print"),
        ):
            results = sanitize_powerbi_report(
                str(report_dir), ["set_theme"], dry_run=True
            )

        assert results.get("set_theme") is True


class TestResetHardcodedColors:
    """Tests for reset_hardcoded_colors."""

    def test_reset_solid_colors(self, tmp_path):
        report_path = str(tmp_path)
        # Create a dummy visual with hardcoded color
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"name": "Page1", "displayName": "Page 1"},
        )
        visual_data = {
            "name": "v1",
            "visual": {
                "visualType": "barChart",
                "objects": {
                    "categoryLabels": [
                        {
                            "properties": {
                                "color": {
                                    "solid": {
                                        "color": {
                                            "expr": {"Literal": {"Value": "'#FCC200'"}}
                                        }
                                    }
                                },
                                "fontSize": {"expr": {"Literal": {"Value": "12D"}}},
                            }
                        }
                    ]
                },
            },
        }
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v1/visual.json",
            visual_data,
        )

        result = reset_hardcoded_colors(report_path)

        assert result is True

        # Verify changes
        updated_data = load_json(
            os.path.join(report_path, "definition/pages/Page1/visuals/v1/visual.json")
        )
        props = updated_data["visual"]["objects"]["categoryLabels"][0]["properties"]
        assert "color" not in props
        assert "fontSize" in props  # Should be preserved
        assert props["fontSize"]["expr"]["Literal"]["Value"] == "12D"

    def test_reset_gradient_colors(self, tmp_path):
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"name": "Page1", "displayName": "Page 1"},
        )
        visual_data = {
            "name": "v1",
            "visual": {
                "visualType": "barChart",
                "objects": {
                    "dataPoint": [
                        {
                            "properties": {
                                "fill": {
                                    "solid": {
                                        "color": {
                                            "expr": {
                                                "FillRule": {
                                                    "FillRule": {
                                                        "linearGradient2": {
                                                            "min": {
                                                                "color": {
                                                                    "Literal": {
                                                                        "Value": "'#808080'"
                                                                    }
                                                                }
                                                            },
                                                            "max": {
                                                                "color": {
                                                                    "Literal": {
                                                                        "Value": "'#FFFFFF'"
                                                                    }
                                                                }
                                                            },
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    ]
                },
            },
        }
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v1/visual.json",
            visual_data,
        )

        result = reset_hardcoded_colors(report_path)

        assert result is True

        updated_data = load_json(
            os.path.join(report_path, "definition/pages/Page1/visuals/v1/visual.json")
        )
        props = updated_data["visual"]["objects"]["dataPoint"][0]["properties"]
        assert "fill" not in props

    def test_preserve_theme_colors(self, tmp_path):
        report_path = str(tmp_path)
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/page.json",
            {"name": "Page1", "displayName": "Page 1"},
        )
        visual_data = {
            "name": "v1",
            "visual": {
                "visualType": "barChart",
                "objects": {
                    "categoryLabels": [
                        {
                            "properties": {
                                "color": {
                                    "solid": {
                                        "color": {
                                            "expr": {
                                                "ThemeDataColor": {
                                                    "ColorId": 0,
                                                    "Percent": 0,
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    ]
                },
            },
        }
        create_dummy_file(
            tmp_path,
            "definition/pages/Page1/visuals/v1/visual.json",
            visual_data,
        )

        result = reset_hardcoded_colors(report_path)

        assert result is False  # No hardcoded colors to remove

        updated_data = load_json(
            os.path.join(report_path, "definition/pages/Page1/visuals/v1/visual.json")
        )
        props = updated_data["visual"]["objects"]["categoryLabels"][0]["properties"]
        assert "color" in props  # Should be preserved
