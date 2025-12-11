/**
 * OrderedSelectFilter - Filter interface for sorted many-to-many fields
 *
 * Transforms a multiple-select box into a two-panel filter interface
 * with ordering controls. Based on Django admin's SelectFilter2 but
 * with added support for maintaining selection order.
 *
 * Requires: OrderedSelectBox.js, Django admin's core.js (for quickElement, gettext)
 *
 * @version 2.0.0 - Django 5.x compatible
 */

/**
 * Find the form element containing a given node.
 * Used to attach submit handlers.
 *
 * @param {HTMLElement} node - Starting node
 * @returns {HTMLFormElement} The containing form
 */
function findForm(node) {
  if (node.tagName.toLowerCase() !== 'form') {
    return findForm(node.parentNode);
  }
  return node;
}

var OrderedSelectFilter = {
  /**
   * Initialize the filter widget for a select element.
   *
   * Transforms a regular multi-select into the two-panel interface
   * with available/chosen lists, transfer buttons, and ordering controls.
   *
   * @param {string} field_id - The ID of the select element to transform
   * @param {string} field_name - Human-readable name for labels
   * @param {boolean} is_stacked - If true, use vertical layout
   * @param {string} admin_media_prefix - Path to admin static files (unused in Django 5+)
   */
  init: function(field_id, field_name, is_stacked, admin_media_prefix) {
    // Don't initialize placeholder elements in empty inline forms
    if (field_id.match(/__prefix__/)) {
      return;
    }

    var from_box = document.getElementById(field_id);

    // Guard against missing element or double-initialization
    if (!from_box) {
      return;
    }
    if (from_box.id.endsWith('_from')) {
      return; // Already initialized
    }

    from_box.id += '_from'; // Change ID to indicate "available" box
    from_box.className = 'filtered';

    // Clean up info/help paragraphs
    var ps = from_box.parentNode.getElementsByTagName('p');
    for (var i = ps.length - 1; i >= 0; i--) {
      if (ps[i].className.indexOf("info") !== -1) {
        // Remove info paragraphs - they clutter the interface
        from_box.parentNode.removeChild(ps[i]);
      } else if (ps[i].className.indexOf("help") !== -1) {
        // Move help text to top
        from_box.parentNode.insertBefore(ps[i], from_box.parentNode.firstChild);
      }
    }

    // Create container: <div class="selector"> or <div class="selector stacked">
    var selector_div = quickElement('div', from_box.parentNode);
    selector_div.className = is_stacked ? 'selector stacked' : 'selector';

    // ===== AVAILABLE (left) panel =====
    var selector_available = quickElement('div', selector_div, '');
    selector_available.className = 'selector-available';

    var title_available = quickElement('h2', selector_available,
      interpolate(gettext('Available %s') + ' ', [field_name]));

    quickElement('span', title_available, '',
      'class', 'help help-tooltip help-icon',
      'title', interpolate(
        gettext('This is the list of available %s. You may choose some by selecting them in the box below and then clicking the "Choose" arrow between the two boxes.'),
        [field_name]
      )
    );

    // Filter input for available items
    var filter_p = quickElement('p', selector_available, '');
    filter_p.className = 'selector-filter';

    var search_filter_label = quickElement('label', filter_p, '', 'for', field_id + '_input');
    quickElement('span', search_filter_label, '',
      'class', 'help-tooltip search-label-icon',
      'title', interpolate(gettext('Type into this box to filter down the list of available %s.'), [field_name])
    );

    filter_p.appendChild(document.createTextNode(' '));

    var filter_input = quickElement('input', filter_p, '', 'type', 'text', 'placeholder', gettext('Filter'));
    filter_input.id = field_id + '_input';

    selector_available.appendChild(from_box);

    var choose_all = quickElement('a', selector_available, gettext('Choose all'),
      'title', gettext('Click to choose all options at once.'),
      'href', '#',
      'id', field_id + '_add_all_link');
    choose_all.className = 'selector-chooseall';

    // ===== TRANSFER buttons (between panels) =====
    var selector_chooser = quickElement('ul', selector_div);
    selector_chooser.className = 'selector-chooser';

    // Create the "Choose" (Right Arrow) Link
    var add_link = quickElement('a', quickElement('li', selector_chooser),
        '', 'title', gettext('Choose'), 'href', '#', 'id', field_id + '_add_link');
    add_link.className = 'selector-add';
    add_link.innerHTML = '&rarr;'; // Explicit HTML Entity for Right Arrow

    // Create the "Remove" (Left Arrow) Link
    var remove_link = quickElement('a', quickElement('li', selector_chooser),
        '', 'title', gettext('Remove'), 'href', '#', 'id', field_id + '_remove_link');
    remove_link.className = 'selector-remove';
    remove_link.innerHTML = '&larr;'; // Explicit HTML Entity for Left Arrow

    // ===== CHOSEN (right) panel =====
    var selector_chosen = quickElement('div', selector_div, '');
    selector_chosen.className = 'selector-chosen';

    var title_chosen = quickElement('h2', selector_chosen,
      interpolate(gettext('Chosen %s') + ' ', [field_name]));

    quickElement('span', title_chosen, '',
      'class', 'help help-tooltip help-icon',
      'title', interpolate(
        gettext('This is the list of chosen %s. You may remove some by selecting them in the box below and then clicking the "Remove" arrow between the two boxes.'),
        [field_name]
      )
    );

    // Create the "to" select box (chosen items)
    var to_box = quickElement('select', selector_chosen, '',
      'id', field_id + '_to',
      'multiple', 'multiple',
      'size', from_box.size,
      'name', from_box.getAttribute('name'));
    to_box.className = 'filtered';

    var clear_all = quickElement('a', selector_chosen, gettext('Remove all'),
      'title', gettext('Click to remove all chosen options at once.'),
      'href', '#',
      'id', field_id + '_remove_all_link');
    clear_all.className = 'selector-clearall';

    // ===== ORDER buttons (up/down) =====
    var order_chooser = quickElement('ul', selector_div);
    order_chooser.className = 'selector-chooser selector-ordering';

    var up_li = quickElement('li', order_chooser, '');
    var up_link = quickElement('a', up_li, '',
      'href', '#',
      'id', field_id + '_up_link',
      'title', gettext('Move selected items up'));
    up_link.className = 'selector-up';
    up_link.innerHTML = '&uarr;';

    var down_li = quickElement('li', order_chooser, '');
    var down_link = quickElement('a', down_li, '',
      'href', '#',
      'id', field_id + '_down_link',
      'title', gettext('Move selected items down'));
    down_link.className = 'selector-down';
    down_link.innerHTML = '&darr;';

    // Change the "from" box name so only "to" box submits
    from_box.setAttribute('name', from_box.getAttribute('name') + '_old');

    // ===== EVENT HANDLERS =====

    /**
     * Handle move actions with active state checking
     */
    var move_selection = function(e, elem, move_func, from, to) {
      if (elem.className.indexOf('active') !== -1) {
        move_func(from, to);
        OrderedSelectFilter.refresh_icons(field_id);
      }
      e.preventDefault();
    };

    choose_all.addEventListener('click', function(e) {
      move_selection(e, this, OrderedSelectBox.move_all, field_id + '_from', field_id + '_to');
    });

    add_link.addEventListener('click', function(e) {
      move_selection(e, this, OrderedSelectBox.move, field_id + '_from', field_id + '_to');
    });

    remove_link.addEventListener('click', function(e) {
      move_selection(e, this, OrderedSelectBox.move, field_id + '_to', field_id + '_from');
    });

    clear_all.addEventListener('click', function(e) {
      move_selection(e, this, OrderedSelectBox.move_all, field_id + '_to', field_id + '_from');
    });

    // Ordering button handlers
    up_link.addEventListener('click', function(e) {
      e.preventDefault();
      OrderedSelectBox.orderUp(field_id + '_to');
    });

    down_link.addEventListener('click', function(e) {
      e.preventDefault();
      OrderedSelectBox.orderDown(field_id + '_to');
    });

    // Filter input handlers
    filter_input.addEventListener('keypress', function(e) {
      OrderedSelectFilter.filter_key_press(e, field_id);
    });

    filter_input.addEventListener('keyup', function(e) {
      OrderedSelectFilter.filter_key_up(e, field_id);
    });

    filter_input.addEventListener('keydown', function(e) {
      OrderedSelectFilter.filter_key_down(e, field_id);
    });

    // Selection change handler
    selector_div.addEventListener('change', function(e) {
      if (e.target.tagName === 'SELECT') {
        OrderedSelectFilter.refresh_icons(field_id);
      }
    });

    // Double-click to transfer
    selector_div.addEventListener('dblclick', function(e) {
      if (e.target.tagName === 'OPTION') {
        var parentSelect = e.target.closest('select');
        if (parentSelect && parentSelect.id === field_id + '_to') {
          OrderedSelectBox.move(field_id + '_to', field_id + '_from');
        } else {
          OrderedSelectBox.move(field_id + '_from', field_id + '_to');
        }
        OrderedSelectFilter.refresh_icons(field_id);
      }
    });

    // Select all chosen items before form submission
    findForm(from_box).addEventListener('submit', function() {
      OrderedSelectBox.select_all(field_id + '_to');
    });

    // Initialize the OrderedSelectBox caches
    OrderedSelectBox.init(field_id + '_from');
    OrderedSelectBox.init(field_id + '_to');

    // Move initially selected items to the "to" box
    OrderedSelectBox.move(field_id + '_from', field_id + '_to');

    // Match heights in horizontal mode
    if (!is_stacked) {
      var resizeFilters = function() {
        var fromHeight = from_box.offsetHeight;
        var filterHeight = filter_p.offsetHeight;
        if (fromHeight > 0) {
          to_box.style.height = (filterHeight + fromHeight) + 'px';
        }
      };

      // Try to resize immediately, or wait for fieldset to open
      if (from_box.offsetHeight > 0) {
        resizeFilters();
      } else {
        // For collapsed fieldsets, resize when they open
        var fieldset = from_box.closest('fieldset');
        if (fieldset) {
          fieldset.addEventListener('show.fieldset', resizeFilters, { once: true });
        }
      }
    }

    // Initial icon state
    OrderedSelectFilter.refresh_icons(field_id);
  },

  /**
   * Update the active/inactive state of all action buttons.
   *
   * @param {string} field_id - Base field ID (without _from/_to suffix)
   */
  refresh_icons: function(field_id) {
    var from_box = document.getElementById(field_id + '_from');
    var to_box = document.getElementById(field_id + '_to');

    if (!from_box || !to_box) return;

    var is_from_selected = from_box.querySelector('option:checked') !== null;
    var is_to_selected = to_box.querySelector('option:checked') !== null;
    var is_from_non_empty = from_box.options.length > 0;
    var is_to_non_empty = to_box.options.length > 0;

    // Helper to toggle 'active' class
    var toggleActive = function(id, condition) {
      var elem = document.getElementById(id);
      if (elem) {
        elem.classList.toggle('active', condition);
      }
    };

    // Existing lines (Keep these)
    toggleActive(field_id + '_add_link', is_from_selected);
    toggleActive(field_id + '_remove_link', is_to_selected);
    toggleActive(field_id + '_add_all_link', is_from_non_empty);
    toggleActive(field_id + '_remove_all_link', is_to_non_empty);

    // --- NEW LINES TO FIX UP/DOWN HOVER ---
    // If items are selected in the "To" box, we should be able to move them Up or Down
    toggleActive(field_id + '_up_link', is_to_selected);
    toggleActive(field_id + '_down_link', is_to_selected);
  },

  /**
   * Handle keypress in filter input (prevent form submission on Enter).
   */
  filter_key_press: function(event, field_id) {
    // Prevent form submission on Enter
    if (event.keyCode === 13) {
      event.preventDefault();
      return false;
    }
  },

  /**
   * Handle keyup in filter input (filter list and handle Enter).
   */
  filter_key_up: function(event, field_id) {
    var from_box = document.getElementById(field_id + '_from');

    // On Enter, transfer first visible item
    if (event.keyCode === 13) {
      from_box.selectedIndex = 0;
      OrderedSelectBox.move(field_id + '_from', field_id + '_to');
      from_box.selectedIndex = 0;
      OrderedSelectFilter.refresh_icons(field_id);
      return false;
    }

    // Filter the list
    var temp = from_box.selectedIndex;
    var filter_value = document.getElementById(field_id + '_input').value;
    OrderedSelectBox.filter(field_id + '_from', filter_value);
    from_box.selectedIndex = temp;

    return true;
  },

  /**
   * Handle keydown in filter input (arrow key navigation and quick transfer).
   */
  filter_key_down: function(event, field_id) {
    var from_box = document.getElementById(field_id + '_from');

    // Right arrow: transfer selected item
    if (event.keyCode === 39) {
      var old_index = from_box.selectedIndex;
      OrderedSelectBox.move(field_id + '_from', field_id + '_to');
      from_box.selectedIndex = (old_index === from_box.length) ? from_box.length - 1 : old_index;
      OrderedSelectFilter.refresh_icons(field_id);
      return false;
    }

    // Down arrow: wrap around to top
    if (event.keyCode === 40) {
      from_box.selectedIndex = (from_box.length === from_box.selectedIndex + 1) ? 0 : from_box.selectedIndex + 1;
    }

    // Up arrow: wrap around to bottom
    if (event.keyCode === 38) {
      from_box.selectedIndex = (from_box.selectedIndex === 0) ? from_box.length - 1 : from_box.selectedIndex - 1;
    }

    return true;
  }
};
