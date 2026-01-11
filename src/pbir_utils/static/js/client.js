/**
 * PBIR-Utils UI Client JavaScript
 * Handles file browsing, action execution, and SSE streaming
 */

// Constants
const SIDEBAR_MIN_WIDTH = 150;
const OUTPUT_PANEL_MIN_HEIGHT = 50;

// State
// currentReportPath, fieldsIndex are defined in template
const selectedActions = new Set();
let reportDirtyState = false;
let currentConfigPath = null;
let customConfigYaml = null;
let expressionRules = [];  // Validation rules
let customRulesConfigYaml = null;  // Custom rules YAML content
let currentRulesConfigPath = null;  // Custom rules config filename


// DOM Elements
const welcomeState = document.getElementById('welcome-state');
const wireframeContainer = document.getElementById('wireframe-container');
const outputContent = document.getElementById('output-content');
const dirtyBanner = document.getElementById('dirty-banner');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadActions();
    browseDirectory(null);

    // Auto-load report if initial path was provided via CLI
    if (typeof initialReportPath !== 'undefined' && initialReportPath) {
        loadReport(initialReportPath);
    }
});

// ============ File Browser ============

async function browseDirectory(path) {
    try {
        let url = '/api/browse';
        if (path) {
            url += `?path=${encodeURIComponent(path)}`;
        }
        const response = await fetch(url);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to browse');
        }
        const data = await response.json();
        renderFileList(data);
    } catch (e) {
        appendOutput('error', `Failed to browse: ${e.message}`);
    }
}

function renderFileList(data) {
    const breadcrumb = document.getElementById('breadcrumb');
    const fileList = document.getElementById('file-list');

    // Breadcrumb
    const crumbs = data.current_path.split(/[\/\\]/).filter(Boolean);
    let builtPath = '';
    breadcrumb.innerHTML = crumbs.map(crumb => {
        builtPath += `${crumb}/`;
        const safePath = builtPath.replace(/'/g, "\\'");
        return `<span class="breadcrumb-item" onclick="browseDirectory('${safePath}')">${crumb}</span>`;
    }).join(' / ');

    // Parent directory
    let html = '';
    if (data.parent_path) {
        const safeParent = data.parent_path.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
        html += `<div class="file-item" onclick="browseDirectory('${safeParent}')">📂 ..</div>`;
    }

    // Items
    html += data.items.map(item => {
        const icon = item.is_report ? '📊' : (item.is_dir ? '📁' : '📄');
        const isActive = currentReportPath && item.path === currentReportPath;
        const cls = `file-item${item.is_report ? ' report' : ''}${isActive ? ' active' : ''}`;

        let onclick = '';
        if (item.is_report || item.is_dir) {
            const safePath = item.path.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
            const func = item.is_report ? 'loadReport' : 'browseDirectory';
            onclick = `${func}('${safePath}')`;
        }

        return onclick
            ? `<div class="${cls}" onclick="${onclick}">${icon} ${escapeHtml(item.name)}</div>`
            : '';
    }).join('');

    fileList.innerHTML = html;
}

// Note: escapeHtml is provided by wireframe.js which is always loaded first

// ============ Report Loading ============

async function loadReport(reportPath, preserveActions) {
    try {
        appendOutput('info', `Loading report: ${reportPath}`);

        // Save current selection if requested
        let savedActions = null;
        if (preserveActions) {
            savedActions = new Set(selectedActions);
        }

        const response = await fetch('/api/reports/wireframe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report_path: reportPath })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load');
        }

        const data = await response.json();
        currentReportPath = reportPath;

        // Update global state for wireframe.js
        fieldsIndex = data.fields_index;
        activePageId = data.active_page_id;

        // Render wireframe
        renderWireframe(data);

        // Enable buttons
        document.getElementById('run-btn').disabled = false;
        document.getElementById('dry-run-btn').disabled = false;
        document.getElementById('export-meta-btn').disabled = false;
        document.getElementById('export-visuals-btn').disabled = false;
        document.getElementById('export-html-btn').disabled = false;

        setDirtyState(false);
        appendOutput('success', `Report loaded: ${data.report_name}`);

        // Reload actions with report path to pick up report-specific config
        await loadActions(reportPath);

        // Restore selections if requested
        if (savedActions) {
            restoreActionSelection(savedActions);
        }

        // Load expression rules for validation
        await loadExpressionRules(reportPath);

        // Navigate file browser to show and highlight the loaded report
        const parentPath = reportPath.replace(/[\\/][^\\/]+$/, '');
        browseDirectory(parentPath);

    } catch (e) {
        appendOutput('error', `Failed to load report: ${e.message}`);
    }
}

function renderWireframe(data) {
    // Hide welcome, show wireframe
    welcomeState.style.display = 'none';

    // Inject server-rendered HTML
    if (data.html_content) {
        wireframeContainer.innerHTML = data.html_content;
    }

    // Move tooltips to document.body (must be outside wireframe-container to avoid overflow clipping)
    const tooltipIds = ['tooltip', 'page-tooltip', 'field-tooltip', 'table-tooltip'];
    tooltipIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            document.body.appendChild(el);
        }
    });

    // Re-initialize wireframe.js global tooltip references (they were null at script load time)
    tooltip = document.getElementById('tooltip');
    pageTooltip = document.getElementById('page-tooltip');
    fieldTooltip = document.getElementById('field-tooltip');
    tableTooltip = document.getElementById('table-tooltip');

    // Reset cached elements
    cachedVisuals = null;
    cachedTabs = null;

    // Initialize wireframe.js functions
    initFieldsPane();
    setupVisualEventDelegation();

    // Set theme from localStorage
    const savedTheme = localStorage.getItem('wireframeTheme');
    if (savedTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
    }
}

// ============ Actions ============


async function loadActions(reportPath) {
    try {
        let url = '/api/reports/actions';
        if (reportPath) {
            url += `?report_path=${encodeURIComponent(reportPath)}`;
        }
        const response = await fetch(url);
        const data = await response.json();
        currentConfigPath = data.config_path;
        customConfigYaml = null;  // Reset custom config when loading from report
        renderActions(data.actions);
        updateConfigIndicator();
    } catch (e) {
        appendOutput('error', `Failed to load actions: ${e.message}`);
    }
}

function renderActions(actions) {
    selectedActions.clear();
    let html = '';

    // Split actions
    const defaultActions = actions.filter(a => a.is_default);
    const additionalActions = actions.filter(a => !a.is_default);

    // --- Default Actions Section ---
    if (defaultActions.length > 0) {
        html += `
        <div class="action-group-header">
            <div class="action-item select-all-container" style="border-bottom: 1px solid var(--border-color); margin-bottom: 4px; padding-bottom: 8px;">
                <input type="checkbox" id="select-all-default" onchange="toggleGroup('default', this)">
                <label for="select-all-default" style="font-weight: 600;">Default Actions</label>
            </div>
        </div>`;

        html += defaultActions.map((action, i) => {
            selectedActions.add(action.id); // Auto-select default
            const description = action.description || action.id.replace(/_/g, ' ');
            return `
            <div class="action-item" title="${escapeHtml(action.id)}">
                <input type="checkbox" id="action-def-${i}" value="${action.id}" checked
                    class="action-checkbox-default" onchange="toggleAction('${action.id}')">
                <label for="action-def-${i}">${escapeHtml(description)}</label>
            </div>`;
        }).join('');
    }

    // --- Additional Actions Section ---
    if (additionalActions.length > 0) {
        html += `
        <div class="action-group-header" style="margin-top: 12px;">
            <div class="action-item select-all-container" style="border-bottom: 1px solid var(--border-color); margin-bottom: 4px; padding-bottom: 8px;">
                <input type="checkbox" id="select-all-additional" onchange="toggleGroup('additional', this)">
                <label for="select-all-additional" style="font-weight: 600;">Additional Actions</label>
            </div>
        </div>`;

        html += additionalActions.map((action, i) => {
            const description = action.description || action.id.replace(/_/g, ' ');
            return `
            <div class="action-item additional" title="${escapeHtml(action.id)}">
                <input type="checkbox" id="action-add-${i}" value="${action.id}"
                    class="action-checkbox-additional" onchange="toggleAction('${action.id}')">
                <label for="action-add-${i}">${escapeHtml(description)}</label>
            </div>`;
        }).join('');
    }

    document.getElementById('actions-list').innerHTML = html;

    // Update select all states initially
    updateSelectAllState();
}

function restoreActionSelection(savedSet) {
    selectedActions.clear();
    const checkboxes = document.querySelectorAll('.action-checkbox-default, .action-checkbox-additional');

    checkboxes.forEach(cb => {
        cb.checked = savedSet.has(cb.value);
        if (cb.checked) {
            selectedActions.add(cb.value);
        }
    });

    updateSelectAllState();
    updateRunButtons();
}

function updateConfigIndicator() {
    const indicator = document.getElementById('config-indicator');
    if (indicator) {
        if (currentConfigPath) {
            const fileName = currentConfigPath.split(/[\\/]/).pop();
            indicator.innerHTML = `
                <span class="config-name">📄 ${fileName}</span>
                <span class="config-reset" onclick="resetConfig(event)" title="Reset to Defaults">×</span>
            `;
            indicator.title = `Custom config: ${currentConfigPath}`;
            indicator.style.display = 'inline-flex';
        } else {
            indicator.style.display = 'none';
        }
    }
}

async function loadCustomConfig(input) {
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];

    // Read file content for later use during execution
    const yamlContent = await file.text();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/reports/config', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load config');
        }

        const data = await response.json();

        // Store config for execution
        currentConfigPath = file.name;
        customConfigYaml = yamlContent;

        // Render new actions from config
        const actions = data.actions.map(id => {
            const def = data.definitions[id];
            return {
                id,
                description: def ? def.description : id.replace(/_/g, ' '),
                is_default: true
            };
        });
        renderActions(actions);
        updateConfigIndicator();
        ensureOutputPanelVisible();
        appendOutput('success', `Loaded custom config: ${file.name}`);

    } catch (e) {
        ensureOutputPanelVisible();
        appendOutput('error', `Failed to load config: ${e.message}`);
    }

    // Reset file input so same file can be selected again
    input.value = '';
}

async function resetConfig(event) {
    if (event) event.stopPropagation();
    currentConfigPath = null;
    customConfigYaml = null;
    await loadActions(currentReportPath);
    appendOutput('info', 'Reset to default configuration');
    updateRunButtons();
}

function updateSelectAllState() {
    updateGroupState('default');
    updateGroupState('additional');
}

function updateGroupState(type) {
    const checkboxes = Array.from(document.querySelectorAll(`.action-checkbox-${type}`));
    const selectAll = document.getElementById(`select-all-${type}`);

    if (!checkboxes.length || !selectAll) return;

    const allChecked = checkboxes.every(cb => cb.checked);
    const anyChecked = checkboxes.some(cb => cb.checked);

    selectAll.checked = allChecked;
    selectAll.indeterminate = !allChecked && anyChecked;
}

function toggleGroup(type, source) {
    const checkboxes = document.querySelectorAll(`.action-checkbox-${type}`);
    const isChecked = source.checked;

    checkboxes.forEach(cb => {
        cb.checked = isChecked;
        if (isChecked) {
            selectedActions.add(cb.value);
        } else {
            selectedActions.delete(cb.value);
        }
    });
    updateSelectAllState(); // Ensure indeterminate state is cleared
    updateRunButtons();
}

function toggleAction(action) {
    if (selectedActions.has(action)) {
        selectedActions.delete(action);
    } else {
        selectedActions.add(action);
    }
    updateSelectAllState();
    updateRunButtons();
}

function updateRunButtons() {
    const hasActions = selectedActions.size > 0;
    const runBtn = document.getElementById('run-btn');
    const dryRunBtn = document.getElementById('dry-run-btn');

    if (runBtn) runBtn.disabled = !hasActions;
    if (dryRunBtn) dryRunBtn.disabled = !hasActions;
}

async function runActions(dryRun) {
    ensureOutputPanelVisible();
    if (!currentReportPath) {
        appendOutput('warning', 'Please open a report first');
        showToast('⚠️ Please open a report first', 3000);
        return;
    }
    if (selectedActions.size === 0) {
        appendOutput('warning', 'Please select at least one action');
        showToast('⚠️ Please select at least one action', 3000);
        return;
    }

    // Confirmation for actual run
    if (!dryRun) {
        const confirmed = confirm(
            "Are you sure you want to run this?\n\n" +
            "This action cannot be undone from the application.\n" +
            "Please ensure you have a backup or the report is checked into git."
        );
        if (!confirmed) return;
    }

    const actions = Array.from(selectedActions).join(',');
    let url = `/api/reports/run/stream?path=${encodeURIComponent(currentReportPath)}` +
        `&actions=${encodeURIComponent(actions)}` +
        `&dry_run=${dryRun}`;

    // Pass custom config if loaded
    if (customConfigYaml) {
        const encoded = btoa(unescape(encodeURIComponent(customConfigYaml)));
        url += `&config_yaml=${encodeURIComponent(encoded)}`;
    }

    appendOutput('info', (dryRun ? '[DRY RUN] ' : '') + `Running: ${actions}`);

    const eventSource = new EventSource(url);

    eventSource.onmessage = event => {
        const data = JSON.parse(event.data);
        appendOutput(data.type || 'info', data.message);
    };

    eventSource.addEventListener('complete', async () => {
        eventSource.close();
        appendOutput('success', 'Actions completed');

        if (!dryRun) {
            showToast('✓ Actions completed. Reloading report...', 4000);
            await loadReport(currentReportPath, true);
            showToast('✓ Report refreshed', 4000);
        }
    });

    eventSource.onerror = () => {
        eventSource.close();
        setDirtyState(true, 'Action may have failed. Report might be in inconsistent state.');
        appendOutput('error', 'Connection lost');
    };
}

// ============ Validation ============

async function loadExpressionRules(reportPath) {
    if (!reportPath) return;
    try {
        const url = `/api/reports/validate/rules?report_path=${encodeURIComponent(reportPath)}`;
        const response = await fetch(url);
        const data = await response.json();
        expressionRules = data.rules || [];
        renderExpressionRules();
        document.getElementById('check-btn').disabled = false;
    } catch (e) {
        console.error('Failed to load validation rules:', e);
        expressionRules = [];
        renderExpressionRules();
    }
}

function renderExpressionRules() {
    const container = document.getElementById('rules-list');
    if (!container) return;

    if (!expressionRules.length) {
        container.innerHTML = '<div style="padding: 16px; color: var(--text-secondary); font-size: 12px;">No expression rules available</div>';
        return;
    }

    const html = expressionRules.map(r => {
        const desc = r.description || r.id.replace(/_/g, ' ');
        const badge = r.severity[0].toUpperCase();
        return `
            <div class="rule-item">
                <input type="checkbox" id="rule-${r.id}" value="${r.id}" checked>
                <label for="rule-${r.id}" style="flex:1;cursor:pointer;">${escapeHtml(desc)}</label>
                <span class="severity-badge ${r.severity}" title="Severity: ${r.severity}">${badge}</span>
            </div>`;
    }).join('');

    container.innerHTML = html;
}

async function runCheck() {
    ensureOutputPanelVisible();
    if (!currentReportPath) {
        showToast('⚠️ Please open a report first', 3000);
        return;
    }

    // Get selected expression rules
    const exprRules = Array.from(document.querySelectorAll('#rules-list input:checked')).map(cb => cb.value);
    // Get selected sanitize actions from ACTIONS panel
    let sanitizeActions = Array.from(selectedActions);
    // Check if sanitizer checks should be included
    const includeSanitizer = document.getElementById('include-sanitizer-checks')?.checked ?? true;

    // If not including sanitizer, clear the actions
    if (!includeSanitizer) {
        sanitizeActions = [];
    }

    if (exprRules.length === 0 && sanitizeActions.length === 0) {
        appendOutput('warning', 'No rules or actions selected for validation');
        return;
    }

    const btn = document.getElementById('check-btn');
    btn.disabled = true;
    btn.innerHTML = '⏳ Checking...';

    // Build SSE URL with query parameters
    let url = `/api/reports/validate/run/stream?report_path=${encodeURIComponent(currentReportPath)}`;

    if (exprRules.length > 0) {
        url += `&expression_rules=${encodeURIComponent(exprRules.join(','))}`;
    }
    if (sanitizeActions.length > 0) {
        url += `&sanitize_actions=${encodeURIComponent(sanitizeActions.join(','))}`;
    }
    url += `&include_sanitizer=${includeSanitizer}`;

    // Add custom rules config if loaded (base64 encoded)
    if (customRulesConfigYaml) {
        const encoded = btoa(unescape(encodeURIComponent(customRulesConfigYaml)));
        url += `&rules_config_yaml=${encodeURIComponent(encoded)}`;
    }

    // Add custom sanitize config if loaded from Actions panel (base64 encoded)
    if (customConfigYaml) {
        const encodedSanitize = btoa(unescape(encodeURIComponent(customConfigYaml)));
        url += `&sanitize_config_yaml=${encodeURIComponent(encodedSanitize)}`;
    }

    const eventSource = new EventSource(url);

    eventSource.onmessage = event => {
        const data = JSON.parse(event.data);
        const message = data.message || '';

        // Detect color type from message content (badges like [PASS], [WARNING], etc.)
        let type = data.type || 'info';
        if (message.indexOf('[PASS]') !== -1) {
            type = 'success';
        } else if (message.indexOf('[WARNING]') !== -1) {
            type = 'warning';
        } else if (message.indexOf('[ERROR]') !== -1) {
            type = 'error';
        } else if (message.indexOf('[INFO]') !== -1) {
            type = 'info';
        }

        appendOutput(type, message);
    };

    eventSource.addEventListener('complete', event => {
        eventSource.close();
        btn.disabled = false;
        btn.innerHTML = '✓ Check';
    });

    eventSource.onerror = () => {
        eventSource.close();
        appendOutput('error', 'Connection lost during validation');
        btn.disabled = false;
        btn.innerHTML = '✓ Check';
    };
}

async function loadCustomRulesConfig(input) {
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];

    // Read file content for later use during validation
    const yamlContent = await file.text();

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/api/reports/validate/config', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to load rules config');
        }

        const data = await response.json();

        // Store config for validation
        currentRulesConfigPath = file.name;
        customRulesConfigYaml = yamlContent;

        // Render new rules from config
        expressionRules = data.rules.map(r => ({
            id: r.id,
            description: r.description,
            severity: r.severity,
            scope: r.scope
        }));
        renderExpressionRules();
        updateRulesConfigIndicator();
        ensureOutputPanelVisible();
        appendOutput('success', `Loaded custom rules config: ${file.name}`);

    } catch (e) {
        ensureOutputPanelVisible();
        appendOutput('error', `Failed to load rules config: ${e.message}`);
    }

    // Reset file input so same file can be selected again
    input.value = '';
}

async function resetRulesConfig(event) {
    if (event) event.stopPropagation();
    currentRulesConfigPath = null;
    customRulesConfigYaml = null;
    await loadExpressionRules(currentReportPath);
    updateRulesConfigIndicator();
    appendOutput('info', 'Reset to default rules configuration');
}

function updateRulesConfigIndicator() {
    const indicator = document.getElementById('rules-config-indicator');
    if (indicator) {
        if (currentRulesConfigPath) {
            const fileName = currentRulesConfigPath.split(/[\\/]/).pop();
            indicator.innerHTML = `
                <span class="config-name">📄 ${fileName}</span>
                <span class="config-reset" onclick="resetRulesConfig(event)" title="Reset to Defaults">×</span>
            `;
            indicator.title = `Custom rules config: ${currentRulesConfigPath}`;
            indicator.style.display = 'inline-flex';
        } else {
            indicator.style.display = 'none';
        }
    }
}



// ============ CSV Export ============

function downloadCSV(type, filteredOnly) {
    if (!currentReportPath) return;

    let url = `/api/reports/${type === 'visuals' ? 'visuals' : 'metadata'}/csv` +
        `?report_path=${encodeURIComponent(currentReportPath)}`;

    // Add visual IDs filter if exporting filtered view (WYSIWYG)
    let isFiltered = false;
    if (filteredOnly && typeof getVisibleVisualIds === 'function' && typeof hasActiveFilters === 'function') {
        if (hasActiveFilters()) {
            const visibleIds = getVisibleVisualIds();
            if (visibleIds.length > 0) {
                url += `&visual_ids=${encodeURIComponent(visibleIds.join(','))}`;
                isFiltered = true;
            }
        }
    }

    window.open(url, '_blank');
    appendOutput('info', `Downloading ${type} CSV${isFiltered ? ' (filtered)' : ''}...`);
}

function downloadWireframeHTML(filteredOnly) {
    if (!currentReportPath) return;

    let url = `/api/reports/wireframe/html?report_path=${encodeURIComponent(currentReportPath)}`;

    // Add visual IDs filter if exporting filtered view (WYSIWYG)
    let isFiltered = false;
    if (filteredOnly && typeof getVisibleVisualIds === 'function' && typeof hasActiveFilters === 'function') {
        if (hasActiveFilters()) {
            const visibleIds = getVisibleVisualIds();
            if (visibleIds.length > 0) {
                url += `&visual_ids=${encodeURIComponent(visibleIds.join(','))}`;
                isFiltered = true;
            }
        }
    }

    window.open(url, '_blank');
    appendOutput('info', `Downloading wireframe HTML${isFiltered ? ' (filtered)' : ''}...`);
}

// ============ Output Console ============

function ensureOutputPanelVisible() {
    const panel = document.getElementById('output-panel');
    if (panel && panel.classList.contains('collapsed')) {
        panel.classList.remove('collapsed');
        savePanelState();
    }
}

function appendOutput(type, message) {
    const line = document.createElement('div');
    line.className = `output-line ${type}`;
    line.textContent = message;
    outputContent.appendChild(line);
    outputContent.scrollTop = outputContent.scrollHeight;
}

function clearOutput() {
    outputContent.innerHTML = '';
}

// ============ State Management ============

function setDirtyState(isDirty, message) {
    reportDirtyState = isDirty;
    if (isDirty) {
        dirtyBanner.textContent = `⚠️ ${message || 'Report may need reload'}`;
        dirtyBanner.style.display = 'block';
    } else {
        dirtyBanner.style.display = 'none';
    }
}

// ============ Resizing Logic ============

let isResizingOutput = false;
let isResizingSidebar = false;
let startResizeY = 0;
let startResizeX = 0;
let startResizeHeight = 0;
let startResizeWidth = 0;

function initOutputResize(e) {
    isResizingOutput = true;
    startResizeY = e.clientY;
    const panel = document.getElementById('output-panel');
    startResizeHeight = parseInt(getComputedStyle(panel).height, 10);
    document.body.style.cursor = 'row-resize';
    e.preventDefault();
}

function initSidebarResize(e) {
    isResizingSidebar = true;
    startResizeX = e.clientX;
    const sidebar = document.getElementById('sidebar');
    startResizeWidth = sidebar.getBoundingClientRect().width;
    sidebar.classList.remove('transition-enabled'); // Disable transition for drag
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
}

document.addEventListener('mousemove', e => {
    if (isResizingOutput) {
        const panel = document.getElementById('output-panel');
        let newHeight = startResizeHeight + (startResizeY - e.clientY);

        // Constraints
        if (newHeight < OUTPUT_PANEL_MIN_HEIGHT) newHeight = OUTPUT_PANEL_MIN_HEIGHT;
        if (newHeight > window.innerHeight * 0.8) newHeight = window.innerHeight * 0.8;

        panel.style.height = `${newHeight}px`;
    }

    if (isResizingSidebar) {
        const sidebar = document.getElementById('sidebar');
        let newWidth = startResizeWidth + (e.clientX - startResizeX);

        // Constraints
        if (newWidth < SIDEBAR_MIN_WIDTH) newWidth = SIDEBAR_MIN_WIDTH;
        if (newWidth > window.innerWidth * 0.5) newWidth = window.innerWidth * 0.5;

        sidebar.style.width = `${newWidth}px`;
    }
});

document.addEventListener('mouseup', () => {
    if (isResizingOutput) {
        isResizingOutput = false;
        document.body.style.cursor = 'default';
        savePanelState();
    }
    if (isResizingSidebar) {
        isResizingSidebar = false;
        document.body.style.cursor = 'default';
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.add('transition-enabled'); // Re-enable transition
        savePanelState();
    }
});

function toggleOutputPanel() {
    const panel = document.getElementById('output-panel');
    const btn = document.getElementById('output-toggle');
    const isCollapsed = panel.classList.toggle('collapsed');

    if (btn) {
        btn.setAttribute('aria-expanded', !isCollapsed);
        btn.setAttribute('aria-label', isCollapsed ? 'Expand Output Panel' : 'Collapse Output Panel');
    }
    savePanelState();
}

// ============ Sidebar Logic ============

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const btn = document.getElementById('sidebar-toggle');
    const isCollapsed = sidebar.classList.toggle('collapsed');

    if (btn) {
        btn.setAttribute('aria-expanded', !isCollapsed);
        btn.setAttribute('aria-label', isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar');
    }
    savePanelState();
}

function toggleSidebarSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) return;

    const header = section.querySelector('.sidebar-section-header');

    // Toggle collapsed state
    const isCollapsed = section.classList.toggle('collapsed');

    // Update ARIA attributes
    if (header) header.setAttribute('aria-expanded', !isCollapsed);

    // Save state preference if needed (optional)
    localStorage.setItem(`section-${sectionId}-collapsed`, isCollapsed);
}

function handleSectionKey(event, sectionId) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleSidebarSection(sectionId);
    }
}

function restoreSidebarSectionState() {
    ['section-reports', 'section-actions', 'section-validate', 'section-export'].forEach(id => {
        const isCollapsed = localStorage.getItem(`section-${id}-collapsed`) === 'true';
        if (isCollapsed) {
            const section = document.getElementById(id);
            if (section) {
                section.classList.add('collapsed');
                const header = section.querySelector('.sidebar-section-header');
                if (header) header.setAttribute('aria-expanded', 'false');
            }
        }
    });
}
// Call restore on load
restoreSidebarSectionState();

function savePanelState() {
    const panel = document.getElementById('output-panel');
    const sidebar = document.getElementById('sidebar');

    const state = {
        outputHeight: panel.style.height,
        outputCollapsed: panel.classList.contains('collapsed'),
        sidebarWidth: sidebar.style.width,
        sidebarCollapsed: sidebar.classList.contains('collapsed')
    };

    localStorage.setItem('uiLayout', JSON.stringify(state));
}

function loadPanelState() {
    const saved = localStorage.getItem('uiLayout');
    if (saved) {
        try {
            const state = JSON.parse(saved);
            const panel = document.getElementById('output-panel');
            const sidebar = document.getElementById('sidebar');
            const outputBtn = document.getElementById('output-toggle');
            const sidebarBtn = document.getElementById('sidebar-toggle');

            if (state.outputHeight) panel.style.height = state.outputHeight;

            if (state.outputCollapsed) {
                panel.classList.add('collapsed');
                if (outputBtn) {
                    outputBtn.setAttribute('aria-expanded', 'false');
                    outputBtn.setAttribute('aria-label', 'Expand Output Panel');
                }
            } else if (outputBtn) {
                outputBtn.setAttribute('aria-expanded', 'true');
                outputBtn.setAttribute('aria-label', 'Collapse Output Panel');
            }

            if (state.sidebarWidth) sidebar.style.width = state.sidebarWidth;

            if (state.sidebarCollapsed) {
                sidebar.classList.add('collapsed');
                if (sidebarBtn) {
                    sidebarBtn.setAttribute('aria-expanded', 'false');
                    sidebarBtn.setAttribute('aria-label', 'Expand Sidebar');
                }
            } else if (sidebarBtn) {
                sidebarBtn.setAttribute('aria-expanded', 'true');
                sidebarBtn.setAttribute('aria-label', 'Collapse Sidebar');
            }

        } catch (e) {
            console.error('Failed to load layout:', e);
        }
    }
}

// Load layout on startup
loadPanelState();
