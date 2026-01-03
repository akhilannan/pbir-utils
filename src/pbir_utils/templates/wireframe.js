var currentZoom = 1;
var minZoom = 0.25;
var maxZoom = 2;
var zoomStep = 0.25;

var initialPageLoaded = false;

function openPage(pageId, skipTracking) {
    // Get current page before switching (for undo tracking)
    var currentActivePage = document.querySelector('.page-container.active');
    var previousPageId = currentActivePage ? currentActivePage.id : null;

    document.querySelectorAll('.page-container.active, .tab-button.active').forEach(function (el) {
        el.classList.remove('active');
    });

    var page = document.getElementById(pageId);
    if (page) page.classList.add("active");

    var tab = document.getElementById('tab-' + pageId);
    if (tab) tab.classList.add("active");

    applyZoom();

    // Track page change for undo (skip on initial load and when undoing/resetting)
    if (initialPageLoaded && !skipTracking && previousPageId && previousPageId !== pageId) {
        trackAction('pageChange', { previousPageId: previousPageId });
    }

    initialPageLoaded = true;
}

/* Zoom Controls */
function zoomIn() {
    if (currentZoom < maxZoom) {
        currentZoom = Math.min(maxZoom, currentZoom + zoomStep);
        applyZoom();
    }
}

function zoomOut() {
    if (currentZoom > minZoom) {
        currentZoom = Math.max(minZoom, currentZoom - zoomStep);
        applyZoom();
    }
}

function resetZoom() {
    currentZoom = 1;
    applyZoom();
}

function applyZoom() {
    var activePage = document.querySelector('.page-container.active');
    if (activePage) {
        activePage.style.transform = 'scale(' + currentZoom + ')';
    }
    document.getElementById('zoom-level').textContent = Math.round(currentZoom * 100) + '%';
}

/* Theme Toggle */
function toggleTheme() {
    var body = document.body;
    var btn = document.getElementById('theme-btn');
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
(function () {
    var savedTheme = localStorage.getItem('wireframe-theme');
    if (savedTheme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        document.getElementById('theme-btn').textContent = '☀️';
    }
})();

/* Interactivity Functions */

var hiddenStack = [];
var hiddenPagesStack = [];

function updateButtons() {
    var hasHiddenItems = hiddenStack.length > 0 || hiddenPagesStack.length > 0;
    document.getElementById('undo-btn').disabled = hiddenStack.length === 0;
    document.getElementById('reset-btn').disabled = !hasHiddenItems;

    // Update hidden pages pill
    var pill = document.getElementById('hidden-pages-pill');
    if (hiddenPagesStack.length > 0) {
        pill.textContent = '+' + hiddenPagesStack.length + ' page' + (hiddenPagesStack.length > 1 ? 's' : '');
        pill.classList.add('visible');
    } else {
        pill.classList.remove('visible');
    }
}

function hidePage(event, pageId) {
    event.preventDefault();
    hidePageTooltip();

    // Count visible tabs
    var tabs = document.querySelectorAll('.tab-button');
    var visibleCount = 0;
    tabs.forEach(function (tab) {
        if (tab.style.display !== 'none') visibleCount++;
    });

    // Don't hide if it's the last visible page
    if (visibleCount <= 1) {
        return;
    }

    var tab = document.getElementById('tab-' + pageId);
    var pageContainer = document.getElementById(pageId);

    // If hiding active page, switch to next visible one first
    if (tab && tab.classList.contains('active')) {
        var nextTab = null;
        var foundCurrent = false;
        tabs.forEach(function (t) {
            if (t === tab) {
                foundCurrent = true;
            } else if (foundCurrent && !nextTab && t.style.display !== 'none') {
                nextTab = t;
            }
        });
        // If no next tab, find previous
        if (!nextTab) {
            tabs.forEach(function (t) {
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
    hiddenPagesStack.forEach(function (pageId) {
        var tab = document.getElementById('tab-' + pageId);
        if (tab) {
            tab.style.display = '';
        }
    });
    hiddenPagesStack = [];
    updateButtons();
}

function copyVisualId(visualId) {
    navigator.clipboard.writeText(visualId).then(function () {
        showToast();
    }, function (err) {
        console.error('Async: Could not copy text: ', err);
    });
}

function showToast() {
    var toast = document.getElementById("toast");
    toast.className = "toast show";
    setTimeout(function () { toast.className = toast.className.replace("show", ""); }, 2000);
}

function hideVisual(event, visualId) {
    event.preventDefault();
    var el = document.getElementById("visual-" + visualId);
    if (el) {
        el.style.opacity = "0";
        el.style.pointerEvents = "none";
        el.dataset.manuallyHidden = "true";

        hiddenStack.push(visualId);
        updateButtons();
    }
    hideTooltip();
}

function undoHideVisual() {
    if (hiddenStack.length === 0) return;

    var visualId = hiddenStack.pop();
    var el = document.getElementById("visual-" + visualId);
    if (el) {
        checkVisualFilterState(el);
        el.style.pointerEvents = "auto";
        el.dataset.manuallyHidden = "false";
    }
    updateButtons();
}

function resetHiddenVisuals() {
    var hiddenElements = document.querySelectorAll('[data-manually-hidden="true"]');
    hiddenElements.forEach(function (el) {
        checkVisualFilterState(el);
        el.style.pointerEvents = "auto";
        el.dataset.manuallyHidden = "false";
    });
    hiddenStack = [];

    // Also reset hidden pages
    resetHiddenPages();

    updateButtons();
}

// Action tracking for undo
var actionStack = [];

function trackAction(actionType, data) {
    actionStack.push({ type: actionType, data: data });
    updateResetButtonState();
}

function undoLastAction() {
    if (actionStack.length === 0) {
        // Fallback to old behavior for hidden visuals
        undoHideVisual();
        return;
    }

    var lastAction = actionStack.pop();

    switch (lastAction.type) {
        case 'hideVisual':
            undoHideVisual();
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
            document.querySelectorAll('.filter-toggle').forEach(function (btn) {
                btn.classList.remove('active');
            });
            if (visibilityFilter) {
                document.getElementById('filter-' + visibilityFilter).classList.add('active');
            }
            filterVisuals();
            break;
        case 'fieldSelection':
            if (lastAction.data.wasSelected) {
                selectedFields.add(lastAction.data.fieldKey);
            } else {
                selectedFields.delete(lastAction.data.fieldKey);
            }
            var fieldItem = document.querySelector('.field-item[data-field="' + lastAction.data.fieldKey + '"]');
            if (fieldItem) {
                fieldItem.classList.toggle('selected', lastAction.data.wasSelected);
            }
            updateFieldsFooter();
            applyFieldFilters();
            break;
        case 'batchFieldSelection':
            lastAction.data.changes.forEach(function (change) {
                if (change.wasSelected) {
                    selectedFields.add(change.key);
                } else {
                    selectedFields.delete(change.key);
                }
                var fieldItem = document.querySelector('.field-item[data-field="' + change.key + '"]');
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
    document.querySelectorAll('.filter-toggle').forEach(function (btn) {
        btn.classList.remove('active');
    });

    // 4. Clear field selections
    selectedFields.clear();
    document.querySelectorAll('.field-item.selected').forEach(function (el) {
        el.classList.remove('selected');
    });
    updateFieldsFooter();

    // 5. Reset hidden visuals
    resetHiddenVisuals();

    // 6. Reset field list display
    document.querySelectorAll('.table-item').forEach(function (tableItem) {
        tableItem.style.display = '';
        tableItem.classList.remove('expanded');
        tableItem.querySelectorAll('.field-item').forEach(function (fieldItem) {
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
    var currentPage = document.querySelector('.page-container.active');
    var currentPageId = currentPage ? currentPage.id : null;
    var pageChanged = typeof activePageId !== 'undefined' && activePageId && currentPageId !== activePageId;

    var hasFilters =
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
    var ds = visual.dataset;
    var pageName = visual.parentElement.dataset.pageName || "";
    return ds.id.toLowerCase().includes(filter) ||
        ds.type.toLowerCase().includes(filter) ||
        pageName.includes(filter);
}

function checkVisualFilterState(visual) {
    var filter = document.getElementById('search-input').value.toLowerCase();
    setVisualVisibility(visual, isMatch(visual, filter));
}

var visibilityFilter = null; // null = all, 'hidden' = only hidden, 'visible' = only visible

function toggleVisibilityFilter(mode) {
    var hiddenBtn = document.getElementById('filter-hidden');
    var visibleBtn = document.getElementById('filter-visible');

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
    var isHidden = visual.classList.contains('hidden');
    if (visibilityFilter === 'hidden') return isHidden;
    if (visibilityFilter === 'visible') return !isHidden;
    return true;
}

function filterVisuals() {
    var filter = document.getElementById('search-input').value.toLowerCase();
    var visuals = document.getElementsByClassName('visual-box');
    var pagesWithMatchingVisuals = new Set();

    // 1. Filter Visuals & Track Matching Pages
    for (var i = 0; i < visuals.length; i++) {
        var visual = visuals[i];

        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") continue;

        var matchesSearch = isMatch(visual, filter);
        var matchesVis = matchesVisibilityFilter(visual);
        var match = matchesSearch && matchesVis;

        setVisualVisibility(visual, match);

        if (match) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    }

    // 2. Filter Tabs
    var tabs = document.getElementsByClassName('tab-button');
    var noFiltersActive = !filter && visibilityFilter === null;

    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        var pageName = tab.dataset.pageName.toLowerCase();
        var pageId = tab.id.replace("tab-", "");

        // Only check page name match if there's actual search text
        var matchesName = filter && pageName.includes(filter);

        if (noFiltersActive || matchesName || pagesWithMatchingVisuals.has(pageId)) {
            tab.style.display = "";
        } else {
            tab.style.display = "none";
        }
    }

    // 3. Auto-switch to first visible page if current page has no matching visuals
    if (!noFiltersActive) {
        switchToFirstVisiblePage(pagesWithMatchingVisuals);
    }

    // Update reset button state
    updateResetButtonState();
}

var tooltip = document.getElementById('tooltip');


function showTooltip(e, visualElement) {
    var type = visualElement.dataset.type;
    var id = visualElement.dataset.id;
    var width = Math.round(parseFloat(visualElement.dataset.width));
    var height = Math.round(parseFloat(visualElement.dataset.height));
    var x = Math.round(parseFloat(visualElement.dataset.x));
    var y = Math.round(parseFloat(visualElement.dataset.y));
    var parent = visualElement.dataset.parentGroup || '';
    var isHidden = visualElement.classList.contains('hidden');

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
    tooltip.style.left = (e.clientX + xOffset) + 'px';
    tooltip.style.top = (e.clientY + yOffset) + 'px';
}

function hideTooltip() {
    tooltip.style.display = 'none';
}

/* Page Tooltip Functions */
var pageTooltip = document.getElementById('page-tooltip');

function showPageTooltip(e, tabElement) {
    var pageName = tabElement.dataset.pageName;
    var visualCount = tabElement.dataset.visualCount;
    var isHidden = tabElement.dataset.isHidden === 'True';
    var visualTypes = {};

    try {
        visualTypes = JSON.parse(tabElement.dataset.visualTypes || '{}');
    } catch (err) {
        visualTypes = {};
    }

    var content = '<h4>' + pageName + (isHidden ? ' <span style="color:var(--hidden-visual-border)">(Hidden)</span>' : '') + '</h4>';
    content += '<div class="stat-row"><span class="stat-label">Page Size:</span><span class="stat-value">' + tabElement.dataset.pageWidth + ' × ' + tabElement.dataset.pageHeight + ' px</span></div>';
    content += '<div class="stat-row"><span class="stat-label">Total Visuals:</span><span class="stat-value">' + visualCount + '</span></div>';

    // Sort visual types by count (descending)
    var sortedTypes = Object.entries(visualTypes).sort((a, b) => b[1] - a[1]);

    if (sortedTypes.length > 0) {
        content += '<div style="margin-top:8px; border-top:1px solid var(--border-color); padding-top:6px;">';
        content += '<div style="font-weight:600; margin-bottom:4px; font-size:11px; color:var(--text-secondary);">By Type:</div>';

        // Show top 8 types to avoid overcrowding
        var displayTypes = sortedTypes.slice(0, 8);
        displayTypes.forEach(function (item) {
            content += '<div class="stat-row"><span class="stat-label">' + item[0] + '</span><span class="stat-value">' + item[1] + '</span></div>';
        });

        if (sortedTypes.length > 8) {
            content += '<div class="stat-row" style="color:var(--text-secondary); font-style:italic;"><span>...and ' + (sortedTypes.length - 8) + ' more types</span></div>';
        }
        content += '</div>';
    }

    content += '<div style="margin-top:8px; padding-top:6px; border-top:1px solid var(--border-color); font-size:10px; color:#aaa">Right click to hide</div>';

    pageTooltip.innerHTML = content;
    pageTooltip.style.display = 'block';

    // Position below the tab
    var rect = tabElement.getBoundingClientRect();
    pageTooltip.style.left = rect.left + 'px';
    pageTooltip.style.top = (rect.bottom + 8) + 'px';
}

function hidePageTooltip() {
    pageTooltip.style.display = 'none';
}

/* Fields Pane Functions */
/* var fieldsIndex is defined in wireframe.html.j2 */
var selectedFields = new Set();
var searchDebounceTimer = null;
var fieldTooltip = document.getElementById('field-tooltip');

function toggleFieldsPane() {
    var pane = document.getElementById('fields-pane');
    var btn = document.getElementById('fields-pane-btn');
    var isCollapsed = pane.classList.toggle('collapsed');
    btn.classList.toggle('pane-collapsed', isCollapsed);

    // Save preference
    localStorage.setItem('wireframe-fields-pane', isCollapsed ? 'collapsed' : 'expanded');
}

function initFieldsPane() {
    var container = document.getElementById('fields-list');
    var tables = fieldsIndex.tables || {};

    // Sort tables alphabetically
    var sortedTables = Object.keys(tables).sort();

    var html = '';
    sortedTables.forEach(function (tableName) {
        var tableData = tables[tableName];
        var totalFields = tableData.columns.length + tableData.measures.length;

        html += '<div class="table-item" data-table="' + escapeHtml(tableName) + '">';
        html += '<div class="table-header">';
        html += '<span class="table-expand-icon" onclick="event.stopPropagation(); toggleTable(\'' + escapeHtml(tableName) + '\')">▶</span>';
        html += '<div class="table-header-content" onclick="toggleTableSelection(\'' + escapeHtml(tableName) + '\')" onmouseenter="showTableTooltip(event, \'' + escapeHtml(tableName) + '\')" onmouseleave="hideTableTooltip()">';
        html += '<svg class="table-icon" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="3" y="3" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="2"/><line x1="9" y1="9" x2="9" y2="21" stroke="currentColor" stroke-width="2"/></svg>';
        html += '<span class="table-name">' + escapeHtml(tableName) + '</span>';
        html += '<span class="table-count">' + tableData.visualCount + '</span>';
        html += '</div>';
        html += '</div>';
        html += '<div class="table-fields">';

        // Columns
        tableData.columns.forEach(function (col) {
            var fieldKey = tableName + '.' + col;
            var count = (fieldsIndex.fieldToVisuals[fieldKey] || []).length;
            html += '<div class="field-item" data-field="' + escapeHtml(fieldKey) + '" onclick="toggleFieldSelection(\'' + escapeHtml(fieldKey) + '\')" onmouseenter="showFieldTooltip(event, \'' + escapeHtml(tableName) + '\', \'' + escapeHtml(col) + '\')" onmouseleave="hideFieldTooltip()">';
            html += '<span class="field-icon column-icon" title="Column">⊟</span>';
            html += '<span class="field-name">' + escapeHtml(col) + '</span>';
            html += '<span class="field-count">(' + count + ')</span>';
            html += '</div>';
        });

        // Measures
        tableData.measures.forEach(function (meas) {
            var fieldKey = tableName + '.' + meas;
            var count = (fieldsIndex.fieldToVisuals[fieldKey] || []).length;
            html += '<div class="field-item" data-field="' + escapeHtml(fieldKey) + '" onclick="toggleFieldSelection(\'' + escapeHtml(fieldKey) + '\')" onmouseenter="showFieldTooltip(event, \'' + escapeHtml(tableName) + '\', \'' + escapeHtml(meas) + '\')" onmouseleave="hideFieldTooltip()">';
            html += '<span class="field-icon measure-icon" title="Measure">Σ</span>';
            html += '<span class="field-name">' + escapeHtml(meas) + '</span>';
            html += '<span class="field-count">(' + count + ')</span>';
            html += '</div>';
        });

        html += '</div></div>';
    });

    container.innerHTML = html || '<div style="padding: 20px; text-align: center; color: var(--text-secondary);">No fields found</div>';

    // Load saved pane state (default is collapsed)
    var savedState = localStorage.getItem('wireframe-fields-pane');
    var pane = document.getElementById('fields-pane');
    var btn = document.getElementById('fields-pane-btn');
    if (savedState === 'expanded') {
        pane.classList.remove('collapsed');
        btn.classList.remove('pane-collapsed');
    } else {
        // Default is collapsed, ensure button class is set
        btn.classList.add('pane-collapsed');
    }
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleTable(tableName) {
    var tableItem = document.querySelector('.table-item[data-table="' + tableName + '"]');
    if (tableItem) {
        tableItem.classList.toggle('expanded');
    }
}

function toggleTableSelection(tableName) {
    var tableData = fieldsIndex.tables[tableName];
    if (!tableData) return;

    // Get all field keys for this table
    var tableFieldKeys = [];
    tableData.columns.forEach(function (col) {
        tableFieldKeys.push(tableName + '.' + col);
    });
    tableData.measures.forEach(function (meas) {
        tableFieldKeys.push(tableName + '.' + meas);
    });

    // Check if all fields in this table are already selected
    var allSelected = tableFieldKeys.every(function (key) {
        return selectedFields.has(key);
    });

    // Prepare undo data
    var changes = [];
    tableFieldKeys.forEach(function (key) {
        var isSelected = selectedFields.has(key);
        // If allSelected is true, we are DESELECTING. Change if currently selected.
        // If allSelected is false, we are SELECTING. Change if currently NOT selected.
        if (allSelected) {
            if (isSelected) changes.push({ key: key, wasSelected: true });
        } else {
            if (!isSelected) changes.push({ key: key, wasSelected: false });
        }
    });

    if (changes.length > 0) {
        trackAction('batchFieldSelection', { changes: changes });
    }

    // Toggle: if all selected, deselect all; otherwise select all
    tableFieldKeys.forEach(function (fieldKey) {
        var fieldItem = document.querySelector('.field-item[data-field="' + fieldKey + '"]');
        if (allSelected) {
            selectedFields.delete(fieldKey);
            if (fieldItem) fieldItem.classList.remove('selected');
        } else {
            selectedFields.add(fieldKey);
            if (fieldItem) fieldItem.classList.add('selected');
        }
    });

    // Also expand the table to show selected items
    var tableItem = document.querySelector('.table-item[data-table="' + tableName + '"]');
    if (tableItem && !allSelected) {
        tableItem.classList.add('expanded');
    }

    updateFieldsFooter();
    applyFieldFilters();
    updateResetButtonState();
}

function toggleFieldSelection(fieldKey) {
    var fieldItem = document.querySelector('.field-item[data-field="' + fieldKey + '"]');
    var wasSelected = selectedFields.has(fieldKey);

    // Track action for undo (store the state to restore to)
    trackAction('fieldSelection', { fieldKey: fieldKey, wasSelected: wasSelected });

    if (wasSelected) {
        selectedFields.delete(fieldKey);
        if (fieldItem) fieldItem.classList.remove('selected');
    } else {
        selectedFields.add(fieldKey);
        if (fieldItem) fieldItem.classList.add('selected');
    }

    updateFieldsFooter();
    applyFieldFilters();
    updateResetButtonState();
}

function updateFieldsFooter() {
    var count = selectedFields.size;
    document.getElementById('selected-count').textContent = count + ' selected';
    document.getElementById('clear-fields-btn').disabled = count === 0;
}

function clearFieldFilters() {
    selectedFields.clear();
    document.querySelectorAll('.field-item.selected').forEach(function (el) {
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

    searchDebounceTimer = setTimeout(function () {
        var query = document.getElementById('fields-search').value.toLowerCase().trim();
        var tableItems = document.querySelectorAll('.table-item');
        var matchingFieldKeys = new Set();

        tableItems.forEach(function (tableItem) {
            var tableName = tableItem.dataset.table.toLowerCase();
            var fieldItems = tableItem.querySelectorAll('.field-item');
            var hasMatchingFields = false;
            var tableMatches = tableName.includes(query);

            fieldItems.forEach(function (fieldItem) {
                var fieldName = fieldItem.querySelector('.field-name').textContent.toLowerCase();
                var matches = tableMatches || fieldName.includes(query) || query === '';

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
    }, 150);
}

function applySearchFieldFilter(matchingFieldKeys) {
    // Filter visuals to only show those using matching fields
    var allVisuals = document.getElementsByClassName('visual-box');
    var pagesWithMatchingVisuals = new Set();

    for (var i = 0; i < allVisuals.length; i++) {
        var visual = allVisuals[i];

        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") continue;

        // Get fields for this visual
        var visualFields = [];
        try {
            visualFields = JSON.parse(visual.dataset.fields || '[]');
        } catch (e) { }

        // Check if any visual field matches the search
        var matchesSearch = visualFields.some(function (f) {
            return matchingFieldKeys.has(f);
        });

        // Also respect other filters
        var matchesText = isMatch(visual, document.getElementById('search-input').value.toLowerCase());
        var matchesVis = matchesVisibilityFilter(visual);

        var isVisible = matchesSearch && matchesText && matchesVis;
        setVisualVisibility(visual, isVisible);

        if (isVisible) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    }

    // Update tab visibility
    var tabs = document.getElementsByClassName('tab-button');
    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        var pageId = tab.id.replace("tab-", "");
        tab.style.display = pagesWithMatchingVisuals.has(pageId) ? "" : "none";
    }

    // Switch to first visible page if current page has no visible visuals
    switchToFirstVisiblePage(pagesWithMatchingVisuals);
}

function applyFieldFilters() {
    if (selectedFields.size === 0) {
        // No field filters, reset to show all (respecting other filters)
        filterVisuals();
        return;
    }

    // Get visual IDs that match ANY selected field (OR logic)
    var matchingVisualIds = new Set();
    selectedFields.forEach(function (fieldKey) {
        var visuals = fieldsIndex.fieldToVisuals[fieldKey] || [];
        visuals.forEach(function (vid) {
            matchingVisualIds.add(vid);
        });
    });

    // Apply filter to visuals
    var allVisuals = document.getElementsByClassName('visual-box');
    var pagesWithMatchingVisuals = new Set();

    for (var i = 0; i < allVisuals.length; i++) {
        var visual = allVisuals[i];
        var visualId = visual.dataset.id;

        // Skip if manually hidden
        if (visual.dataset.manuallyHidden === "true") continue;

        // Check all filter conditions
        var matchesSearch = isMatch(visual, document.getElementById('search-input').value.toLowerCase());
        var matchesVis = matchesVisibilityFilter(visual);
        var matchesField = matchingVisualIds.has(visualId);

        var isVisible = matchesSearch && matchesVis && matchesField;
        setVisualVisibility(visual, isVisible);

        if (isVisible) {
            pagesWithMatchingVisuals.add(visual.parentElement.id);
        }
    }

    // Update tab visibility
    var tabs = document.getElementsByClassName('tab-button');
    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        var pageId = tab.id.replace("tab-", "");
        tab.style.display = pagesWithMatchingVisuals.has(pageId) ? "" : "none";
    }

    // Switch to first visible page if current page has no visible visuals
    switchToFirstVisiblePage(pagesWithMatchingVisuals);
}

function switchToFirstVisiblePage(pagesWithMatchingVisuals) {
    // Get current active page
    var activePage = document.querySelector('.page-container.active');
    if (!activePage) return;

    var currentPageId = activePage.id;

    // If current page has matching visuals, no need to switch
    if (pagesWithMatchingVisuals.has(currentPageId)) return;

    // Find and switch to first visible page
    var tabs = document.getElementsByClassName('tab-button');
    for (var i = 0; i < tabs.length; i++) {
        var tab = tabs[i];
        if (tab.style.display !== 'none') {
            var pageId = tab.id.replace("tab-", "");
            openPage(pageId);
            break;
        }
    }
}

function showFieldTooltip(e, tableName, fieldName) {
    var fieldKey = tableName + '.' + fieldName;
    var tableData = fieldsIndex.tables[tableName];

    if (!tableData) return;

    var content = '<h5>' + escapeHtml(tableName) + ' → ' + escapeHtml(fieldName) + '</h5>';

    // Get non-visual usage (bookmarks and filters)
    var fieldUsage = (fieldsIndex.fieldUsage || {})[fieldKey] || {};
    var bookmarkCount = fieldUsage.bookmark_count || 0;
    var filterCount = fieldUsage.filter_count || 0;

    // Show bookmark and filter usage if present
    if (bookmarkCount > 0 || filterCount > 0) {
        content += '<div class="usage-info" style="margin-bottom: 8px; padding: 6px 8px; background: var(--hover-bg); border-radius: 4px; font-size: 11px;">';
        var usageItems = [];
        if (bookmarkCount > 0) {
            usageItems.push('<span>📑 ' + bookmarkCount + ' Bookmark' + (bookmarkCount > 1 ? 's' : '') + '</span>');
        }
        if (filterCount > 0) {
            usageItems.push('<span>🔍 ' + filterCount + ' Filter' + (filterCount > 1 ? 's' : '') + '</span>');
        }
        content += usageItems.join(' &nbsp;·&nbsp; ');
        content += '</div>';
    }

    content += '<div class="page-breakdown">';

    // Get page breakdown for this specific field
    var visualIds = fieldsIndex.fieldToVisuals[fieldKey] || [];
    var pageCount = {};

    document.querySelectorAll('.visual-box').forEach(function (visual) {
        if (visualIds.includes(visual.dataset.id)) {
            var pageName = visual.closest('.page-container').dataset.pageName;
            pageCount[pageName] = (pageCount[pageName] || 0) + 1;
        }
    });

    var sortedPages = Object.entries(pageCount).sort((a, b) => b[1] - a[1]);

    if (sortedPages.length > 0) {
        sortedPages.forEach(function (entry) {
            content += '<div class="page-row"><span>' + escapeHtml(entry[0]) + '</span><span>' + entry[1] + ' visual(s)</span></div>';
        });
    } else if (bookmarkCount > 0 || filterCount > 0) {
        content += '<div class="page-row" style="color: var(--text-secondary); font-style: italic;"><span>Not used in any visuals</span></div>';
    }

    content += '</div>';

    fieldTooltip.innerHTML = content;
    fieldTooltip.style.display = 'block';
    fieldTooltip.style.left = (e.clientX + 15) + 'px';
    fieldTooltip.style.top = (e.clientY + 10) + 'px';
}

function hideFieldTooltip() {
    fieldTooltip.style.display = 'none';
}

/* Table Tooltip Functions */
var tableTooltip = document.getElementById('table-tooltip');

function showTableTooltip(e, tableName) {
    var tableData = fieldsIndex.tables[tableName];
    if (!tableData) return;

    var totalFields = tableData.columns.length + tableData.measures.length;

    var content = '<h5>' + escapeHtml(tableName) + '</h5>';
    content += '<div class="stat-row"><span class="stat-label">Columns:</span><span class="stat-value">' + tableData.columns.length + '</span></div>';
    content += '<div class="stat-row"><span class="stat-label">Measures:</span><span class="stat-value">' + tableData.measures.length + '</span></div>';
    content += '<div class="stat-row"><span class="stat-label">Total Fields:</span><span class="stat-value">' + totalFields + '</span></div>';
    content += '<div class="stat-row"><span class="stat-label">Visuals Using:</span><span class="stat-value">' + tableData.visualCount + '</span></div>';

    // Page breakdown
    var pageBreakdown = tableData.pageBreakdown || {};
    var sortedPages = Object.entries(pageBreakdown).sort((a, b) => b[1] - a[1]);

    if (sortedPages.length > 0) {
        content += '<div style="margin-top: 8px; border-top: 1px solid var(--border-color); padding-top: 6px;">';
        content += '<div style="font-weight: 600; margin-bottom: 4px; font-size: 10px; color: var(--text-secondary);">By Page:</div>';

        var displayPages = sortedPages.slice(0, 5);
        displayPages.forEach(function (entry) {
            content += '<div class="stat-row"><span class="stat-label">' + escapeHtml(entry[0]) + '</span><span class="stat-value">' + entry[1] + '</span></div>';
        });

        if (sortedPages.length > 5) {
            content += '<div class="stat-row" style="color: var(--text-secondary); font-style: italic;"><span>...and ' + (sortedPages.length - 5) + ' more</span></div>';
        }
        content += '</div>';
    }

    tableTooltip.innerHTML = content;
    tableTooltip.style.display = 'block';
    tableTooltip.style.left = (e.clientX + 15) + 'px';
    tableTooltip.style.top = (e.clientY + 10) + 'px';
}

function hideTableTooltip() {
    tableTooltip.style.display = 'none';
}

// Override filterVisuals to include field filtering
var originalFilterVisuals = filterVisuals;
filterVisuals = function () {
    if (selectedFields.size > 0) {
        applyFieldFilters();
    } else {
        originalFilterVisuals();
    }
};

// Initialize Fields Pane on load
initFieldsPane();
