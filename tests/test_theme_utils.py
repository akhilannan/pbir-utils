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
