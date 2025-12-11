/**
 * OrderedSelectBox - Manage select box contents with ordering support
 *
 * Provides caching and manipulation of select box options, including
 * filtering, moving between boxes, and reordering.
 *
 * Used by OrderedSelectFilter for the sorted many-to-many widget.
 *
 * @version 2.0.0 - jQuery-free version for Django 5.x
 */

var OrderedSelectBox = {
  /**
   * Cache of select box contents.
   * Keys are select element IDs, values are arrays of option objects.
   * @type {Object.<string, Array>}
   */
  cache: {},

  /**
   * Initialize the cache for a select box.
   *
   * @param {string} id - The select element ID
   */
  init: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
   */
  redisplay: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
   */
  add_to_cache: function(id, option) {
    if (!OrderedSelectBox.cache[id]) {
      OrderedSelectBox.cache[id] = [];
    }

    // Get sort order from data attribute
    var order = 0;
    var sortValue = option.getAttribute('data-sort-value');
    if (sortValue) {
      order = parseInt(sortValue, 10);
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
   * Move selected options from one select to another.
   *
   * @param {string} from - Source select element ID
   * @param {string} to - Destination select element ID
   */
  move: function(from, to) {
    var from_box = document.getElementById(from);
    var to_box = document.getElementById(to);

    if (!from_box || !to_box) return;

    // Reset order values in destination (items are appended in order)
    var to_cache = OrderedSelectBox.cache[to] || [];
    for (var i = 0; i < to_cache.length; i++) {
      to_cache[i].order = 0;
    }

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
   */
  move_all: function(from, to) {
    var from_box = document.getElementById(from);

    if (!from_box) return;

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
   * Sort the cache alphabetically by text.
   *
   * @param {string} id - The select element ID
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
  },

  /**
   * Move selected options up in the list.
   *
   * @param {string} id - The select element ID
   */
  orderUp: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
   */
  orderDown: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
   */
  sync_cache_from_dom: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
   */
  select_all: function(id) {
    var box = document.getElementById(id);
    if (!box) return;

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
if (typeof window.showAddAnotherPopup !== 'undefined' || typeof window.showRelatedObjectPopup !== 'undefined') {
  // Store original function
  var originalDismissAddRelatedObjectPopup = window.dismissAddRelatedObjectPopup;

  window.dismissAddRelatedObjectPopup = function(win, newId, newRepr) {
    // Get the target element name from the popup window name
    var name = win.name.replace(/^add_/, '').replace(/_\d+$/, '');

    // Try to find the element - might be the _from version
    var elem = document.getElementById(name);
    if (!elem) {
      elem = document.getElementById(name + '_from');
    }

    if (!elem) {
      // Fall back to finding by name attribute
      var selects = document.querySelectorAll('select[name="' + name + '_old"]');
      if (selects.length > 0) {
        elem = selects[0];
      }
    }

    if (elem && elem.className.indexOf('filtered') !== -1) {
      // This is an OrderedSelectBox - add to the "to" (chosen) box
      var toId = elem.id.replace('_from', '_to');
      if (toId === elem.id) {
        toId = elem.id + '_to';
      }

      var newOption = new Option(newRepr, newId);
      OrderedSelectBox.add_to_cache(toId, newOption);
      OrderedSelectBox.redisplay(toId);
      win.close();
    } else if (originalDismissAddRelatedObjectPopup) {
      // Fall back to original behavior
      originalDismissAddRelatedObjectPopup(win, newId, newRepr);
    }
  };
}
