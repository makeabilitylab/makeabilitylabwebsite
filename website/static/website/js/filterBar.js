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

(function ($) {
    var filterBar, currCategory, settings;
    var oldfilter = ".";

    // debounce so filtering doesn't happen every millisecond
    function debounce(fn, threshold) {

        var timeout;
        return function debounced() {
            if (timeout) {
                clearTimeout(timeout);
            }

            function delayed() {
                fn();
                timeout = null;
            }

            timeout = setTimeout(delayed, threshold || 100);
        }
    }

    $.fn.filterBar = function (options) {

        // save a reference to "this" so that we can refer to it in the event handlers below
        filterBar = this;

        // This is the easiest way to have default options.
        settings = $.extend({
            // These are the defaults.
            items: [],
            categories: ["None"],
            defaultCategory:  null,
            groupsForCategory: {"None": []},
            passesFilter: function (item, filter) {
                return true;
            },
            displayGroupHeader: function (group) {
                return group.toString();
            },
            displayItem: function (item) {
                return item.toString();
            },
            afterDisplay: function () {
                return;
            },

        }, options);

       if (settings.defaultCategory && $.inArray(settings.defaultCategory, settings.categories) >= 0){
            currCategory = settings.defaultCategory
        }else {
            currCategory = settings.categories[0];
        }


        // append filter bar content
        filterBar.append("<h1 style=\"margin-top:7px\">FILTER</h1><input class=\"shortTextbox\" id=\"filter-textbox\" type=\"text\" value=\"\" /><h1>GROUP BY</h1>");
        $("#filter-textbox").autocomplete({
            source: settings.keywords,
            appendTo: "#fixed-side-bar"
        });
        categoryList = $(document.createElement("div"));
        categoryList.addClass("filter-bar-categories");
        $(settings.categories).each(function () {
            var categoryItem = $(document.createElement("li"));
            var categoryText = this;
            categoryItem.addClass("filter-category");
            categoryItem.attr("id", "filter-category-" + categoryText.toLowerCase().replace(new RegExp(" "), "-"));
            categoryItem.click(function () {
                debounce(filterBar.applyFilter(categoryText), 1000);
            });
            categoryItem.text(categoryText);
            categoryList.append(categoryItem);
        });
        filterBar.append(categoryList);

        filterBar.append("<div id=\"filter-bar-groups\"></div>");

        // update the filtered items whenever the filter textbox changes
        // note: it's not enough just to bind to keyup, since there are other
        //       ways for the text to change
        $("#filter-textbox").on("propertychange change keyup paste input", function () {
            debounce(filterBar.applyTextFilter(), 500);
        });
        $("#filter-textbox-backup").on("propertychange change keyup paste input", function () {
            debounce(filterBar.applyTextFilter(), 500);
        });

        filterBar.applyFilter();
        if (initialFilter && initialFilter.length > 0 && initialFilter != "None") {
            $('#filter-textbox').val(initialFilter);
            filterBar.applyTextFilter();
        }

        if (initialGroupBy) {
            var matchesGroup = false;
            for (var i = 0; i < settings.categories.length; i++)
                if (initialGroupBy.toLowerCase() === settings.categories[i].toLowerCase()) {
                    matchesGroup = true;
                    initialGroupBy = settings.categories[i];
                }

            if (matchesGroup) {
                filterBar.applyFilter(initialGroupBy);
                console.log("applied filter: " + initialGroupBy);
            }
        }

        return this;

    };

    $.fn.cleanName = function (name) {
        return name.toLowerCase().replace(new RegExp(" ", "g"), "-");
    }

    $.fn.applyFilter = function (newCategory) {
        if (newCategory) currCategory = newCategory;
        var filter = $("#filter-textbox").val().toLowerCase() || $("#filter-textbox-backup").val().toLowerCase();
        $(".filter-category").removeClass("filter-selected");
        $("#filter-category-" + this.cleanName(currCategory)).addClass("filter-selected");

        var groupList = $("#filter-bar-groups");
        if (settings.groupsForCategory[currCategory].length <= 1) {
            groupList.css("display", "none");
        } else {
            groupList.css("display", "block");
            var data = "<h1>" + currCategory.toUpperCase() + "</h1>\n"
            for (var i = 0; i < settings.groupsForCategory[currCategory].length; i++) {
                data += "<li><a href=\"#" + this.cleanName(settings.groupsForCategory[currCategory][i].name) + "\" class=\"scroll\" title=\"" + settings.groupsForCategory[currCategory][i].name + "\"><span class=\"filter-group\">" + settings.groupsForCategory[currCategory][i].name + "</span><span class=\"filter-group-count\"> (" + settings.groupsForCategory[currCategory][i].items.length + ")</span></a></li>\n";
            }
            groupList[0].innerHTML = data;
        }

        $('#fixed-side-bar').resizeSideBar();

        var content = $("#main-content")[0];
        var data = "";
        settings.groupsForCategory[currCategory].forEach(function (group, groupIndex, groupArray) {
            var groupCount = 0;
            group.items.forEach(function (item, itemIndex, itemArray) {
                if (settings.passesFilter(item, filter)) groupCount++;
            });
            if (groupCount == 0) return;

            data += settings.displayGroupHeader(group.name);
            group.items.forEach(function (item, itemIndex, itemArray) {
                if (!settings.passesFilter(item, filter)) return;
                data += settings.displayItem(item, filter);
            });
        });
        content.innerHTML = data;
        settings.afterDisplay();
    }

    function checkFilter(groups, title, filter, groupPasses) {
        var res = false;
        groups.forEach(function (group, groupIndex, groupArray) {
            group.items.forEach(function (item, itemIndex, itemArray) {
                if (item['title'].trim() == title.trim()) {
                    if (settings.passesFilter(item, filter)) {
                        res = true;
                        groupPasses[group['name']]++;
                    }
                    else {
                        res = false;
                    }
                }
            });
        });
        return res;
    }

    // adds html markup to the specified text wherever it matches the filter, applying the highlight style
    function addHighlight(text, filter) {
        var result = text;
        if (filter && filter.length > 0)
            result = text.replace(new RegExp('(' + filter + ')', 'gi'), "<span class=\"highlight\">$1</span>");
        return result;
    }

    function removeHighlight(text) {
        text.replace(new RegExp('(<span class=\"highlight\">*</span>)', 'gi'), "");
        return text;
    }

    function resetHTML($template) {
        $template.find('.publication-keywords').children().each(function () {
            $(this).html(removeHighlight($(this).html()));
        });
    }

    //This will check each entry and highlight text as appropriate.
    //TODO: now that I am updating the css to be more general and switching things like publication-title or video-title to artifact-title,
    //      we should be able to simplify this code and make it more generalizable and less .css file specific
    $.fn.applyTextFilter = function () {
        var filter = $("#filter-textbox").val().toLowerCase() || $("#filter-textbox-backup").val().toLowerCase();
        var groups = settings.groupsForCategory[currCategory];
        var groupPasses = {};
        groups.forEach(function (group, groupIndex, groupArray) {
            groupPasses[group['name']] = 0;
        });
        if (oldfilter != filter) {
            //TODO: Ack, imo, this filter stuff should be content agnostic, so should not be referring to
            //specific tags in publication, talks, videos, unless those tags are universal across each
            $('.publication-template').each(function () {
                var title = $(this).find('.artifact-title').text();
                title = title.replace(/(<([^>]+)>)/ig, "");
                var passes = checkFilter(groups, title, filter, groupPasses);
                if (!passes) {
                    $(this).fadeOut();
                    //resetHTML($(this));
                }
                else {
                    $(this).fadeIn();
                    $(this).find('.publication-keywords').children().each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });
                    $(this).find('.publication-authors').children().each(function () {
                        $(this).find('a').html(addHighlight($(this).find('a').text(), filter));
                    });
                    $(this).find('.artifact-title').each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });
                    $(this).find('.publication-venue').each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });
                }
            });

            $('.talk-template').each(function () {
                var title = $(this).find('.artifact-title').text();
                var passes = checkFilter(groups, title, filter, groupPasses);
                if (!passes) {
                    $(this).fadeOut();
                }
                else {
                    $(this).fadeIn();
                    $(this).find('.talk-speakers').children().each(function () {
                        $(this).find('a').html(addHighlight($(this).find('a').text(), filter));
                    });
                    $(this).find('.artifact-title').each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });
                }
            });

            $('.video-template').each(function () {
                var title = $(this).find('.artifact-title').text();
                var passes = checkFilter(groups, title, filter, groupPasses);
                if (!passes) {
                    $(this).fadeOut();
                }
                else {
                    $(this).fadeIn();

                    $(this).find('.artifact-title').each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });

                    $(this).find('.video-caption').each(function () {
                        $(this).html(addHighlight($(this).text(), filter));
                    });
                }
            });

            for (var key in groupPasses) {
                if (groupPasses[key] == 0) {
                    $('h1[name=' + key + ']').fadeOut();
                }
                else {
                    $('h1[name=' + key + ']').fadeIn();
                }
            }
            oldfilter = filter;
        }

    }

}(jQuery));
