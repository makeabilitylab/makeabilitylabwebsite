// Reusable filter bar module
//
// usage: $('#filter-bar').filterBar(options)
// 		the options should include:
//			items: a list of items in the order they should be displayed (e.g., reverse chronological)
//			categories: a list of categories in the order they should be displayed in the sidebar
//			groupsForCategory: a dictionary of grouped items for each category
//				for example, {"category": [{"name": "group1", "items", [item1, item2, item3]}]}
//			passesFilter: a function that returns true if the item passes the filter value and false if not
//			displayGroupHeader: a function that formats the group header for display, and returns the html that should be appended
//			displayItem: a function that formats the item for display, and returns the html that should be appended
//			afterDisplay: an optional function that is called after initialization or after the filter is updated
//
// 		if you need to re-apply the filter or select the category, you can call
//			$('#filter-bar').applyFilter(category)
//		where category is an optional category name from those defined in the initial filterBar call

(function($) {
	var filterBar, currCategory, settings;

	$.fn.filterBar = function(options) {

		// save a reference to "this" so that we can refer to it in the event handlers below
		filterBar = this;

		// This is the easiest way to have default options.
        settings = $.extend({
            // These are the defaults.
            items: [],
            categories: ["None"],
            groupsForCategory: {"None": []},
            passesFilter: function(item, filter) { return true; },
            displayGroupHeader: function(group) { return group.toString(); },
            displayItem: function(item) { return item.toString(); },
            afterDisplay: function() { return; }
        }, options );

        currCategory = settings.categories[0];

		// append filter bar content
		filterBar.append("<h1 style=\"margin-top:7px\">FILTER</h1><input class=\"shortTextbox\" id=\"filter-textbox\" type=\"text\" value=\"\" /><h1>GROUP BY</h1>");

		categoryList = $(document.createElement("div"));
		categoryList.addClass("filter-bar-categories");
		$(settings.categories).each(function() {
			var categoryItem = $(document.createElement("li"));
			var categoryText = this;
			categoryItem.addClass("filter-category");
			categoryItem.attr("id", "filter-category-" + categoryText.toLowerCase().replace(new RegExp(" "), "-"));
			categoryItem.click(function() { filterBar.applyFilter(categoryText); });
			categoryItem.text(categoryText);
			categoryList.append(categoryItem);
		});
		filterBar.append(categoryList);

		filterBar.append("<div id=\"filter-bar-groups\"></div>");

		// update the filtered items whenever the filter textbox changes
		// note: it's not enough just to bind to keyup, since there are other 
		//       ways for the text to change
		$("#filter-textbox").on("propertychange change keyup paste input", function(){
			filterBar.applyFilter();
		});

		return this;
	};

	$.fn.applyFilter = function(newCategory) {
		if(newCategory) currCategory = newCategory;
		$(".filter-category").removeClass("filter-selected");
		$("#filter-category-" + currCategory.toLowerCase().replace(new RegExp(" "), "-")).addClass("filter-selected");

		var groupList = $("#filter-bar-groups");
		if(settings.groupsForCategory[currCategory].length <= 1) {
			groupList.css("display", "none");
		} else {
			groupList.css("display", "block");
			var data = "<h1>" + currCategory.toUpperCase() + "</h1>\n"
			for(var i=0; i<settings.groupsForCategory[currCategory].length; i++) {
				data += "<li><a href=\"#" + settings.groupsForCategory[currCategory][i].name + "\" class=\"scroll\">" + settings.groupsForCategory[currCategory][i].name + " (" + settings.groupsForCategory[currCategory][i].items.length + ")</a></li>\n";
			}
			groupList[0].innerHTML = data;
		}

		$('#fixed-side-bar').resizeSideBar();

		var content = $("#main-content")[0];
		var data = "";
		var filter = $("#filter-textbox").val().toLowerCase();
		settings.groupsForCategory[currCategory].forEach(function (group, groupIndex, groupArray) {
			var groupCount = 0;
			group.items.forEach(function(item, itemIndex, itemArray) { if(settings.passesFilter(item, filter)) groupCount++; });
			if(groupCount == 0) return;

			data += settings.displayGroupHeader(group.name);
			group.items.forEach(function (item, itemIndex, itemArray) {
				if(!settings.passesFilter(item, filter)) return;
				data += settings.displayItem(item, filter);
			});
		});
		content.innerHTML = data;
		settings.afterDisplay();
	}

}(jQuery));