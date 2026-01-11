// Mode detection: API mode loads data dynamically from backend
// API_MODE is defined in the template


// Constants
const MIN_ZOOM = 0.25;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.25;
const FIELDS_PANE_MIN_WIDTH = 200;
const FIELDS_PANE_MAX_WIDTH = 600;
const SEARCH_DEBOUNCE_MS = 150;

// State
let currentZoom = 1;
let initialPageLoaded = false;

/* Performance: Cached DOM References */
let cachedVisuals = null;
let cachedTabs = null;
const escapeDiv = document.createElement('div');

function getCachedVisuals() {
    if (!cachedVisuals) {
        cachedVisuals = Array.from(document.getElementsByClassName('visual-box'));
    }
    return cachedVisuals;
}

function getCachedTabs() {
    if (!cachedTabs) {
        cachedTabs = Array.from(document.getElementsByClassName('tab-button'));
    }
    return cachedTabs;
}

/* Global UI Elements */
let tooltip = document.getElementById('tooltip');
let pageTooltip = document.getElementById('page-tooltip');
let fieldTooltip = document.getElementById('field-tooltip');
let tableTooltip = document.getElementById('table-tooltip');

function openPage(pageId, skipTracking) {
    // Get current page before switching (for undo tracking)
    const currentActivePage = document.querySelector('.page-container.active');
    const previousPageId = currentActivePage ? currentActivePage.id : null;

    document.querySelectorAll('.page-container.active, .tab-button.active').forEach(el => {
        el.classList.remove('active');
    });

    const page = document.getElementById(pageId);
    if (page) page.classList.add("active");

    const tab = document.getElementById(`tab-${pageId}`);
    if (tab) tab.classList.add("active");

    applyZoom();

    // Track page change for undo (skip on initial load and when undoing/resetting)
    if (initialPageLoaded && !skipTracking && previousPageId && previousPageId !== pageId) {
        trackAction('pageChange', { previousPageId });
    }

    initialPageLoaded = true;
}

/* Zoom Controls */
function zoomIn() {
    if (currentZoom < MAX_ZOOM) {
        currentZoom = Math.min(MAX_ZOOM, currentZoom + ZOOM_STEP);
        applyZoom();
    }
}

function zoomOut() {
    if (currentZoom > MIN_ZOOM) {
        currentZoom = Math.max(MIN_ZOOM, currentZoom - ZOOM_STEP);
        applyZoom();
    }
}

function resetZoom() {
    currentZoom = 1;
    applyZoom();
}

function applyZoom() {
    const activePage = document.querySelector('.page-container.active');
    if (activePage) {
        activePage.style.transform = `scale(${currentZoom})`;
    }
    document.getElementById('zoom-level').textContent = `${Math.round(currentZoom * 100)}%`;
}

/* Theme Toggle */
function toggleTheme() {
    const body = document.body;
    const btn = document.getElementById('theme-btn');
    if (body.getAttribute('data-theme') === 'dark') {
        body.removeAttribute('data-theme');
        btn.textContent = '🌙';
        localStorage.setItem('wireframe-theme', 'light');
    } else {
        body.setAttribute('data-theme', 'dark');
        btn.textContent = '☀️';
        localStorage.setItem('wireframe-theme', 'dark');
    }
}

// Load saved theme on page load
(() => {
    const savedTheme = localStorage.getItem('wireframe-theme');
    if (savedTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        document.getElementById('theme-btn').textContent = '☀️';
    }
})();

/* Interactivity Functions */

let hiddenStack = [];
let hiddenPagesStack = [];

function updateButtons() {
    const hasHiddenItems = hiddenStack.length > 0 || hiddenPagesStack.length > 0;
    document.getElementById('undo-btn').disabled = hiddenStack.length === 0;
    document.getElementById('reset-btn').disabled = !hasHiddenItems;

    // Update hidden pages pill
    const pagePill = document.getElementById('hidden-pages-pill');
    if (hiddenPagesStack.length > 0) {
        pagePill.textContent = `+${hiddenPagesStack.length} page${hiddenPagesStack.length > 1 ? 's' : ''}`;
        pagePill.classList.add('visible');
    } else {
        pagePill.classList.remove('visible');
    }

    // Update hidden visuals pill
    const visualPill = document.getElementById('hidden-visuals-pill');
    if (hiddenStack.length > 0) {
        visualPill.textContent = `+${hiddenStack.length} visual${hiddenStack.length > 1 ? 's' : ''}`;
        visualPill.classList.add('visible');
    } else {
        visualPill.classList.remove('visible');
    }
}

function hidePage(event, pageId) {
    event.preventDefault();
    hidePageTooltip();

    // Count visible tabs
    const tabs = document.querySelectorAll('.tab-button');
    let visibleCount = 0;
    tabs.forEach(tab => {
        if (tab.style.display !== 'none') visibleCount++;
    });

    // Don't hide if it's the last visible page
    if (visibleCount <= 1) {
        return;
    }

    const tab = document.getElementById(`tab-${pageId}`);

    // If hiding active page, switch to next visible one first
    if (tab && tab.classList.contains('active')) {
        let nextTab = null;
        let foundCurrent = false;
        tabs.forEach(t => {
            if (t === tab) {
                foundCurrent = true;
            } else if (foundCurrent && !nextTab && t.style.display !== 'none') {
                nextTab = t;
            }
        });
        // If no next tab, find previous
        if (!nextTab) {
            tabs.forEach(t => {
                if (t !== tab && t.style.display !== 'none') {
                    nextTab = t;
                }
            });
        }
        if (nextTab) {
            nextTab.click();
        }
    }

    // Hide the tab
    if (tab) {
        tab.style.display = 'none';
        hiddenPagesStack.push(pageId);
    }

    updateButtons();
}

function resetHiddenPages() {
    hiddenPagesStack = [];
    // Re-apply filters
    filterVisuals();
    updateButtons();
}

function copyVisualId(visualId) {
    navigator.clipboard.writeText(visualId).then(() => {
        showToast('ID Copied!');
    }, err => {
        console.error('Async: Could not copy text: ', err);
    });
}

function showToast(message) {
    const toast = document.getElementById("toast");
    if (message) toast.textContent = message;
    toast.className = "toast show";
    setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 2000);
}

function hideVisual(event, visualId) {
    event.preventDefault();
    const el = document.getElementById(`visual-${visualId}`);
    if (el) {
        el.style.opacity = "0";
        el.style.pointerEvents = "none";
        el.dataset.manuallyHidden = "true";

        hiddenStack.push(visualId);
        // Track in actionStack so undo respects the order of all actions
        trackAction('hideVisual', { visualId });
        updateButtons();
    }
    hideTooltip();
}

function undoHideVisual() {
    if (hiddenStack.length === 0) return;

    const visualId = hiddenStack.pop();
    const el = document.getElementById(`visual-${visualId}`);
    if (el) {
        checkVisualFilterState(el);
        el.style.pointerEvents = "auto";
        el.dataset.manuallyHidden = "false";
    }
    updateButtons();
}

function resetHiddenVisuals() {
    const hiddenElements = document.querySelectorAll('[data-manually-hidden="true"]');
    hiddenElements.forEach(el => {
        checkVisualFilterState(el);
        el.style.pointerEvents = "auto";
        el.dataset.manuallyHidden = "false";
    });
    hiddenStack = [];

    updateButtons();
}

// Action tracking for undo
let actionStack = [];

function trackAction(actionType, data) {
    actionStack.push({ type: actionType, data });
    updateResetButtonState();
}

function undoLastAction() {
    if (actionStack.length === 0) {
        // Fallback to old behavior for hidden visuals
        undoHideVisual();
        return;
    }

    const lastAction = actionStack.pop();

    switch (lastAction.type) {
        case 'hideVisual':
            // Use the specific visualId from the action, not blindly pop from hiddenStack
            const visualId = lastAction.data.visualId;
            const el = document.getElementById(`visual-${visualId}`);
            if (el) {
                checkVisualFilterState(el);
                el.style.pointerEvents = "auto";
                el.dataset.manuallyHidden = "false";
            }
            // Remove from hiddenStack by value
            const idx = hiddenStack.indexOf(visualId);
            if (idx > -1) {
                hiddenStack.splice(idx, 1);
            }
            updateButtons();
            break;
        case 'search':
            document.getElementById('search-input').value = lastAction.data.previousValue || '';
            filterVisuals();
            break;
        case 'fieldsSearch':
            document.getElementById('fields-search').value = lastAction.data.previousValue || '';
            searchFields();
            break;
        case 'visibilityFilter':
            visibilityFilter = lastAction.data.previousValue;
            document.querySelectorAll('.filter-toggle').forEach(btn => {
                btn.classList.remove('active');
            });
            if (visibilityFilter) {
                document.getElementById(`filter-${visibilityFilter}`).classList.add('active');
            }
            filterVisuals();
            break;
        case 'fieldSelection':
            if (lastAction.data.wasSelected) {
                selectedFields.add(lastAction.data.fieldKey);
            } else {
                selectedFields.delete(lastAction.data.fieldKey);
            }
            const fieldItem = document.querySelector(`.field-item[data-field="${lastAction.data.fieldKey}"]`);
            if (fieldItem) {
                fieldItem.classList.toggle('selected', lastAction.data.wasSelected);
            }
            updateFieldsFooter();
            applyFieldFilters();
            break;
        case 'batchFieldSelection':
            lastAction.data.changes.forEach(change => {
                if (change.wasSelected) {
                    selectedFields.add(change.key);
                } else {
                    selectedFields.delete(change.key);
                }
                const fieldItem = document.querySelector(`.field-item[data-field="${change.key}"]`);
                if (fieldItem) {
                    fieldItem.classList.toggle('selected', change.wasSelected);
                }
            });
            updateFieldsFooter();
            applyFieldFilters();
            break;
        case 'pageChange':
            openPage(lastAction.data.previousPageId, true);
            break;
    }

    updateResetButtonState();
}

function resetAllFilters() {
    // 1. Clear visual search
    document.getElementById('search-input').value = '';

    // 2. Clear fields search
    document.getElementById('fields-search').value = '';

    // 3. Clear visibility filter
    visibilityFilter = null;
    document.querySelectorAll('.filter-toggle').forEach(btn => {
        btn.classList.remove('active');
    });

    // 4. Clear field selections
    selectedFields.clear();
    document.querySelectorAll('.field-item.selected').forEach(el => {
        el.classList.remove('selected');
    });
    updateFieldsFooter();

    // 5. Reset hidden visuals
    resetHiddenVisuals();

    // 6. Reset field list display
    document.querySelectorAll('.table-item').forEach(tableItem => {
        tableItem.style.display = '';
        tableItem.classList.remove('expanded');
        tableItem.querySelectorAll('.field-item').forEach(fieldItem => {
            fieldItem.style.display = '';
        });
    });

    // 7. Clear action stack
    actionStack = [];

    // 8. Apply filters (will show all)
    filterVisuals();

    // 9. Reset to initial active page
    if (typeof activePageId !== 'undefined' && activePageId) {
        openPage(activePageId, true);
    }

    updateResetButtonState();
}

function updateResetButtonState() {
    // Check if current page differs from initial active page
    const currentPage = document.querySelector('.page-container.active');
    const currentPageId = currentPage ? currentPage.id : null;
    const pageChanged = typeof activePageId !== 'undefined' && activePageId && currentPageId !== activePageId;

    const hasFilters =
        document.getElementById('search-input').value !== '' ||
        document.getElementById('fields-search').value !== '' ||
        visibilityFilter !== null ||
        selectedFields.size > 0 ||
        hiddenStack.length > 0 ||
        hiddenPagesStack.length > 0 ||
        pageChanged;

    document.getElementById('reset-btn').disabled = !hasFilters;
    document.getElementById('undo-btn').disabled = actionStack.length === 0 && hiddenStack.length === 0;
}

function setVisualVisibility(visual, isVisible) {
    if (isVisible) {
        visual.style.opacity = "1";
        visual.style.pointerEvents = "auto";
    } else {
        visual.style.opacity = "0.1";
        visual.style.pointerEvents = "none";
    }
}

function isMatch(visual, filter) {
    if (!filter) return true;
    const ds = visual.dataset;
    const pageName = visual.parentElement.dataset.pageName || "";
    return ds.id.toLowerCase().includes(filter) ||
        ds.type.toLowerCase().includes(filter) ||
        pageName.includes(filter);
}

function checkVisualFilterState(visual) {
    const filter = document.getElementById('search-input').value.toLowerCase();
    setVisualVisibility(visual, isMatch(visual, filter));
}

let visibilityFilter = null; // null = all, 'hidden' = only hidden, 'visible' = only visible

function toggleVisibilityFilter(mode) {
    const hiddenBtn = document.getElementById('filter-hidden');
    const visibleBtn = document.getElementById('filter-visible');

    if (visibilityFilter === mode) {
        // Clicking active filter deactivates it
        visibilityFilter = null;
        hiddenBtn.classList.remove('active');
        visibleBtn.classList.remove('active');
    } else {
        // Activate the clicked filter, deactivate the other
        visibilityFilter = mode;
        hiddenBtn.classList.toggle('active', mode === 'hidden');
        visibleBtn.classList.toggle('active', mode === 'visible');
    }

    filterVisuals();
    updateResetButtonState();
}

function matchesVisibilityFilter(visual) {
    if (visibilityFilter === null) return true;
    const isHidden = visual.classList.contains('hidden');
    if (visibilityFilter === 'hidden') return isHidden;
    if (visibilityFilter === 'visible') return !isHidden;
    return true;
}

/* Helper function to update tab visibility based on matching pages */
function updateTabVisibility(pagesWithMatchingVisuals, noFiltersActive, searchFilter) {
    getCachedTabs().forEach(tab => {
        const pageName = tab.dataset.pageName.toLowerCase();
        const pageId = tab.id.replace("tab-", "");

        // Check if page is explicitly hidden by user
        const isManuallyHidden = hiddenPagesStack.indexOf(pageId) !== -1;

        if (isManuallyHidden) {
            tab.style.display = "none";
            return;
        }

        // Only check page name match if there's actual search text
        const matchesName = searchFilter && pageName.includes(searchFilter);
        if (noFiltersActive || matchesName || pagesWithMatchingVisuals.has(pageId)) {
            tab.style.display = "";
        } else {
            tab.style.display = "none";
        }
    });
}

/* Helper function to check if visual matches field filters */
function checkFieldMatch(visual, matchingVisualIds, matchingFieldKeys) {
    // If no field filters active, always match
    if (!matchingVisualIds && !matchingFieldKeys) return true;

    // Check by visual ID (from selected fields)
    if (matchingVisualIds && matchingVisualIds.has(visual.dataset.id)) {
        return true;
    }

    // Check by field keys (from field search)
    if (matchingFieldKeys) {
        let visualFields = [];
        try {
            visualFields = JSON.parse(visual.dataset.fields || '[]');
        } catch (e) { }
        return visualFields.some(f => matchingFieldKeys.has(f));
    }

    return false;
}

function filterVisualsBase() {
    const filter = document.getElementById('search-input').value.toLowerCase();
    const visuals = getCachedVisuals();
    const pagesWithMatchingVisuals = new Set();
    const noFiltersActive = !filter && visibilityFilter === null;

    // Filter Visuals & Track Matching Pages
    visuals.forEach(visual => {
        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") return;

        const matchesSearch = isMatch(visual, filter);
        const matchesVis = matchesVisibilityFilter(visual);
        const match = matchesSearch && matchesVis;

        setVisualVisibility(visual, match);

        if (match) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    });

    // Update tab visibility using helper
    updateTabVisibility(pagesWithMatchingVisuals, noFiltersActive, filter);

    // Auto-switch to first visible page if current page has no matching visuals
    if (!noFiltersActive) {
        switchToFirstVisiblePage(pagesWithMatchingVisuals);
    }

    // Update reset button state
    updateResetButtonState();
}

/* Main filter function - routes to appropriate filter based on state */
function filterVisuals() {
    if (selectedFields.size > 0) {
        applyFieldFilters();
    } else {
        filterVisualsBase();
    }
}

function showTooltip(e, visualElement) {
    const type = visualElement.dataset.type;
    const id = visualElement.dataset.id;
    const width = Math.round(parseFloat(visualElement.dataset.width));
    const height = Math.round(parseFloat(visualElement.dataset.height));
    const x = Math.round(parseFloat(visualElement.dataset.x));
    const y = Math.round(parseFloat(visualElement.dataset.y));
    const parent = visualElement.dataset.parentGroup || '';
    const isHidden = visualElement.classList.contains('hidden');

    let content = `<strong>${type}</strong>${isHidden ? ' <span style="color:var(--hidden-visual-border)">(Hidden)</span>' : ''}<br>ID: ${id}`;
    content += `<br><span style='color:var(--text-secondary)'>Size:</span> ${width} × ${height} px`;
    content += `<br><span style='color:var(--text-secondary)'>Position:</span> X: ${x}, Y: ${y}`;
    if (parent && parent !== 'None' && parent !== '') {
        content += `<br><span style='color:var(--text-secondary)'>Parent:</span> ${parent}`;
    }
    content += `<br><span style='font-size:10px; color:#aaa'>Left click to copy ID · Right click to hide</span>`;
    tooltip.innerHTML = content;
    tooltip.style.display = 'block';
    moveTooltip(e);
}

function moveTooltip(e) {
    const xOffset = 15;
    const yOffset = 15;
    tooltip.style.left = `${e.clientX + xOffset}px`;
    tooltip.style.top = `${e.clientY + yOffset}px`;
}

function hideTooltip() {
    tooltip.style.display = 'none';
}

/* Page Tooltip Functions */
function showPageTooltip(e, tabElement) {
    const pageName = tabElement.dataset.pageName;
    const visualCount = tabElement.dataset.visualCount;
    const isHidden = tabElement.dataset.isHidden === 'True';
    let visualTypes = {};

    try {
        visualTypes = JSON.parse(tabElement.dataset.visualTypes || '{}');
    } catch (err) {
        visualTypes = {};
    }

    let content = `<h4>${pageName}${isHidden ? ' <span style="color:var(--hidden-visual-border)">(Hidden)</span>' : ''}</h4>`;
    content += `<div class="stat-row"><span class="stat-label">Page Size:</span><span class="stat-value">${tabElement.dataset.pageWidth} × ${tabElement.dataset.pageHeight} px</span></div>`;
    content += `<div class="stat-row"><span class="stat-label">Total Visuals:</span><span class="stat-value">${visualCount}</span></div>`;

    // Sort visual types by count (descending)
    const sortedTypes = Object.entries(visualTypes).sort((a, b) => b[1] - a[1]);

    if (sortedTypes.length > 0) {
        content += '<div style="margin-top:8px; border-top:1px solid var(--border-color); padding-top:6px;">';
        content += '<div style="font-weight:600; margin-bottom:4px; font-size:11px; color:var(--text-secondary);">By Type:</div>';

        // Show top 8 types to avoid overcrowding
        const displayTypes = sortedTypes.slice(0, 8);
        displayTypes.forEach(item => {
            content += `<div class="stat-row"><span class="stat-label">${item[0]}</span><span class="stat-value">${item[1]}</span></div>`;
        });

        if (sortedTypes.length > 8) {
            content += `<div class="stat-row" style="color:var(--text-secondary); font-style:italic;"><span>...and ${sortedTypes.length - 8} more types</span></div>`;
        }
        content += '</div>';
    }

    content += '<div style="margin-top:8px; padding-top:6px; border-top:1px solid var(--border-color); font-size:10px; color:#aaa">Right click to hide</div>';

    pageTooltip.innerHTML = content;
    pageTooltip.style.display = 'block';

    // Position below the tab
    const rect = tabElement.getBoundingClientRect();
    pageTooltip.style.left = `${rect.left}px`;
    pageTooltip.style.top = `${rect.bottom + 8}px`;
}

function hidePageTooltip() {
    pageTooltip.style.display = 'none';
}

/* Fields Pane Functions */
const selectedFields = new Set();
let searchDebounceTimer = null;

function toggleFieldsPane() {
    const pane = document.getElementById('fields-pane');
    const btn = document.getElementById('fields-pane-btn');
    const isCollapsed = pane.classList.toggle('collapsed');
    btn.classList.toggle('pane-collapsed', isCollapsed);

    // Update ARIA state
    btn.setAttribute('aria-expanded', !isCollapsed);
    btn.setAttribute('aria-label', isCollapsed ? 'Expand Fields Pane' : 'Collapse Fields Pane');

    // Save preference
    localStorage.setItem('wireframe-fields-pane', isCollapsed ? 'collapsed' : 'expanded');
}

function initFieldsPane() {
    const container = document.getElementById('fields-list');
    const tables = fieldsIndex.tables || {};

    // Sort tables alphabetically
    const sortedTables = Object.keys(tables).sort();

    let html = '';
    sortedTables.forEach(tableName => {
        const tableData = tables[tableName];

        html += `<div class="table-item" data-table="${escapeHtml(tableName)}">`;
        html += '<div class="table-header">';
        html += `<span class="table-expand-icon" onclick="event.stopPropagation(); toggleTable('${escapeHtml(tableName)}')" aria-hidden="true">▶</span>`;
        html += `<div class="table-header-content" role="button" tabindex="0" aria-expanded="false" onclick="toggleTableSelection('${escapeHtml(tableName)}')" onkeydown="handleTableKey(event, '${escapeHtml(tableName)}')" onmouseenter="showTableTooltip(event, '${escapeHtml(tableName)}')" onmouseleave="hideTableTooltip()">`;
        html += '<svg class="table-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="2"/><line x1="9" y1="9" x2="9" y2="21" stroke="currentColor" stroke-width="2"/></svg>';
        html += `<span class="table-name">${escapeHtml(tableName)}</span>`;
        html += `<span class="table-count">${tableData.visualCount}</span>`;
        html += '</div>';
        html += '</div>';
        html += '<div class="table-fields">';

        // Columns
        tableData.columns.forEach(col => {
            const fieldKey = `${tableName}.${col}`;
            const count = (fieldsIndex.fieldToVisuals[fieldKey] || []).length;
            html += `<div class="field-item" role="checkbox" aria-checked="false" tabindex="0" data-field="${escapeHtml(fieldKey)}" onclick="toggleFieldSelection('${escapeHtml(fieldKey)}')" onkeydown="handleFieldKey(event, '${escapeHtml(fieldKey)}')" onmouseenter="showFieldTooltip(event, '${escapeHtml(tableName)}', '${escapeHtml(col)}')" onmouseleave="hideFieldTooltip()">`;
            html += '<span class="field-icon column-icon" title="Column">⊟</span>';
            html += `<span class="field-name">${escapeHtml(col)}</span>`;
            html += `<span class="field-count">(${count})</span>`;
            html += '</div>';
        });

        // Measures
        tableData.measures.forEach(meas => {
            const fieldKey = `${tableName}.${meas}`;
            const count = (fieldsIndex.fieldToVisuals[fieldKey] || []).length;
            html += `<div class="field-item" role="checkbox" aria-checked="false" tabindex="0" data-field="${escapeHtml(fieldKey)}" onclick="toggleFieldSelection('${escapeHtml(fieldKey)}')" onkeydown="handleFieldKey(event, '${escapeHtml(fieldKey)}')" onmouseenter="showFieldTooltip(event, '${escapeHtml(tableName)}', '${escapeHtml(meas)}')" onmouseleave="hideFieldTooltip()">`;
            html += '<span class="field-icon measure-icon" title="Measure">Σ</span>';
            html += `<span class="field-name">${escapeHtml(meas)}</span>`;
            html += `<span class="field-count">(${count})</span>`;
            html += '</div>';
        });

        html += '</div></div>';
    });

    container.innerHTML = html || '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No fields found</div>';

    // Load saved pane state (default is collapsed)
    const savedState = localStorage.getItem('wireframe-fields-pane');
    const pane = document.getElementById('fields-pane');
    const btn = document.getElementById('fields-pane-btn');
    if (savedState === 'expanded') {
        pane.classList.remove('collapsed');
        btn.classList.remove('pane-collapsed');
    } else {
        // Default is collapsed, ensure button class is set
        btn.classList.add('pane-collapsed');
    }
}

function handleTableKey(event, tableName) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleTableSelection(tableName);
    } else if (event.key === 'ArrowRight') {
        event.preventDefault();
        const tableItem = document.querySelector(`.table-item[data-table="${tableName}"]`);
        if (tableItem && !tableItem.classList.contains('expanded')) {
            tableItem.classList.add('expanded');
        }
    } else if (event.key === 'ArrowLeft') {
        event.preventDefault();
        const tableItem = document.querySelector(`.table-item[data-table="${tableName}"]`);
        if (tableItem && tableItem.classList.contains('expanded')) {
            tableItem.classList.remove('expanded');
        }
    }
}

function handleFieldKey(event, fieldKey) {
    if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        toggleFieldSelection(fieldKey);
    }
}

function escapeHtml(text) {
    escapeDiv.textContent = text;
    return escapeDiv.innerHTML;
}

function toggleTable(tableName) {
    const tableItem = document.querySelector(`.table-item[data-table="${tableName}"]`);
    if (tableItem) {
        tableItem.classList.toggle('expanded');
    }
}

function toggleTableSelection(tableName) {
    const tableData = fieldsIndex.tables[tableName];
    if (!tableData) return;

    // Get all field keys for this table
    const tableFieldKeys = [];
    tableData.columns.forEach(col => {
        tableFieldKeys.push(`${tableName}.${col}`);
    });
    tableData.measures.forEach(meas => {
        tableFieldKeys.push(`${tableName}.${meas}`);
    });

    // Check if all fields in this table are already selected
    const allSelected = tableFieldKeys.every(key => selectedFields.has(key));

    // Prepare undo data
    const changes = [];
    tableFieldKeys.forEach(key => {
        const isSelected = selectedFields.has(key);
        // If allSelected is true, we are DESELECTING. Change if currently selected.
        // If allSelected is false, we are SELECTING. Change if currently NOT selected.
        if (allSelected) {
            if (isSelected) changes.push({ key, wasSelected: true });
        } else {
            if (!isSelected) changes.push({ key, wasSelected: false });
        }
    });

    if (changes.length > 0) {
        trackAction('batchFieldSelection', { changes });
    }

    // Toggle: if all selected, deselect all; otherwise select all
    tableFieldKeys.forEach(fieldKey => {
        const fieldItem = document.querySelector(`.field-item[data-field="${fieldKey}"]`);
        if (allSelected) {
            selectedFields.delete(fieldKey);
            if (fieldItem) {
                fieldItem.classList.remove('selected');
                fieldItem.setAttribute('aria-checked', 'false');
            }
        } else {
            selectedFields.add(fieldKey);
            if (fieldItem) {
                fieldItem.classList.add('selected');
                fieldItem.setAttribute('aria-checked', 'true');
            }
        }

        if (fieldItem && !selectedFields.has(fieldKey)) {
            fieldItem.setAttribute('aria-checked', 'false');
        }
    });

    // Also expand the table to show selected items
    const tableItem = document.querySelector(`.table-item[data-table="${tableName}"]`);
    if (tableItem && !allSelected) {
        tableItem.classList.add('expanded');
    }

    updateFieldsFooter();
    applyFieldFilters();
    updateResetButtonState();
}

function toggleFieldSelection(fieldKey) {
    const fieldItem = document.querySelector(`.field-item[data-field="${fieldKey}"]`);
    const wasSelected = selectedFields.has(fieldKey);

    // Track action for undo (store the state to restore to)
    trackAction('fieldSelection', { fieldKey, wasSelected });

    if (wasSelected) {
        selectedFields.delete(fieldKey);
        if (fieldItem) {
            fieldItem.classList.remove('selected');
            fieldItem.setAttribute('aria-checked', 'false');
        }
    } else {
        selectedFields.add(fieldKey);
        if (fieldItem) {
            fieldItem.classList.add('selected');
            fieldItem.setAttribute('aria-checked', 'true');
        }
    }

    updateFieldsFooter();
    applyFieldFilters();
    updateResetButtonState();
}

function updateFieldsFooter() {
    const count = selectedFields.size;
    document.getElementById('selected-count').textContent = `${count} selected`;
    document.getElementById('clear-fields-btn').disabled = count === 0;
}

function clearFieldFilters() {
    selectedFields.clear();
    document.querySelectorAll('.field-item.selected').forEach(el => {
        el.classList.remove('selected');
    });
    updateFieldsFooter();
    applyFieldFilters();
    updateResetButtonState();
}

function searchFields() {
    // Debounce search
    if (searchDebounceTimer) {
        clearTimeout(searchDebounceTimer);
    }

    searchDebounceTimer = setTimeout(() => {
        const query = document.getElementById('fields-search').value.toLowerCase().trim();
        const tableItems = document.querySelectorAll('.table-item');
        let matchingFieldKeys = new Set();

        tableItems.forEach(tableItem => {
            const tableName = tableItem.dataset.table.toLowerCase();
            const fieldItems = tableItem.querySelectorAll('.field-item');
            let hasMatchingFields = false;
            const tableMatches = tableName.includes(query);

            fieldItems.forEach(fieldItem => {
                const fieldName = fieldItem.querySelector('.field-name').textContent.toLowerCase();
                const matches = tableMatches || fieldName.includes(query) || query === '';

                fieldItem.style.display = matches ? '' : 'none';
                if (matches) {
                    hasMatchingFields = true;
                    matchingFieldKeys.add(fieldItem.dataset.field);
                }
            });

            // Show table if it matches or has matching fields
            tableItem.style.display = (tableMatches || hasMatchingFields) ? '' : 'none';

            // Auto-expand tables with matching fields during search
            if (query && hasMatchingFields) {
                tableItem.classList.add('expanded');
            }
        });

        // Also filter visuals based on search
        if (query) {
            applySearchFieldFilter(matchingFieldKeys);
        } else {
            // Clear field-based filtering when search is cleared
            filterVisuals();
        }
        updateResetButtonState();
    }, SEARCH_DEBOUNCE_MS);
}

function applySearchFieldFilter(matchingFieldKeys) {
    // Filter visuals to only show those using matching fields
    const visuals = getCachedVisuals();
    const pagesWithMatchingVisuals = new Set();
    const searchFilter = document.getElementById('search-input').value.toLowerCase();

    visuals.forEach(visual => {
        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") return;

        // Use helper for field matching
        const matchesFields = checkFieldMatch(visual, null, matchingFieldKeys);
        const matchesText = isMatch(visual, searchFilter);
        const matchesVis = matchesVisibilityFilter(visual);

        const isVisible = matchesFields && matchesText && matchesVis;
        setVisualVisibility(visual, isVisible);

        if (isVisible) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    });

    // Update tab visibility using helper (no name matching for field search)
    updateTabVisibility(pagesWithMatchingVisuals, false, null);
    switchToFirstVisiblePage(pagesWithMatchingVisuals);
}

function applyFieldFilters() {
    if (selectedFields.size === 0) {
        // No field selection - check if there's an active field search
        const fieldSearchQuery = document.getElementById('fields-search').value.trim();
        if (fieldSearchQuery) {
            // Re-trigger field search filtering
            searchFields();
        } else {
            // No field filters at all, reset to show all (respecting other filters)
            filterVisualsBase();
        }
        return;
    }

    // Get visual IDs that match ANY selected field (OR logic)
    const matchingVisualIds = new Set();
    selectedFields.forEach(fieldKey => {
        const visuals = fieldsIndex.fieldToVisuals[fieldKey] || [];
        visuals.forEach(vid => {
            matchingVisualIds.add(vid);
        });
    });

    // Apply filter to visuals
    const visuals = getCachedVisuals();
    const pagesWithMatchingVisuals = new Set();
    const searchFilter = document.getElementById('search-input').value.toLowerCase();

    visuals.forEach(visual => {
        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") return;

        // Use helper for field matching
        const matchesField = checkFieldMatch(visual, matchingVisualIds, null);
        const matchesSearch = isMatch(visual, searchFilter);
        const matchesVis = matchesVisibilityFilter(visual);

        const isVisible = matchesSearch && matchesVis && matchesField;
        setVisualVisibility(visual, isVisible);

        if (isVisible) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    });

    // Update tab visibility using helper
    updateTabVisibility(pagesWithMatchingVisuals, false, null);
    switchToFirstVisiblePage(pagesWithMatchingVisuals);
}

function switchToFirstVisiblePage(pagesWithMatchingVisuals) {
    // Get current active page
    const activePage = document.querySelector('.page-container.active');
    if (!activePage) return;

    const currentPageId = activePage.id;

    // If current page has matching visuals, no need to switch
    if (pagesWithMatchingVisuals.has(currentPageId)) return;

    // Find and switch to first visible page using cached tabs
    const tabs = getCachedTabs();
    for (let i = 0; i < tabs.length; i++) {
        const tab = tabs[i];
        if (tab.style.display !== 'none') {
            const pageId = tab.id.replace("tab-", "");
            openPage(pageId);
            break;
        }
    }
}

function showFieldTooltip(e, tableName, fieldName) {
    const fieldKey = `${tableName}.${fieldName}`;
    const tableData = fieldsIndex.tables[tableName];

    if (!tableData) return;

    let content = `<h5>${escapeHtml(tableName)} → ${escapeHtml(fieldName)}</h5>`;

    // Get non-visual usage (bookmarks and filters)
    const fieldUsage = (fieldsIndex.fieldUsage || {})[fieldKey] || {};
    const bookmarkCount = fieldUsage.bookmark_count || 0;
    const filterCount = fieldUsage.filter_count || 0;

    // Show bookmark and filter usage if present
    if (bookmarkCount > 0 || filterCount > 0) {
        content += '<div class="usage-info" style="margin-bottom: 8px; padding: 6px 8px; background: var(--hover-bg); border-radius: 4px; font-size: 11px;">';
        const usageItems = [];
        if (bookmarkCount > 0) {
            usageItems.push(`<span>📑 ${bookmarkCount} Bookmark${bookmarkCount > 1 ? 's' : ''}</span>`);
        }
        if (filterCount > 0) {
            usageItems.push(`<span>🔍 ${filterCount} Filter${filterCount > 1 ? 's' : ''}</span>`);
        }
        content += usageItems.join(' &nbsp;·&nbsp; ');
        content += '</div>';
    }

    content += '<div class="page-breakdown">';

    // Get page breakdown for this specific field
    const visualIds = fieldsIndex.fieldToVisuals[fieldKey] || [];
    const pageCount = {};

    getCachedVisuals().forEach(visual => {
        if (visualIds.includes(visual.dataset.id)) {
            const pageName = visual.closest('.page-container').dataset.pageName;
            pageCount[pageName] = (pageCount[pageName] || 0) + 1;
        }
    });

    const sortedPages = Object.entries(pageCount).sort((a, b) => b[1] - a[1]);

    if (sortedPages.length > 0) {
        sortedPages.forEach(entry => {
            content += `<div class="page-row"><span>${escapeHtml(entry[0])}</span><span>${entry[1]} visual(s)</span></div>`;
        });
    } else if (bookmarkCount > 0 || filterCount > 0) {
        content += '<div class="page-row" style="color: var(--text-secondary); font-style: italic;"><span>Not used in any visuals</span></div>';
    }

    content += '</div>';

    fieldTooltip.innerHTML = content;
    fieldTooltip.style.display = 'block';
    fieldTooltip.style.left = `${e.clientX + 15}px`;
    fieldTooltip.style.top = `${e.clientY + 10}px`;
}

function hideFieldTooltip() {
    fieldTooltip.style.display = 'none';
}

function showTableTooltip(e, tableName) {
    const tableData = fieldsIndex.tables[tableName];
    if (!tableData) return;

    const totalFields = tableData.columns.length + tableData.measures.length;

    let content = `<h5>${escapeHtml(tableName)}</h5>`;
    content += `<div class="stat-row"><span class="stat-label">Columns:</span><span class="stat-value">${tableData.columns.length}</span></div>`;
    content += `<div class="stat-row"><span class="stat-label">Measures:</span><span class="stat-value">${tableData.measures.length}</span></div>`;
    content += `<div class="stat-row"><span class="stat-label">Total Fields:</span><span class="stat-value">${totalFields}</span></div>`;
    content += `<div class="stat-row"><span class="stat-label">Visuals:</span><span class="stat-value">${tableData.visualCount}</span></div>`;

    // Page breakdown
    const pageBreakdown = tableData.pageBreakdown || {};
    const sortedPages = Object.entries(pageBreakdown).sort((a, b) => b[1] - a[1]);

    if (sortedPages.length > 0) {
        content += '<div style="margin-top: 8px; border-top: 1px solid var(--border-color); padding-top: 6px;">';
        content += '<div style="font-weight: 600; margin-bottom: 4px; font-size: 10px; color: var(--text-secondary);">Visuals by Page:</div>';

        const displayPages = sortedPages.slice(0, 5);
        displayPages.forEach(entry => {
            content += `<div class="stat-row"><span class="stat-label">${escapeHtml(entry[0])}</span><span class="stat-value">${entry[1]}</span></div>`;
        });

        if (sortedPages.length > 5) {
            content += `<div class="stat-row" style="color: var(--text-secondary); font-style: italic;"><span>...and ${sortedPages.length - 5} more</span></div>`;
        }
        content += '</div>';
    }

    tableTooltip.innerHTML = content;
    tableTooltip.style.display = 'block';
    tableTooltip.style.left = `${e.clientX + 15}px`;
    tableTooltip.style.top = `${e.clientY + 10}px`;
}

function hideTableTooltip() {
    tableTooltip.style.display = 'none';
}

// Event Delegation for Visual Boxes (performance optimization)
function setupVisualEventDelegation() {
    const contentArea = document.querySelector('.content-area');
    if (!contentArea) return;

    // Delegated click handler
    contentArea.addEventListener('click', e => {
        const visual = e.target.closest('.visual-box');
        if (visual && visual.dataset.manuallyHidden !== 'true') {
            copyVisualId(visual.dataset.id);
        }
    });

    // Delegated right-click (context menu) handler
    contentArea.addEventListener('contextmenu', e => {
        const visual = e.target.closest('.visual-box');
        if (visual) {
            hideVisual(e, visual.dataset.id);
        }
    });

    // Delegated mousemove for tooltip
    contentArea.addEventListener('mousemove', e => {
        const visual = e.target.closest('.visual-box');
        if (visual) {
            showTooltip(e, visual);
        }
    });

    // Delegated mouseout for tooltip
    contentArea.addEventListener('mouseout', e => {
        const visual = e.target.closest('.visual-box');
        const relatedTarget = e.relatedTarget;
        // Only hide tooltip if leaving visual entirely
        if (visual && (!relatedTarget || !visual.contains(relatedTarget))) {
            hideTooltip();
        }
    });
}

/* Fields Pane Resize Functionality */
let isResizingFieldsPane = false;
let fieldsPaneStartX = 0;
let fieldsPaneStartWidth = 0;

function initFieldsPaneResize(e) {
    const pane = document.getElementById('fields-pane');
    if (!pane || pane.classList.contains('collapsed')) return;

    isResizingFieldsPane = true;
    fieldsPaneStartX = e.clientX;
    fieldsPaneStartWidth = pane.getBoundingClientRect().width;

    // Disable transitions for smooth dragging
    pane.classList.add('resizing');
    const btn = document.getElementById('fields-pane-btn');
    if (btn) btn.classList.add('resizing');
    document.getElementById('fields-pane-resize').classList.add('active');

    document.body.style.cursor = 'ew-resize';
    e.preventDefault();
}

document.addEventListener('mousemove', e => {
    if (!isResizingFieldsPane) return;

    // Dragging left edge: moving left increases width, moving right decreases width
    let newWidth = fieldsPaneStartWidth - (e.clientX - fieldsPaneStartX);

    // Constraints (using defined constants)
    if (newWidth < FIELDS_PANE_MIN_WIDTH) newWidth = FIELDS_PANE_MIN_WIDTH;
    if (newWidth > FIELDS_PANE_MAX_WIDTH) newWidth = FIELDS_PANE_MAX_WIDTH;

    document.documentElement.style.setProperty('--fields-pane-width', `${newWidth}px`);
});

document.addEventListener('mouseup', e => {
    if (!isResizingFieldsPane) return;

    isResizingFieldsPane = false;
    document.body.style.cursor = '';

    // Re-enable transitions
    const pane = document.getElementById('fields-pane');
    if (pane) pane.classList.remove('resizing');
    const btn = document.getElementById('fields-pane-btn');
    if (btn) btn.classList.remove('resizing');
    const handle = document.getElementById('fields-pane-resize');
    if (handle) handle.classList.remove('active');

    // Save width to localStorage
    const width = getComputedStyle(document.documentElement).getPropertyValue('--fields-pane-width').trim();
    localStorage.setItem('wireframe-fields-pane-width', width);
});

// Restore saved fields pane width
(() => {
    const savedWidth = localStorage.getItem('wireframe-fields-pane-width');
    if (savedWidth) {
        document.documentElement.style.setProperty('--fields-pane-width', savedWidth);
    }
})();

/**
 * Returns an array of visual IDs that are currently visible (not filtered out).
 * Used for WYSIWYG CSV export - exports only what the user sees.
 */
function getVisibleVisualIds() {
    const visibleIds = [];
    getCachedVisuals().forEach(visual => {
        // Skip manually hidden visuals
        if (visual.dataset.manuallyHidden === "true") return;

        // Skip filtered out visuals (opacity 0.1 or 0 means hidden by filter)
        if (visual.style.opacity === "0.1" || visual.style.opacity === "0") return;

        // Skip visuals on manually hidden pages
        const pageId = visual.parentElement.id;
        if (hiddenPagesStack.indexOf(pageId) !== -1) return;

        visibleIds.push(visual.dataset.id);
    });
    return visibleIds;
}

/**
 * Checks if any filters are currently active that would limit visible visuals.
 */
function hasActiveFilters() {
    return document.getElementById('search-input').value !== '' ||
        document.getElementById('fields-search').value !== '' ||
        visibilityFilter !== null ||
        selectedFields.size > 0 ||
        hiddenStack.length > 0 ||
        hiddenPagesStack.length > 0;
}

// Initialize based on mode
if (!API_MODE) {
    // Static mode: data is embedded by Jinja, initialize immediately
    initFieldsPane();
    setupVisualEventDelegation();
}
