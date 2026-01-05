"""Report API routes for wireframe, actions, and exports."""

import asyncio
import csv
import io
import json
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
)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/wireframe", response_model=WireframeResponse)
async def get_wireframe(request: WireframeRequest):
    """
    Get wireframe data for a report.

    Runs in thread pool to avoid blocking on large reports.
    """
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
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from pathlib import Path

    # Assuming templates are in parent of api/routes/.. -> src/pbir_utils/templates
    # Actually file is pbir_utils/api/routes/reports.py
    # Templates are pbir_utils/templates
    template_dir = Path(__file__).parent.parent.parent / "templates"

    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "htm", "xml", "j2"]),
    )
    template = env.get_template("wireframe_content.html.j2")

    html_content = template.render(
        report_name=data["report_name"],
        pages=data["pages"],
        fields_index=data["fields_index"],
        active_page_id=data["active_page_id"],
    )

    data["html_content"] = html_content

    return WireframeResponse(**data)


@router.get("/actions", response_model=ActionsResponse)
async def list_actions(report_path: str = None):
    """
    List all available sanitize actions from config.

    If report_path is provided, checks for pbir-sanitize.yaml in that location.
    Returns all defined actions with their descriptions and default status.
    """
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
                name=action.name,
                description=action.description,
                is_default=True,
            )
        )

    # Then add additional defined actions (not in defaults)
    for name, spec in config.definitions.items():
        if name not in default_action_names:
            actions.append(
                ActionInfo(
                    name=name,
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
        user_config = yaml.safe_load(content) or {}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")

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
    from pbir_utils import sanitize_powerbi_report
    from pbir_utils.console_utils import console

    output_lines = []
    with console.capture_output() as queue:
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
        except Exception:
            pass  # Fall back to default config on error

    async def generate():
        with console.capture_output() as queue:

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
                                ActionSpec(name=action_name, implementation=action_name)
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
