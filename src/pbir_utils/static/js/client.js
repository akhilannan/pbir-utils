/**
 * PBIR-Utils UI Client JavaScript
 * Handles file browsing, action execution, and SSE streaming
 */

// Constants
var SIDEBAR_MIN_WIDTH = 150;
var OUTPUT_PANEL_MIN_HEIGHT = 50;

// State
var currentReportPath = null;
var selectedActions = new Set();
var reportDirtyState = false;
var fieldsIndex = null;
var activePageId = null;
var currentConfigPath = null;
var customConfigYaml = null;
var expressionRules = [];  // Validation rules
var customRulesConfigYaml = null;  // Custom rules YAML content
var currentRulesConfigPath = null;  // Custom rules config filename


// DOM Elements
var welcomeState = document.getElementById('welcome-state');
var wireframeContainer = document.getElementById('wireframe-container');
var outputContent = document.getElementById('output-content');
var dirtyBanner = document.getElementById('dirty-banner');

// Initialize
document.addEventListener('DOMContentLoaded', function () {
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
        var url = '/api/browse';
        if (path) {
            url += '?path=' + encodeURIComponent(path);
        }
        var response = await fetch(url);
        if (!response.ok) throw new Error('Failed to browse');
        var data = await response.json();
        renderFileList(data);
    } catch (e) {
        appendOutput('error', 'Failed to browse: ' + e.message);
    }
}

function renderFileList(data) {
    var breadcrumb = document.getElementById('breadcrumb');
    var fileList = document.getElementById('file-list');

    // Breadcrumb
    var crumbs = data.current_path.split(/[\/\\]/).filter(Boolean);
    var builtPath = '';
    breadcrumb.innerHTML = crumbs.map(function (crumb) {
        builtPath += crumb + '/';
        var safePath = builtPath.replace(/'/g, "\\'");
        return `<span class="breadcrumb-item" onclick="browseDirectory('${safePath}')">${crumb}</span>`;
    }).join(' / ');

    // Parent directory
    var html = '';
    if (data.parent_path) {
        var safeParent = data.parent_path.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
        html += `<div class="file-item" onclick="browseDirectory('${safeParent}')">📂 ..</div>`;
    }

    // Items
    html += data.items.map(function (item) {
        var icon = item.is_report ? '📊' : (item.is_dir ? '📁' : '📄');
        var isActive = currentReportPath && item.path === currentReportPath;
        var cls = `file-item${item.is_report ? ' report' : ''}${isActive ? ' active' : ''}`;

        var onclick = '';
        if (item.is_report || item.is_dir) {
            var safePath = item.path.replace(/'/g, "\\'").replace(/\\/g, '\\\\');
            var func = item.is_report ? 'loadReport' : 'browseDirectory';
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
        appendOutput('info', 'Loading report: ' + reportPath);

        // Save current selection if requested
        var savedActions = null;
        if (preserveActions) {
            savedActions = new Set(selectedActions);
        }

        var response = await fetch('/api/reports/wireframe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report_path: reportPath })
        });

        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to load');
        }

        var data = await response.json();
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
        appendOutput('success', 'Report loaded: ' + data.report_name);

        // Reload actions with report path to pick up report-specific config
        await loadActions(reportPath);

        // Restore selections if requested
        if (savedActions) {
            restoreActionSelection(savedActions);
        }

        // Load expression rules for validation
        await loadExpressionRules(reportPath);

        // Navigate file browser to show and highlight the loaded report
        var parentPath = reportPath.replace(/[\\/][^\\/]+$/, '');
        browseDirectory(parentPath);

    } catch (e) {
        appendOutput('error', 'Failed to load report: ' + e.message);
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
    var tooltipIds = ['tooltip', 'page-tooltip', 'field-tooltip', 'table-tooltip'];
    tooltipIds.forEach(function (id) {
        var el = document.getElementById(id);
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
    var savedTheme = localStorage.getItem('wireframeTheme');
    if (savedTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
    }
}

// ============ Actions ============


async function loadActions(reportPath) {
    try {
        var url = '/api/reports/actions';
        if (reportPath) {
            url += '?report_path=' + encodeURIComponent(reportPath);
        }
        var response = await fetch(url);
        var data = await response.json();
        currentConfigPath = data.config_path;
        customConfigYaml = null;  // Reset custom config when loading from report
        renderActions(data.actions);
        updateConfigIndicator();
    } catch (e) {
        appendOutput('error', 'Failed to load actions: ' + e.message);
    }
}

function renderActions(actions) {
    selectedActions.clear();
    var html = '';

    // Split actions
    var defaultActions = actions.filter(function (a) { return a.is_default; });
    var additionalActions = actions.filter(function (a) { return !a.is_default; });

    // --- Default Actions Section ---
    if (defaultActions.length > 0) {
        html += `
        <div class="action-group-header">
            <div class="action-item select-all-container" style="border-bottom: 1px solid var(--border-color); margin-bottom: 4px; padding-bottom: 8px;">
                <input type="checkbox" id="select-all-default" onchange="toggleGroup('default', this)">
                <label for="select-all-default" style="font-weight: 600;">Default Actions</label>
            </div>
        </div>`;

        html += defaultActions.map(function (action, i) {
            selectedActions.add(action.id); // Auto-select default
            var description = action.description || action.id.replace(/_/g, ' ');
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

        html += additionalActions.map(function (action, i) {
            var description = action.description || action.id.replace(/_/g, ' ');
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
    var checkboxes = document.querySelectorAll('.action-checkbox-default, .action-checkbox-additional');

    checkboxes.forEach(function (cb) {
        cb.checked = savedSet.has(cb.value);
        if (cb.checked) {
            selectedActions.add(cb.value);
        }
    });

    updateSelectAllState();
    updateRunButtons();
}

function updateConfigIndicator() {
    var indicator = document.getElementById('config-indicator');
    if (indicator) {
        if (currentConfigPath) {
            var fileName = currentConfigPath.split(/[\\/]/).pop();
            indicator.textContent = '📄 ' + fileName;
            indicator.title = 'Custom config: ' + currentConfigPath;
            indicator.style.display = 'inline-block';
        } else {
            indicator.style.display = 'none';
        }
    }
    // Show/hide reset button based on custom config
    var resetBtn = document.getElementById('reset-config-btn');
    if (resetBtn) {
        resetBtn.style.display = currentConfigPath ? 'block' : 'none';
    }
}

async function loadCustomConfig(input) {
    if (!input.files || !input.files[0]) return;

    var file = input.files[0];

    // Read file content for later use during execution
    var yamlContent = await file.text();

    var formData = new FormData();
    formData.append('file', file);

    try {
        var response = await fetch('/api/reports/config', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to load config');
        }

        var data = await response.json();

        // Store config for execution
        currentConfigPath = file.name;
        customConfigYaml = yamlContent;

        // Render new actions from config
        var actions = data.actions.map(function (id) {
            var def = data.definitions[id];
            return {
                id: id,
                description: def ? def.description : id.replace(/_/g, ' '),
                is_default: true
            };
        });
        renderActions(actions);
        updateConfigIndicator();
        appendOutput('success', 'Loaded custom config: ' + file.name);

    } catch (e) {
        appendOutput('error', 'Failed to load config: ' + e.message);
    }

    // Reset file input so same file can be selected again
    input.value = '';
}

async function resetConfig() {
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
    var checkboxes = Array.from(document.querySelectorAll('.action-checkbox-' + type));
    var selectAll = document.getElementById('select-all-' + type);

    if (!checkboxes.length || !selectAll) return;

    var allChecked = checkboxes.every(function (cb) { return cb.checked; });
    var anyChecked = checkboxes.some(function (cb) { return cb.checked; });

    selectAll.checked = allChecked;
    selectAll.indeterminate = !allChecked && anyChecked;
}

function toggleGroup(type, source) {
    var checkboxes = document.querySelectorAll('.action-checkbox-' + type);
    var isChecked = source.checked;

    checkboxes.forEach(function (cb) {
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
    var hasActions = selectedActions.size > 0;
    var runBtn = document.getElementById('run-btn');
    var dryRunBtn = document.getElementById('dry-run-btn');

    if (runBtn) runBtn.disabled = !hasActions;
    if (dryRunBtn) dryRunBtn.disabled = !hasActions;
}

async function runActions(dryRun) {
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
        var confirmed = confirm(
            "Are you sure you want to run this?\n\n" +
            "This action cannot be undone from the application.\n" +
            "Please ensure you have a backup or the report is checked into git."
        );
        if (!confirmed) return;
    }

    var actions = Array.from(selectedActions).join(',');
    var url = '/api/reports/run/stream?path=' + encodeURIComponent(currentReportPath) +
        '&actions=' + encodeURIComponent(actions) +
        '&dry_run=' + dryRun;

    // Pass custom config if loaded
    if (customConfigYaml) {
        var encoded = btoa(unescape(encodeURIComponent(customConfigYaml)));
        url += '&config_yaml=' + encodeURIComponent(encoded);
    }

    appendOutput('info', (dryRun ? '[DRY RUN] ' : '') + 'Running: ' + actions);

    var eventSource = new EventSource(url);

    eventSource.onmessage = function (event) {
        var data = JSON.parse(event.data);
        appendOutput(data.type || 'info', data.message);
    };

    eventSource.addEventListener('complete', async function () {
        eventSource.close();
        appendOutput('success', 'Actions completed');

        if (!dryRun) {
            showToast('✓ Actions completed. Reloading report...', 4000);
            await loadReport(currentReportPath, true);
            showToast('✓ Report refreshed', 4000);
        }
    });

    eventSource.onerror = function () {
        eventSource.close();
        setDirtyState(true, 'Action may have failed. Report might be in inconsistent state.');
        appendOutput('error', 'Connection lost');
    };
}

// ============ Validation ============

async function loadExpressionRules(reportPath) {
    if (!reportPath) return;
    try {
        var url = '/api/reports/validate/rules?report_path=' + encodeURIComponent(reportPath);
        var response = await fetch(url);
        var data = await response.json();
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
    var container = document.getElementById('rules-list');
    if (!container) return;

    if (!expressionRules.length) {
        container.innerHTML = '<div style="padding: 16px; color: var(--text-secondary); font-size: 12px;">No expression rules available</div>';
        return;
    }

    var html = expressionRules.map(function (r) {
        var desc = r.description || r.id.replace(/_/g, ' ');
        var badge = r.severity[0].toUpperCase();
        return `
            <div class="rule-item">
                <input type="checkbox" id="rule-${r.id}" value="${r.id}" checked>
                <label for="rule-${r.id}" style="flex:1;cursor:pointer;">${escapeHtml(desc)}</label>
                <span class="severity-badge ${r.severity}">${badge}</span>
            </div>`;
    }).join('');

    container.innerHTML = html;
}

async function runCheck() {
    if (!currentReportPath) {
        showToast('⚠️ Please open a report first', 3000);
        return;
    }

    // Get selected expression rules
    var exprRules = Array.from(document.querySelectorAll('#rules-list input:checked')).map(function (cb) { return cb.value; });
    // Get selected sanitize actions from ACTIONS panel
    var sanitizeActions = Array.from(selectedActions);
    // Check if sanitizer checks should be included
    var includeSanitizer = document.getElementById('include-sanitizer-checks')?.checked ?? true;

    // If not including sanitizer, clear the actions
    if (!includeSanitizer) {
        sanitizeActions = [];
    }

    if (exprRules.length === 0 && sanitizeActions.length === 0) {
        showValidationToast(0, 0, 0, 0, 'warning');
        appendOutput('warning', 'No rules or actions selected for validation');
        return;
    }

    var btn = document.getElementById('check-btn');
    btn.disabled = true;
    btn.innerHTML = '⏳ Checking...';

    // Build SSE URL with query parameters
    var url = '/api/reports/validate/run/stream?report_path=' + encodeURIComponent(currentReportPath);

    if (exprRules.length > 0) {
        url += '&expression_rules=' + encodeURIComponent(exprRules.join(','));
    }
    if (sanitizeActions.length > 0) {
        url += '&sanitize_actions=' + encodeURIComponent(sanitizeActions.join(','));
    }
    url += '&include_sanitizer=' + includeSanitizer;

    // Add custom rules config if loaded (base64 encoded)
    if (customRulesConfigYaml) {
        var encoded = btoa(unescape(encodeURIComponent(customRulesConfigYaml)));
        url += '&rules_config_yaml=' + encodeURIComponent(encoded);
    }

    // Add custom sanitize config if loaded from Actions panel (base64 encoded)
    if (customConfigYaml) {
        var encodedSanitize = btoa(unescape(encodeURIComponent(customConfigYaml)));
        url += '&sanitize_config_yaml=' + encodeURIComponent(encodedSanitize);
    }

    var eventSource = new EventSource(url);

    eventSource.onmessage = function (event) {
        var data = JSON.parse(event.data);
        var message = data.message || '';

        // Detect color type from message content (badges like [PASS], [WARNING], etc.)
        var type = data.type || 'info';
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

    eventSource.addEventListener('complete', function (event) {
        eventSource.close();
        var summary = JSON.parse(event.data);

        showValidationToast(summary.passed, summary.failed, summary.warning_count, summary.error_count);

        btn.disabled = false;
        btn.innerHTML = '✓ Check';
    });

    eventSource.onerror = function () {
        eventSource.close();
        appendOutput('error', 'Connection lost during validation');
        btn.disabled = false;
        btn.innerHTML = '✓ Check';
    };
}

async function loadCustomRulesConfig(input) {
    if (!input.files || !input.files[0]) return;

    var file = input.files[0];

    // Read file content for later use during validation
    var yamlContent = await file.text();

    var formData = new FormData();
    formData.append('file', file);

    try {
        var response = await fetch('/api/reports/validate/config', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            var error = await response.json();
            throw new Error(error.detail || 'Failed to load rules config');
        }

        var data = await response.json();

        // Store config for validation
        currentRulesConfigPath = file.name;
        customRulesConfigYaml = yamlContent;

        // Render new rules from config
        expressionRules = data.rules.map(function (r) {
            return {
                id: r.id,
                description: r.description,
                severity: r.severity,
                scope: r.scope
            };
        });
        renderExpressionRules();
        updateRulesConfigIndicator();
        appendOutput('success', 'Loaded custom rules config: ' + file.name);

    } catch (e) {
        appendOutput('error', 'Failed to load rules config: ' + e.message);
    }

    // Reset file input so same file can be selected again
    input.value = '';
}

async function resetRulesConfig() {
    currentRulesConfigPath = null;
    customRulesConfigYaml = null;
    await loadExpressionRules(currentReportPath);
    updateRulesConfigIndicator();
    appendOutput('info', 'Reset to default rules configuration');
}

function updateRulesConfigIndicator() {
    var indicator = document.getElementById('rules-config-indicator');
    if (indicator) {
        if (currentRulesConfigPath) {
            indicator.textContent = '📄 ' + currentRulesConfigPath;
            indicator.title = 'Custom config: ' + currentRulesConfigPath;
            indicator.style.display = 'inline-block';
        } else {
            indicator.style.display = 'none';
        }
    }
    // Show/hide reset button based on custom config
    var resetBtn = document.getElementById('reset-rules-config-btn');
    if (resetBtn) {
        resetBtn.style.display = currentRulesConfigPath ? 'block' : 'none';
    }
}

function showValidationToast(passed, failed, warnings, errors) {
    // Remove existing validation toast
    var existing = document.querySelector('.validation-toast');
    if (existing) existing.remove();

    var type = errors > 0 ? 'error' : (failed > 0 ? 'warning' : 'success');
    var toast = document.createElement('div');
    toast.className = 'validation-toast ' + type;
    toast.innerHTML =
        '<div style="font-weight:600;margin-bottom:4px;">Validation Complete</div>' +
        '<div>✓ ' + passed + ' passed &nbsp; ✗ ' + failed + ' failed</div>' +
        (errors ? '<div style="color:var(--error-color);">🔴 ' + errors + ' error(s)</div>' : '') +
        (warnings ? '<div style="color:var(--warning-color);">🟡 ' + warnings + ' warning(s)</div>' : '');
    document.body.appendChild(toast);
    setTimeout(function () { toast.remove(); }, 5000);
}

// ============ CSV Export ============

function downloadCSV(type, filteredOnly) {
    if (!currentReportPath) return;

    var url = '/api/reports/' + (type === 'visuals' ? 'visuals' : 'metadata') + '/csv' +
        '?report_path=' + encodeURIComponent(currentReportPath);

    // Add visual IDs filter if exporting filtered view (WYSIWYG)
    var isFiltered = false;
    if (filteredOnly && typeof getVisibleVisualIds === 'function' && typeof hasActiveFilters === 'function') {
        if (hasActiveFilters()) {
            var visibleIds = getVisibleVisualIds();
            if (visibleIds.length > 0) {
                url += '&visual_ids=' + encodeURIComponent(visibleIds.join(','));
                isFiltered = true;
            }
        }
    }

    window.open(url, '_blank');
    appendOutput('info', 'Downloading ' + type + ' CSV' + (isFiltered ? ' (filtered)' : '') + '...');
}

function downloadWireframeHTML(filteredOnly) {
    if (!currentReportPath) return;

    var url = '/api/reports/wireframe/html?report_path=' + encodeURIComponent(currentReportPath);

    // Add visual IDs filter if exporting filtered view (WYSIWYG)
    var isFiltered = false;
    if (filteredOnly && typeof getVisibleVisualIds === 'function' && typeof hasActiveFilters === 'function') {
        if (hasActiveFilters()) {
            var visibleIds = getVisibleVisualIds();
            if (visibleIds.length > 0) {
                url += '&visual_ids=' + encodeURIComponent(visibleIds.join(','));
                isFiltered = true;
            }
        }
    }

    window.open(url, '_blank');
    appendOutput('info', 'Downloading wireframe HTML' + (isFiltered ? ' (filtered)' : '') + '...');
}

// ============ Output Console ============

function appendOutput(type, message) {
    var line = document.createElement('div');
    line.className = 'output-line ' + type;
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
        dirtyBanner.textContent = '⚠️ ' + (message || 'Report may need reload');
        dirtyBanner.style.display = 'block';
    } else {
        dirtyBanner.style.display = 'none';
    }
}

// ============ Resizing Logic ============

var isResizingOutput = false;
var isResizingSidebar = false;
var startResizeY = 0;
var startResizeX = 0;
var startResizeHeight = 0;
var startResizeWidth = 0;

function initOutputResize(e) {
    isResizingOutput = true;
    startResizeY = e.clientY;
    var panel = document.getElementById('output-panel');
    startResizeHeight = parseInt(getComputedStyle(panel).height, 10);
    document.body.style.cursor = 'row-resize';
    e.preventDefault();
}

function initSidebarResize(e) {
    isResizingSidebar = true;
    startResizeX = e.clientX;
    var sidebar = document.getElementById('sidebar');
    startResizeWidth = sidebar.getBoundingClientRect().width;
    sidebar.classList.remove('transition-enabled'); // Disable transition for drag
    document.body.style.cursor = 'col-resize';
    e.preventDefault();
}

document.addEventListener('mousemove', function (e) {
    if (isResizingOutput) {
        var panel = document.getElementById('output-panel');
        var newHeight = startResizeHeight + (startResizeY - e.clientY);

        // Constraints
        if (newHeight < OUTPUT_PANEL_MIN_HEIGHT) newHeight = OUTPUT_PANEL_MIN_HEIGHT;
        if (newHeight > window.innerHeight - 100) newHeight = window.innerHeight - 100;

        panel.style.height = newHeight + 'px';
    } else if (isResizingSidebar) {
        var newWidth = startResizeWidth + (e.clientX - startResizeX);

        // Constraints
        if (newWidth < SIDEBAR_MIN_WIDTH) newWidth = SIDEBAR_MIN_WIDTH;
        if (newWidth > window.innerWidth - 100) newWidth = window.innerWidth - 100;

        document.documentElement.style.setProperty('--sidebar-width', newWidth + 'px');
    }
});

document.addEventListener('mouseup', function (e) {
    if (isResizingOutput) {
        isResizingOutput = false;
        document.body.style.cursor = '';
        savePanelState();
    } else if (isResizingSidebar) {
        isResizingSidebar = false;
        document.body.style.cursor = '';
        var sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('transition-enabled');
        savePanelState();
    }
});



// ============ Collapsible Panels ============

function toggleSidebarSection(sectionId) {
    var section = document.getElementById(sectionId);
    if (section) {
        section.classList.toggle('collapsed');
        savePanelState();
    }
}

function toggleOutputPanel(event) {
    // Don't toggle if clicking the Clear button
    if (event && event.target.tagName === 'BUTTON' && !event.target.classList.contains('output-toggle')) return;

    var panel = document.getElementById('output-panel');
    if (panel) {
        panel.classList.toggle('collapsed');
        savePanelState();
    }
}

function savePanelState() {
    var outputPanel = document.getElementById('output-panel');
    var sidebar = document.getElementById('sidebar');
    var sidebarWidth = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width').trim();

    var state = {
        reports: document.getElementById('section-reports')?.classList.contains('collapsed'),
        actions: document.getElementById('section-actions')?.classList.contains('collapsed'),
        validate: document.getElementById('section-validate')?.classList.contains('collapsed'),
        export: document.getElementById('section-export')?.classList.contains('collapsed'),
        output: outputPanel?.classList.contains('collapsed'),
        sidebar: sidebar?.classList.contains('collapsed'),
        outputHeight: outputPanel ? outputPanel.style.height : null,
        sidebarWidth: sidebarWidth
    };
    localStorage.setItem('pbirUtilsPanelState', JSON.stringify(state));
}

function restorePanelState() {
    try {
        var saved = localStorage.getItem('pbirUtilsPanelState');
        if (saved) {
            var state = JSON.parse(saved);
            if (state.reports) document.getElementById('section-reports')?.classList.add('collapsed');
            if (state.actions) document.getElementById('section-actions')?.classList.add('collapsed');
            if (state.validate) document.getElementById('section-validate')?.classList.add('collapsed');
            if (state.export) document.getElementById('section-export')?.classList.add('collapsed');

            var outputPanel = document.getElementById('output-panel');
            if (state.output) {
                outputPanel?.classList.add('collapsed');
            } else if (state.outputHeight && outputPanel) {
                outputPanel.style.height = state.outputHeight;
            }

            if (state.sidebarWidth) {
                document.documentElement.style.setProperty('--sidebar-width', state.sidebarWidth);
            }

            if (state.sidebar) document.getElementById('sidebar')?.classList.add('collapsed');
        }
    } catch (e) {
        // Ignore localStorage errors
    }
}

function toggleSidebar() {
    var sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
        savePanelState();
    }
}

function showToast(message, duration) {
    duration = duration || 4000;
    var toast = document.getElementById('toast');
    if (!toast) return; // Toast not available yet
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(function () {
        toast.classList.remove('show');
    }, duration);
}

// Restore panel states on load
document.addEventListener('DOMContentLoaded', restorePanelState);
