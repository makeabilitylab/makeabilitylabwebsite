/**
 * OrderedSelectBox - Manage select box contents with ordering support.
 *
 * Provides caching and manipulation of select box options, including
 * filtering, moving between boxes, and reordering.
 *
 * Used by OrderedSelectFilter for the sorted many-to-many widget.
 *
 * @version 2.1.0 - jQuery-free version for Django 5.x
 * @requires None (vanilla JavaScript)
 */

var OrderedSelectBox = {
  /**
   * Cache of select box contents.
   * Keys are select element IDs, values are arrays of option objects.
   * @type {Object.<string, Array<{value: string, text: string, displayed: boolean, order: number}>>}
   */
  cache: {},

  /**
   * Initialize the cache for a select box.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  init: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    OrderedSelectBox.cache[id] = [];

    // Cache all existing options
    for (var i = 0; i < box.options.length; i++) {
      OrderedSelectBox.add_to_cache(id, box.options[i]);
    }
  },

  /**
   * Redisplay the select box from cached data.
   * Only shows items marked as 'displayed'.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  redisplay: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    // Clear existing options
    box.options.length = 0;

    // Rebuild from cache
    var cache = OrderedSelectBox.cache[id] || [];
    for (var i = 0; i < cache.length; i++) {
      var node = cache[i];
      if (node.displayed) {
        box.options[box.options.length] = new Option(node.text, node.value, false, false);
      }
    }
  },

  /**
   * Filter the select box by text.
   * Uses AND matching - all words must appear in the option text.
   *
   * @param {string} id - The select element ID
   * @param {string} text - Filter text (space-separated words)
   * @returns {void}
   *
   * @example
   * // Filter to show only options containing both "john" and "doe"
   * OrderedSelectBox.filter('my_select', 'john doe');
   */
  filter: function(id, text) {
    var tokens = text.toLowerCase().split(/\s+/);
    var cache = OrderedSelectBox.cache[id] || [];

    for (var i = 0; i < cache.length; i++) {
      var node = cache[i];
      node.displayed = true;

      // Check if all tokens are present
      var nodeText = node.text.toLowerCase();
      for (var j = 0; j < tokens.length; j++) {
        if (tokens[j] && nodeText.indexOf(tokens[j]) === -1) {
          node.displayed = false;
          break;
        }
      }
    }

    OrderedSelectBox.redisplay(id);
  },

  /**
   * Add an option to the cache.
   * Options are sorted by their data-sort-value attribute.
   *
   * @param {string} id - The select element ID
   * @param {HTMLOptionElement} option - The option element to add
   * @returns {void}
   */
  add_to_cache: function(id, option) {
    if (!OrderedSelectBox.cache[id]) {
      OrderedSelectBox.cache[id] = [];
    }

    // Get sort order from data attribute, defaulting to 0
    var order = 0;
    var sortValue = option.getAttribute('data-sort-value');
    if (sortValue !== null && sortValue !== '') {
      var parsed = parseInt(sortValue, 10);
      // Only use parsed value if it's a valid number
      if (!isNaN(parsed)) {
        order = parsed;
      }
    }

    OrderedSelectBox.cache[id].push({
      value: option.value,
      text: option.text,
      displayed: true,
      order: order
    });

    // Re-sort by order value
    OrderedSelectBox.cache[id].sort(function(a, b) {
      return a.order - b.order;
    });
  },

  /**
   * Remove an option from the cache by value.
   *
   * @param {string} id - The select element ID
   * @param {string} value - The option value to remove
   * @returns {void}
   */
  delete_from_cache: function(id, value) {
    var cache = OrderedSelectBox.cache[id] || [];

    for (var i = 0; i < cache.length; i++) {
      if (cache[i].value === value) {
        cache.splice(i, 1);
        return;
      }
    }
  },

  /**
   * Check if a value exists in the cache.
   *
   * @param {string} id - The select element ID
   * @param {string} value - The value to check
   * @returns {boolean} True if the value exists in cache
   */
  cache_contains: function(id, value) {
    var cache = OrderedSelectBox.cache[id] || [];

    for (var i = 0; i < cache.length; i++) {
      if (cache[i].value === value) {
        return true;
      }
    }
    return false;
  },

  /**
   * Reset order values in the cache to zero.
   * Used before moving items to ensure proper append behavior.
   *
   * @param {string} id - The select element ID
   * @private
   */
  _reset_order_values: function(id) {
    var cache = OrderedSelectBox.cache[id] || [];
    for (var i = 0; i < cache.length; i++) {
      cache[i].order = 0;
    }
  },

  /**
   * Move selected options from one select to another.
   *
   * @param {string} from - Source select element ID
   * @param {string} to - Destination select element ID
   * @returns {void}
   */
  move: function(from, to) {
    var from_box = document.getElementById(from);
    var to_box = document.getElementById(to);

    if (!from_box || !to_box) {
      return;
    }

    // Reset order values in destination (items are appended in order)
    OrderedSelectBox._reset_order_values(to);

    // Move selected items
    for (var i = 0; i < from_box.options.length; i++) {
      var option = from_box.options[i];
      if (option.selected && OrderedSelectBox.cache_contains(from, option.value)) {
        OrderedSelectBox.add_to_cache(to, option);
        OrderedSelectBox.delete_from_cache(from, option.value);
      }
    }

    OrderedSelectBox.redisplay(from);
    OrderedSelectBox.redisplay(to);
  },

  /**
   * Move all visible options from one select to another.
   *
   * @param {string} from - Source select element ID
   * @param {string} to - Destination select element ID
   * @returns {void}
   */
  move_all: function(from, to) {
    var from_box = document.getElementById(from);

    if (!from_box) {
      return;
    }

    // Reset order values in destination for consistent behavior with move()
    OrderedSelectBox._reset_order_values(to);

    // Move all visible items
    for (var i = 0; i < from_box.options.length; i++) {
      var option = from_box.options[i];
      if (OrderedSelectBox.cache_contains(from, option.value)) {
        OrderedSelectBox.add_to_cache(to, option);
        OrderedSelectBox.delete_from_cache(from, option.value);
      }
    }

    OrderedSelectBox.redisplay(from);
    OrderedSelectBox.redisplay(to);
  },

  /**
   * Sort the cache alphabetically by text and redisplay.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  sort: function(id) {
    var cache = OrderedSelectBox.cache[id] || [];

    cache.sort(function(a, b) {
      var aText = a.text.toLowerCase();
      var bText = b.text.toLowerCase();
      if (aText > bText) return 1;
      if (aText < bText) return -1;
      return 0;
    });

    // Redisplay to reflect the new order
    OrderedSelectBox.redisplay(id);
  },

  /**
   * Move selected options up in the list.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  orderUp: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    // Get selected indices
    var selected = [];
    for (var i = 0; i < box.options.length; i++) {
      if (box.options[i].selected) {
        selected.push(i);
      }
    }

    // Move each selected item up (if possible)
    for (var i = 0; i < selected.length; i++) {
      var idx = selected[i];
      if (idx > 0 && selected.indexOf(idx - 1) === -1) {
        // Swap with previous option
        var option = box.options[idx];
        var prevOption = box.options[idx - 1];

        // Swap in DOM
        var tempText = option.text;
        var tempValue = option.value;
        option.text = prevOption.text;
        option.value = prevOption.value;
        prevOption.text = tempText;
        prevOption.value = tempValue;

        // Update selection
        option.selected = false;
        prevOption.selected = true;

        // Update selected indices
        selected[i] = idx - 1;
      }
    }

    // Update cache to match DOM order
    OrderedSelectBox.sync_cache_from_dom(id);
  },

  /**
   * Move selected options down in the list.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  orderDown: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    // Get selected indices (in reverse order for proper processing)
    var selected = [];
    for (var i = box.options.length - 1; i >= 0; i--) {
      if (box.options[i].selected) {
        selected.push(i);
      }
    }

    // Move each selected item down (if possible)
    for (var i = 0; i < selected.length; i++) {
      var idx = selected[i];
      if (idx < box.options.length - 1 && selected.indexOf(idx + 1) === -1) {
        // Swap with next option
        var option = box.options[idx];
        var nextOption = box.options[idx + 1];

        // Swap in DOM
        var tempText = option.text;
        var tempValue = option.value;
        option.text = nextOption.text;
        option.value = nextOption.value;
        nextOption.text = tempText;
        nextOption.value = tempValue;

        // Update selection
        option.selected = false;
        nextOption.selected = true;

        // Update selected indices
        selected[i] = idx + 1;
      }
    }

    // Update cache to match DOM order
    OrderedSelectBox.sync_cache_from_dom(id);
  },

  /**
   * Synchronize cache from current DOM state.
   * Used after reordering to ensure cache matches visible order.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  sync_cache_from_dom: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    OrderedSelectBox.cache[id] = [];
    for (var i = 0; i < box.options.length; i++) {
      OrderedSelectBox.cache[id].push({
        value: box.options[i].value,
        text: box.options[i].text,
        displayed: true,
        order: i
      });
    }
  },

  /**
   * Select all options in a select box.
   * Called before form submission to ensure all chosen items are submitted.
   *
   * @param {string} id - The select element ID
   * @returns {void}
   */
  select_all: function(id) {
    var box = document.getElementById(id);
    if (!box) {
      return;
    }

    for (var i = 0; i < box.options.length; i++) {
      box.options[i].selected = true;
    }
  }
};

/**
 * Override Django's dismissAddRelatedObjectPopup to work with OrderedSelectBox.
 *
 * When adding a related object via the popup, the new item needs to be added
 * to the OrderedSelectBox cache, not just the raw select element.
 */
(function() {
  'use strict';

  /**
   * Find an OrderedSelectBox element by various lookup strategies.
   * Returns the "_from" select element if found, otherwise null.
   *
   * @param {string} windowName - The popup window name (e.g., "add_id_authors_12345")
   * @returns {HTMLSelectElement|null} The matching select element or null
   */
  function findOrderedSelectBoxElement(windowName) {
    // Extract base name from window name (remove "add_" prefix and trailing "_<digits>")
    var name = windowName.replace(/^add_/, '').replace(/_+\d+$/, '');

    console.log('[OrderedSelectBox] Looking for element, windowName:', windowName, '-> parsed name:', name);

    // Strategy 1: Direct ID lookup (for non-transformed elements)
    var elem = document.getElementById(name);
    if (elem && elem.classList.contains('filtered')) {
      console.log('[OrderedSelectBox] Found via Strategy 1 (direct ID):', elem.id);
      return elem;
    }

    // Strategy 2: Look for the "_from" version (our widget renames the original)
    elem = document.getElementById(name + '_from');
    if (elem && elem.classList.contains('filtered')) {
      console.log('[OrderedSelectBox] Found via Strategy 2 (_from suffix):', elem.id);
      return elem;
    }

    // Strategy 3: Find by name attribute with "_old" suffix
    // (our widget changes the name from "fieldname" to "fieldname_old")
    var selects = document.querySelectorAll('select.filtered[name$="_old"]');
    console.log('[OrderedSelectBox] Strategy 3: Found', selects.length, 'select.filtered[name$="_old"] elements');
    for (var i = 0; i < selects.length; i++) {
      var selectName = selects[i].getAttribute('name');
      // Strip "_old" and check if it matches
      var baseName = selectName.replace(/_old$/, '');
      console.log('[OrderedSelectBox] Strategy 3: Checking', selectName, '-> baseName:', baseName);
      // The name attribute won't have "id_" prefix, so check both
      if (baseName === name || 'id_' + baseName === name) {
        console.log('[OrderedSelectBox] Found via Strategy 3 (name attribute):', selects[i].id);
        return selects[i];
      }
    }

    // Strategy 4: Check if any of our cached elements match
    // This handles cases where ID patterns don't match expectations
    console.log('[OrderedSelectBox] Strategy 4: Checking cache keys:', Object.keys(OrderedSelectBox.cache));
    for (var cacheId in OrderedSelectBox.cache) {
      if (OrderedSelectBox.cache.hasOwnProperty(cacheId) && cacheId.endsWith('_from')) {
        var baseId = cacheId.replace(/_from$/, '');
        // Check if the base ID is related to the window name
        if (name === baseId || name.endsWith(baseId) || baseId.endsWith(name)) {
          elem = document.getElementById(cacheId);
          if (elem && elem.classList.contains('filtered')) {
            console.log('[OrderedSelectBox] Found via Strategy 4 (cache inspection):', elem.id);
            return elem;
          }
        }
      }
    }

    console.warn('[OrderedSelectBox] No element found for windowName:', windowName);
    return null;
  }

  /**
   * Set up the popup override once Django's functions are available.
   */
  var setupPopupOverride = function() {
    // Check if popup functions exist
    if (typeof window.dismissAddRelatedObjectPopup === 'undefined') {
      console.log('[OrderedSelectBox] setupPopupOverride: dismissAddRelatedObjectPopup not yet defined');
      return;
    }

    console.log('[OrderedSelectBox] setupPopupOverride: Installing custom dismissAddRelatedObjectPopup');

    // Store original function
    var originalDismissAddRelatedObjectPopup = window.dismissAddRelatedObjectPopup;

    /**
     * Custom dismissAddRelatedObjectPopup that handles OrderedSelectBox widgets.
     *
     * @param {Window} win - The popup window object
     * @param {string} newId - The ID of the newly created object
     * @param {string} newRepr - The string representation of the new object
     */
    window.dismissAddRelatedObjectPopup = function(win, newId, newRepr) {
      console.log('[OrderedSelectBox] dismissAddRelatedObjectPopup called:', {
        windowName: win.name,
        newId: newId,
        newRepr: newRepr
      });

      var elem = findOrderedSelectBoxElement(win.name);

      if (elem) {
        // This is an OrderedSelectBox widget
        // Determine the "_to" box ID (where chosen items go)
        var toId;
        if (elem.id.endsWith('_from')) {
          toId = elem.id.replace(/_from$/, '_to');
        } else {
          toId = elem.id + '_to';
        }

        console.log('[OrderedSelectBox] Target toId:', toId);

        // Verify the "_to" box exists and is initialized
        var toBox = document.getElementById(toId);
        var cacheExists = OrderedSelectBox.cache[toId] !== undefined;

        console.log('[OrderedSelectBox] toBox element:', toBox ? 'found' : 'NOT FOUND');
        console.log('[OrderedSelectBox] cache[toId] exists:', cacheExists);

        if (toBox && cacheExists) {
          // Add the new option to the chosen box
          var newOption = new Option(newRepr, newId);
          OrderedSelectBox.add_to_cache(toId, newOption);
          OrderedSelectBox.redisplay(toId);

          // Refresh icons if OrderedSelectFilter is available
          if (typeof OrderedSelectFilter !== 'undefined') {
            var fieldId = elem.id.replace(/_from$/, '');
            OrderedSelectFilter.refresh_icons(fieldId);
          }

          console.log('[OrderedSelectBox] Successfully added new item and closing popup');
          win.close();
          return;
        } else {
          console.error('[OrderedSelectBox] Cannot add to cache - toBox or cache missing!');
        }
      }

      // Fall back to original behavior for non-OrderedSelectBox widgets
      console.log('[OrderedSelectBox] Falling back to original dismissAddRelatedObjectPopup');
      if (originalDismissAddRelatedObjectPopup) {
        originalDismissAddRelatedObjectPopup(win, newId, newRepr);
      }
    };
  };

  // Set up immediately if functions are available, otherwise wait for load
  if (document.readyState === 'complete') {
    console.log('[OrderedSelectBox] Document complete, setting up popup override now');
    setupPopupOverride();
  } else {
    console.log('[OrderedSelectBox] Document not complete, waiting for load event');
    window.addEventListener('load', setupPopupOverride);
  }
})();