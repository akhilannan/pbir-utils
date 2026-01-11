"""Report API routes for wireframe, actions, and exports."""

import asyncio
import csv
import io
import json
import logging
import threading
from queue import Empty

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import yaml

from ..models import (
    WireframeRequest,
    WireframeResponse,
    ActionsResponse,
    ConfigResponse,
    RunActionRequest,
    RunActionResponse,
    RuleInfo,
    RulesResponse,
    ValidateRequest,
    ViolationInfo,
    ValidateResponse,
)
from pbir_utils.common import validate_report_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/wireframe", response_model=WireframeResponse)
async def get_wireframe(request: WireframeRequest):
    """
    Get wireframe data for a report.

    Args:
        request: WireframeRequest containing report path and filters.

    Returns:
        WireframeResponse with HTML content and page metadata.
    """
    try:
        request.report_path = str(validate_report_path(request.report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    logger.info("Generating wireframe for: %s", request.report_path)
    from pbir_utils.report_wireframe_visualizer import get_wireframe_data

    data = await run_in_threadpool(
        get_wireframe_data,
        request.report_path,
        pages=request.pages,
        visual_types=request.visual_types,
        show_hidden=request.show_hidden,
    )

    if data is None:
        raise HTTPException(
            status_code=404, detail="No pages found or no pages match filters"
        )

    # Render wireframe content template
    from pbir_utils.template_utils import render_wireframe_content

    html_content = render_wireframe_content(data)

    data["html_content"] = html_content

    return WireframeResponse(**data)


@router.get("/actions", response_model=ActionsResponse)
async def list_actions(report_path: str = None):
    """
    List all available sanitize actions from config.

    Args:
        report_path: Optional path to report for loading custom config.

    If report_path is provided, checks for pbir-sanitize.yaml in that location.
    Returns all defined actions with their descriptions and default status.
    """
    if report_path:
        try:
            report_path = str(validate_report_path(report_path))
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    logger.debug("Listing actions (report_path=%s)", report_path)
    from pbir_utils.sanitize_config import load_config, find_user_config

    from ..models import ActionInfo

    config = load_config(report_path=report_path)

    # Get default action names for marking is_default
    default_action_names = set(config.get_action_names())

    # Build action list with metadata from all definitions
    actions = []

    # First add default actions in their configured order
    for action in config.actions:
        actions.append(
            ActionInfo(
                id=action.id,
                description=action.description,
                is_default=True,
            )
        )

    # Then add additional defined actions (not in defaults)
    for action_id, spec in config.definitions.items():
        if action_id not in default_action_names:
            actions.append(
                ActionInfo(
                    id=action_id,
                    description=spec.description,
                    is_default=False,
                )
            )

    # Determine config path for UI indicator
    user_config_path = find_user_config(report_path)
    config_path_str = str(user_config_path) if user_config_path else None

    return ActionsResponse(actions=actions, config_path=config_path_str)


@router.get("/config", response_model=ConfigResponse)
async def get_config(report_path: str = None):
    """
    Get the sanitize configuration.

    If report_path is provided, looks for pbir-sanitize.yaml in that location.
    """
    if report_path:
        try:
            report_path = str(validate_report_path(report_path))
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    from pbir_utils.sanitize_config import load_config

    config = load_config(report_path=report_path)
    return ConfigResponse(
        actions=config.get_action_names(),
        definitions={k: v.__dict__ for k, v in config.definitions.items()},
    )


@router.post("/config", response_model=ConfigResponse)
async def load_custom_config(file: UploadFile):
    """Parse and merge a custom pbir-sanitize.yaml file with defaults."""
    from pbir_utils.sanitize_config import (
        get_default_config_path,
        _load_yaml,
        _merge_configs,
    )

    try:
        content = await file.read()
        logger.info("Loading custom config from upload: %s", file.filename)
        user_config = yaml.safe_load(content) or {}

        # Validate structure: Sanitizer config must NOT look like a Rules config
        if "rules" in user_config:
            raise ValueError(
                "Invalid Sanitizer config: Found 'rules' key. "
                "Did you try to load a Rules configuration file?"
            )

        # Check definitions for rule-specific keys
        if "definitions" in user_config:
            for def_id, def_data in user_config["definitions"].items():
                if "expression" in def_data:
                    raise ValueError(
                        f"Invalid Sanitizer config: Definition '{def_id}' contains 'expression'. "
                        "This looks like a Rules configuration."
                    )

        # Strict validation: Must contain at least one valid Sanitizer key
        valid_keys = {"actions", "definitions", "include", "exclude", "options"}
        if not any(k in user_config for k in valid_keys):
            raise ValueError(
                "Invalid Sanitizer config: No valid keys found. "
                f"Expected one of: {', '.join(valid_keys)}"
            )

    except Exception as e:
        logger.error("Failed to parse custom config: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid Config: {e}")

    # Load default config and merge with user config
    default_config = _load_yaml(get_default_config_path())
    merged = _merge_configs(default_config, user_config)

    return ConfigResponse(
        actions=merged.get_action_names(),
        definitions={k: v.__dict__ for k, v in merged.definitions.items()},
    )


@router.post("/run", response_model=RunActionResponse)
async def run_actions(request: RunActionRequest):
    """
    Run sanitize actions synchronously.

    For streaming output, use /run/stream instead.
    """
    try:
        request.report_path = str(validate_report_path(request.report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    from pbir_utils import sanitize_powerbi_report
    from pbir_utils.console_utils import console

    output_lines = []
    with console.stream_output() as queue:
        try:
            await run_in_threadpool(
                sanitize_powerbi_report,
                request.report_path,
                actions=request.actions,
                dry_run=request.dry_run,
            )
            success = True
        except Exception as e:
            output_lines.append(f"Error: {e}")
            success = False

        # Drain the queue
        while not queue.empty():
            try:
                msg = queue.get_nowait()
                output_lines.append(msg.get("message", ""))
            except Empty:
                break

    return RunActionResponse(success=success, output=output_lines)


@router.get("/run/stream")
async def run_actions_stream(
    path: str, actions: str, dry_run: bool = True, config_yaml: str = None
):  # noqa: FBT001, FBT002
    """
    Run sanitize actions with SSE streaming output.

    Uses Server-Sent Events to stream console output in real-time.
    If config_yaml is provided (base64 encoded), it will be merged with defaults.
    """
    try:
        path = str(validate_report_path(path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    import base64
    from pbir_utils import sanitize_powerbi_report
    from pbir_utils.console_utils import console
    from pbir_utils.sanitize_config import (
        get_default_config_path,
        _load_yaml,
        _merge_configs,
        SanitizeConfig,
    )

    action_list = actions.split(",")

    # Parse custom config if provided
    custom_config = None
    if config_yaml:
        try:
            yaml_content = base64.b64decode(config_yaml).decode("utf-8")
            user_config = yaml.safe_load(yaml_content) or {}
            default_config = _load_yaml(get_default_config_path())
            custom_config = _merge_configs(default_config, user_config)
        except Exception as e:
            logger.debug("Failed to merge custom config: %s", e)

    async def generate():
        with console.stream_output() as queue:

            def run():
                if custom_config:
                    # Build config with requested actions using custom definitions
                    from pbir_utils.sanitize_config import ActionSpec

                    action_specs = []
                    for action_name in action_list:
                        if action_name in custom_config.definitions:
                            action_specs.append(custom_config.definitions[action_name])
                        else:
                            action_specs.append(
                                ActionSpec(id=action_name, implementation=action_name)
                            )

                    # Merge options from custom config with dry_run override
                    merged_options = dict(custom_config.options)
                    merged_options["dry_run"] = dry_run

                    run_config = SanitizeConfig(
                        actions=action_specs,
                        definitions=custom_config.definitions,
                        options=merged_options,
                    )
                    sanitize_powerbi_report(path, config=run_config)
                else:
                    sanitize_powerbi_report(path, actions=action_list, dry_run=dry_run)

            thread = threading.Thread(target=run)
            thread.start()

            while thread.is_alive() or not queue.empty():
                try:
                    # Non-blocking check
                    msg = queue.get_nowait()
                    yield {"event": "message", "data": json.dumps(msg)}
                except Empty:
                    # Yield control to event loop
                    await asyncio.sleep(0.05)

            yield {"event": "complete", "data": "{}"}

    return EventSourceResponse(generate())


@router.get("/metadata/csv")
async def download_metadata_csv(report_path: str, visual_ids: str = None):
    """
    Download attribute metadata as CSV.

    Args:
        report_path: Path to the PBIR report folder.
        visual_ids: Optional comma-separated list of visual IDs to filter by (WYSIWYG export).
    """
    from pbir_utils.metadata_extractor import (
        _consolidate_metadata_from_directory,
        HEADER_FIELDS,
    )

    try:
        report_path = str(validate_report_path(report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Build filters from visual_ids if provided (WYSIWYG filtered export)
    # Note: HEADER_FIELDS uses "ID" for the visual identifier
    filters = None
    if visual_ids:
        filters = {"ID": set(visual_ids.split(","))}

    metadata = await run_in_threadpool(
        _consolidate_metadata_from_directory, report_path, filters
    )

    if not metadata:
        raise HTTPException(status_code=404, detail="No metadata found")

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=HEADER_FIELDS)
    writer.writeheader()
    writer.writerows(metadata)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=metadata.csv"},
    )


@router.get("/visuals/csv")
async def download_visuals_csv(report_path: str, visual_ids: str = None):
    """
    Download visual metadata as CSV.

    Args:
        report_path: Path to the PBIR report folder.
        visual_ids: Optional comma-separated list of visual IDs to filter by (WYSIWYG export).
    """
    from pbir_utils.common import iter_pages, extract_visual_info
    from pbir_utils.metadata_extractor import VISUAL_HEADER_FIELDS
    from pathlib import Path

    # Parse visual IDs filter (for WYSIWYG filtered export)
    visual_id_set = set(visual_ids.split(",")) if visual_ids else None

    try:
        report_path = str(validate_report_path(report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    def extract_visuals():
        metadata = []
        report_name = Path(report_path).name.replace(".Report", "")

        for page_id, page_folder, page_data in iter_pages(report_path):
            page_name = page_data.get("displayName", "NA")
            visuals_info = extract_visual_info(page_folder)

            for visual_id, info in visuals_info.items():
                # Skip if filtering and this visual not in filter (WYSIWYG)
                if visual_id_set and visual_id not in visual_id_set:
                    continue
                metadata.append(
                    {
                        "Report": report_name,
                        "Page Name": page_name,
                        "Page ID": page_id,
                        "Visual Type": info["visualType"],
                        "Visual ID": visual_id,
                        "Parent Group ID": info.get("parentGroupName"),
                        "Is Hidden": info.get("isHidden", False),
                    }
                )
        return metadata

    metadata = await run_in_threadpool(extract_visuals)

    if not metadata:
        raise HTTPException(status_code=404, detail="No visuals found")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=VISUAL_HEADER_FIELDS)
    writer.writeheader()
    writer.writerows(metadata)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=visuals.csv"},
    )


@router.get("/wireframe/html")
async def download_wireframe_html(report_path: str, visual_ids: str = None):
    """
    Download wireframe as self-contained HTML file.

    Args:
        report_path: Path to the PBIR report folder.
        visual_ids: Optional comma-separated list of visual IDs to filter by (WYSIWYG export).
    """
    from pbir_utils.report_wireframe_visualizer import get_wireframe_data
    from pbir_utils.template_utils import render_wireframe_html

    # Parse visual IDs filter (for WYSIWYG filtered export)
    visual_id_list = visual_ids.split(",") if visual_ids else None

    try:
        report_path = str(validate_report_path(report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Get wireframe data with optional filtering
    data = await run_in_threadpool(
        get_wireframe_data,
        report_path,
        visual_ids=visual_id_list,
    )

    if data is None:
        raise HTTPException(
            status_code=404, detail="No pages found or no pages match filters"
        )

    # Render the full standalone wireframe HTML template
    html_content = render_wireframe_html(data)

    # Generate filename from report name
    report_name = data["report_name"].replace(" ", "_")
    filename = f"wireframe_{report_name}.html"

    return StreamingResponse(
        iter([html_content]),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# Validation endpoints


@router.get("/validate/rules", response_model=RulesResponse)
async def list_expression_rules(report_path: str = None):
    """
    List expression-based validation rules only.

    Excludes sanitizer-based rules since those are shown in the Actions panel.
    """
    if report_path:
        try:
            report_path = str(validate_report_path(report_path))
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))

    from pbir_utils.rule_config import load_rules, find_user_rules

    cfg = await run_in_threadpool(load_rules, report_path=report_path)

    # Filter to expression-based rules only
    rules = [
        RuleInfo(
            id=r.id,
            description=r.description or r.display_name,
            severity=r.severity,
            scope=r.scope,
        )
        for r in cfg.rules
        if r.is_expression_rule
    ]

    user_config = find_user_rules(report_path)
    return RulesResponse(
        rules=rules, config_path=str(user_config) if user_config else None
    )


@router.post("/validate/config", response_model=RulesResponse)
async def load_custom_rules_config(file: UploadFile):
    """Parse and merge a custom pbir-rules.yaml file with defaults."""
    from pbir_utils.rule_config import (
        get_default_rules_path,
        _load_yaml,
        _merge_configs,
    )

    try:
        content = await file.read()
        logger.info("Loading custom rules config from upload: %s", file.filename)
        user_config = yaml.safe_load(content) or {}

        # Validate structure: Rules config must NOT look like a Sanitizer config
        if "actions" in user_config:
            raise ValueError(
                "Invalid Rules config: Found 'actions' key. "
                "Did you try to load a Sanitizer configuration file?"
            )

        # Check definitions for action-specific keys
        if "definitions" in user_config:
            for def_id, def_data in user_config["definitions"].items():
                if "implementation" in def_data:
                    raise ValueError(
                        f"Invalid Rules config: Definition '{def_id}' contains 'implementation'. "
                        "This looks like a Sanitizer configuration."
                    )

        # Strict validation: Must contain at least one valid Rules key
        valid_keys = {"rules", "definitions", "include", "exclude", "options"}
        if not any(k in user_config for k in valid_keys):
            raise ValueError(
                "Invalid Rules config: No valid keys found. "
                f"Expected one of: {', '.join(valid_keys)}"
            )

    except Exception as e:
        logger.error("Failed to parse custom rules config: %s", e)
        raise HTTPException(status_code=400, detail=f"Invalid Config: {e}")

    # Load default config and merge with user config
    default_path = get_default_rules_path()
    default_config = _load_yaml(default_path) if default_path.exists() else {}
    merged = _merge_configs(default_config, user_config)

    # Filter to expression-based rules only (same as list_expression_rules)
    rules = [
        RuleInfo(
            id=r.id,
            description=r.description or r.display_name,
            severity=r.severity,
            scope=r.scope,
        )
        for r in merged.rules
        if r.is_expression_rule
    ]

    return RulesResponse(rules=rules, config_path=file.filename)


@router.post("/validate/run", response_model=ValidateResponse)
async def run_validation(request: ValidateRequest):
    """
    Run combined validation: expression rules + sanitize action checks.

    Express rules evaluate conditions on report structure.
    Sanitize actions are run in dry-run mode to check if changes would be made.
    """
    try:
        request.report_path = str(validate_report_path(request.report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    import base64
    import tempfile
    from pathlib import Path
    from pbir_utils.rule_engine import validate_report
    from pbir_utils.sanitize_config import load_config as load_sanitize_config
    from pbir_utils.console_utils import console

    all_results = {}
    all_violations = []

    # Decode custom rules config if provided
    rules_config_path = None
    temp_file = None
    if request.rules_config_yaml:
        try:
            yaml_content = base64.b64decode(request.rules_config_yaml).decode("utf-8")
            # Write to temp file for validate_report
            temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            )
            temp_file.write(yaml_content)
            temp_file.close()
            rules_config_path = temp_file.name
        except Exception as e:
            logger.debug("Failed to decode rules config: %s", e)

    try:
        # 1. Run expression rules
        if request.expression_rules:
            with console.suppress_all():
                result = await run_in_threadpool(
                    validate_report,
                    request.report_path,
                    source="rules",
                    rules=request.expression_rules,
                    rules_config=rules_config_path,
                    strict=False,
                )
            all_results.update(result.results)
            for v in result.violations:
                all_violations.append(
                    ViolationInfo(
                        rule_id=v.get("rule_id", ""),
                        rule_name=v.get("rule_name", ""),
                        severity=v.get("severity", "warning"),
                        message=v.get("message", ""),
                        rule_type="expression",
                        page_name=v.get("page_name"),
                        visual_name=v.get("visual_name"),
                    )
                )

        # 2. Run sanitize action dry-run checks (only if include_sanitizer is True)
        if request.include_sanitizer and request.sanitize_actions:
            # Load sanitize config to get action severities
            san_cfg = await run_in_threadpool(
                load_sanitize_config, report_path=request.report_path
            )

            with console.suppress_all():
                result = await run_in_threadpool(
                    validate_report,
                    request.report_path,
                    source="sanitize",
                    actions=request.sanitize_actions,
                    strict=False,
                )

            all_results.update(result.results)
            for v in result.violations:
                # Get severity from sanitize config
                action_id = v.get("rule_id", "")
                action_spec = san_cfg.definitions.get(action_id)
                severity = action_spec.severity if action_spec else "warning"

                all_violations.append(
                    ViolationInfo(
                        rule_id=action_id,
                        rule_name=v.get(
                            "rule_name", action_id.replace("_", " ").title()
                        ),
                        severity=severity,
                        message=v.get("message", "Would make changes"),
                        rule_type="sanitizer",
                    )
                )
    finally:
        # Cleanup temp file
        if temp_file:
            try:
                Path(temp_file.name).unlink(missing_ok=True)
            except Exception as e:
                logger.debug("Failed to cleanup temp file: %s", e)

    # Calculate counts
    passed = sum(1 for v in all_results.values() if v)
    failed = sum(1 for v in all_results.values() if not v)

    return ValidateResponse(
        passed=passed,
        failed=failed,
        error_count=sum(1 for v in all_violations if v.severity == "error"),
        warning_count=sum(1 for v in all_violations if v.severity == "warning"),
        info_count=sum(1 for v in all_violations if v.severity == "info"),
        results=all_results,
        violations=all_violations,
    )


@router.get("/validate/run/stream")
async def run_validation_stream(
    report_path: str,
    expression_rules: str = None,
    sanitize_actions: str = None,
    include_sanitizer: bool = True,
    rules_config_yaml: str = None,
    sanitize_config_yaml: str = None,
):
    """
    Run validation with SSE streaming output.

    Uses Server-Sent Events to stream console output in real-time.
    Same as CLI output behavior.
    """
    try:
        report_path = str(validate_report_path(report_path))
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    import base64
    import tempfile
    from pathlib import Path
    from pbir_utils.rule_engine import validate_report
    from pbir_utils.console_utils import console

    # Parse comma-separated lists
    expr_rules_list = expression_rules.split(",") if expression_rules else []
    sanitize_actions_list = (
        sanitize_actions.split(",") if sanitize_actions and include_sanitizer else []
    )

    # Decode custom rules config if provided
    rules_config_path = None
    rules_temp_file = None
    if rules_config_yaml:
        try:
            yaml_content = base64.b64decode(rules_config_yaml).decode("utf-8")
            rules_temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            )
            rules_temp_file.write(yaml_content)
            rules_temp_file.close()
            rules_config_path = rules_temp_file.name
        except Exception as e:
            logger.debug("Failed to decode rules config: %s", e)

    # Decode custom sanitize config if provided
    sanitize_config_path = None
    sanitize_temp_file = None
    if sanitize_config_yaml:
        try:
            yaml_content = base64.b64decode(sanitize_config_yaml).decode("utf-8")
            sanitize_temp_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            )
            sanitize_temp_file.write(yaml_content)
            sanitize_temp_file.close()
            sanitize_config_path = sanitize_temp_file.name
        except Exception as e:
            logger.debug("Failed to decode sanitize config: %s", e)

    async def generate():
        all_results = {}
        all_violations = []

        with console.stream_output() as queue:

            def run():
                nonlocal all_results, all_violations

                try:
                    # Run validation with both rules and sanitizer actions
                    result = validate_report(
                        report_path,
                        source="all",
                        rules=expr_rules_list if expr_rules_list else None,
                        actions=(
                            sanitize_actions_list if sanitize_actions_list else None
                        ),
                        rules_config=rules_config_path,
                        sanitize_config=sanitize_config_path,
                        strict=False,
                    )
                    all_results.update(result.results)
                    all_violations.extend(result.violations)

                except Exception as e:
                    # Error will be captured in console output
                    logger.debug("Validation error: %s", e)

            thread = threading.Thread(target=run)
            thread.start()

            while thread.is_alive() or not queue.empty():
                try:
                    msg = queue.get_nowait()
                    yield {"event": "message", "data": json.dumps(msg)}
                except Empty:
                    await asyncio.sleep(0.05)

            # Send final summary
            passed = sum(1 for v in all_results.values() if v)
            failed = sum(1 for v in all_results.values() if not v)
            error_count = sum(1 for v in all_violations if v.get("severity") == "error")
            warning_count = sum(
                1 for v in all_violations if v.get("severity") == "warning"
            )

            summary = {
                "passed": passed,
                "failed": failed,
                "error_count": error_count,
                "warning_count": warning_count,
            }
            yield {"event": "complete", "data": json.dumps(summary)}

        # Cleanup temp files
        if rules_temp_file:
            try:
                Path(rules_temp_file.name).unlink(missing_ok=True)
            except Exception as e:
                logger.debug("Failed to cleanup rules temp file: %s", e)
        if sanitize_temp_file:
            try:
                Path(sanitize_temp_file.name).unlink(missing_ok=True)
            except Exception as e:
                logger.debug("Failed to cleanup sanitize temp file: %s", e)

    return EventSourceResponse(generate())
