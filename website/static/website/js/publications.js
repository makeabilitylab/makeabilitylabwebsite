// TODO: separate filter code, make generalizable
// Note: this code depends on a variable called "publications" that contains
// 		 all of the publication data in json format. It should be initialized in
//		 the Django template file.

var groupMode = "year"; // can be year, pub-type, keyword, project, or none
var filterTop = 0, filterInitOffset = 0;
var groupedPublications = [];

// dictionary for abbreviated publication types
// TODO: this should probably go in the model instead of here
var pubTypeCodes = {
	"Conference": "C",
	"Article": "A",
	"Journal": "J",
	"Book Chapter": "BC",
	"Book": "B",
	"MS Thesis": "T",
	"PhD Dissertation": "D",
	"Workshop": "W",
    "Poster": "P",
    "Demo": "Dm",
    "Work in Progress": "WiP",
    "Late Breaking Result": "LBR",
    "Other": "O"
};

// initialization code that's called when the window has finished loading
$(window).load(function () {

	// save the current position of the filter bar to use when scrolling
	filterTop = $('.filter-bar').offset().top - parseInt($('.filter-bar').css('margin-top'));
	filterInitOffset = $('.filter-bar').css('top');

	// update the list of publications whenever the filter textbox changes
	// note: it's not enough just to bind to keyup, since there are other 
	//       ways for the text to change
	$("#filter-textbox").on("propertychange change keyup paste input", function(){
		groupPublications();
    	updateDisplay();
	});

	// Hide popovers when clicking outside, but not when clicking inside
	// from: http://stackoverflow.com/a/14857326
	// LS: this is a bit of a hack, since the default click behavior leaves them open
	// until you click on the button again, but the default focus behavior prevents you
	// from interacting with the content of the popover
	$('body').on('click', function (e) {
	    $('[data-toggle="popover"]').each(function () {
	        //the 'is' for buttons that trigger popups
	        //the 'has' for icons within a button that triggers a popup
	        if (!$(this).is(e.target) && $(this).has(e.target).length === 0 && $('.popover').has(e.target).length === 0) {
	            $(this).popover('hide');
	        }
	    });
	});

	preprocessPublications();
	groupPublications();
	updateDisplay();
});

// when the window scrolls, need to adjust the position of the filter bar
$(window).scroll(function(event) {
	// check the vertical position of the scroll
    var y = $(this).scrollTop();

    var filterBar = $('.filter-bar');

    // is it below the form?
    if (y >= filterTop) {
        // if so, set fixed position
        filterBar.css('position', 'fixed');
        filterBar.css('top', '0');
        filterBar.css('left', parseInt($('#content').css('margin-left')) + "px");
    } else {
        // otherwise set absolute position
        filterBar.css('position', 'absolute');
        filterBar.css('top', filterInitOffset);
        filterBar.css('left', "0");
    }
});

// when the window is resized, need to adjust the filter bar position and 
// publication list height to avoid formatting issues
$(window).resize(resize);
function resize() {
	var filterBar = $('.filter-bar');
	var minHeight = filterBar.height() + 10; // should probably use something from the css rather than a magic number here
	var publicationList = $('#publication-list');
	publicationList.css('min-height', minHeight + "px");

	if(filterBar.css('position') == "fixed") {
		filterBar.css('left', parseInt($('#content').css('margin-left')) + "px");
	} else {
		filterBar.css('left', 0);
	}
}

// run some additional processing on the publications
function preprocessPublications() {
	var pubTypeCount = {};

	// sort by date
	publications.sort(function(a, b) {
		return a.date - b.date;
	});

	// group into publication types, initialize publication ids (e.g., C.1 for first conference paper)
	publications.forEach(function(pub, index, array) {
		if(!(pub.pub_type in pubTypeCount)) {
			pubTypeCount[pub.pub_type] = 1;
		} else {
			pubTypeCount[pub.pub_type]++;
		}

		pub.id = "[" + pubTypeCodes[pub.pub_type] + "." + pubTypeCount[pub.pub_type] + "]";
	});
	publications.reverse(); // most recent first

	// connect the array index to the dictionary objects for reverse lookup
	publications.forEach(function(pub, index, array) {
		pub["index"] = index;
	});
}

// called when the filter group is changes
function setGrouping(newGroupMode) {
	groupMode = newGroupMode;
	groupPublications();
	updateDisplay();
}

// group the publications by the selected grouping mode
function groupPublications() {
	$(".group-type").removeClass("filter-selected");
	$("#group-" + groupMode).addClass("filter-selected");

	var tempGroupedPublications = {};
	groupedPublications = [];
	publications.forEach(function(pub, index, array) {
		
		if(!passesFilter(pub)) return; // ignore publications that don't pass the filter
		
		if(groupMode === "year") {
			var group = pub.date.getFullYear().toString();
			if(!(group in tempGroupedPublications)) {
				tempGroupedPublications[group] = [];
			}
			tempGroupedPublications[group].push(pub);
		} else if(groupMode === "pub-type") {
			var group = pub.pub_type;
			if(!(group in tempGroupedPublications)) {
				tempGroupedPublications[group] = [];
			}
			tempGroupedPublications[group].push(pub);
		} else if(groupMode === "keyword") {
			var groups = pub.keywords;
			groups.forEach(function(group, index, array) {
				if(!(group in tempGroupedPublications)) {
					tempGroupedPublications[group] = [];
				}
				tempGroupedPublications[group].push(pub);
			});
		} else if(groupMode === "project") {
			var groups = pub.projects;
			groups.forEach(function(group, index, array) {
				if(!(group in tempGroupedPublications)) {
					tempGroupedPublications[group] = [];
				}
				tempGroupedPublications[group].push(pub);
			});
		} else {
			var group = "Chronological List";
			if(!(group in tempGroupedPublications)) {
				tempGroupedPublications[group] = [];
			}
			tempGroupedPublications[group].push(pub);
		}
	});

	for(group in tempGroupedPublications) {
		groupedPublications.push({"name": group, "items": tempGroupedPublications[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	if(groupMode === "year") {
		groupedPublications.sort(function(a,b) { return parseInt(b.name) - parseInt(a.name) });
	} else if(groupMode === "pub-type" || groupMode === "keyword" || groupMode === "project") {
		groupedPublications.sort(function(a,b) { return b.items.length - a.items.length });
	}

	// update the filter bar's sub-groups for the current grouping
	var groupList = $(".filter-bar-items");
	if(groupMode === "none") {
		groupList.css("display", "none");
	} else {
		groupList.css("display", "block");
		var displayGroupMode = groupMode.toUpperCase().replace("-", " ");
		var data = "<h1>" + displayGroupMode + "</h1>\n"
		for(var i=0; i<groupedPublications.length; i++) {
			data += "<li><a href=\"#" + groupedPublications[i].name + "\" class=\"scroll\">" + groupedPublications[i].name + " (" + groupedPublications[i].items.length + ")</a></li>\n";
		}
		groupList[0].innerHTML = data;
	}
}

// returns true if the publication contains the text entered into the filter box anywhere
// in the title, authors, venue, keywords, or projects
function passesFilter(pub) {
	var filter = $('#filter-textbox').val().toLowerCase();
	var passes = false;
	if(!filter || filter.length == 0) passes = true;

	if(pub.title.toLowerCase().indexOf(filter) >= 0) passes = true;
	if(pub.venue.toLowerCase().indexOf(filter) >= 0) passes = true;
	pub.authors.forEach(function(author, index, array) { 
		if(author.name.toLowerCase().indexOf(filter) >= 0) passes = true; 
	});
	pub.keywords.forEach(function(keyword, index, array) { if(keyword.toLowerCase().indexOf(filter) >= 0) passes = true; });
	pub.projects.forEach(function(project, index, array) { if(project.toLowerCase().indexOf(filter) >= 0) passes = true; });

	return passes;
}

// helper function to group display functions
function updateDisplay() {
	displayPublications();
	resize();
}

// adds html markup to the specified text wherever it matches the filter, applying the highlight style
function addHighlight(text) {
	var result = text;
	var filter = $('#filter-textbox').val().toLowerCase();
	if(filter && filter.length > 0)
		result = text.replace(new RegExp('(' + filter + ')', 'gi'), "<span class=\"highlight\">$1</span>");
	return result;
}

// displays the grouped publications matching the current filter in the main panel
function displayPublications() {
	var content = $("#publication-list")[0];
	var data = "";
	groupedPublications.forEach(function (group, groupIndex, groupArray) {
		var groupCount = 0;
		group.items.forEach(function(pub, pubIndex, pubArray) { if(passesFilter(pub))groupCount++; });
		if(groupCount == 0) return;

		data += "<h1 name=\"" + group.name + "\">" + group.name + "</h1>";
		group.items.forEach(function (pub, pubIndex, pubArray) {
			if(!passesFilter(pub)) return;
			data += "<div class=\"publication-row\">\n";
	        data += "	<div class=\"publication-id\">" + pub.id + "</div>\n";
	        data += "    <div class=\"publication-thumbnail\">\n";
	        data += "        <a href=\"" + pub.pdf + "\">\n";
	        data += "            <img src=\"" + pub.thumbnail + "\" class=\"img-responsive\"/>\n";
	        data += "        </a>\n";
	        data += "    </div>\n";
	        data += "    <div class=\"publication-info\">\n";
	        data += "    	<p class=\"publication-title\">" + addHighlight(pub.title) + "</p>\n";
	        data += "    	<p class=\"publication-authors\">\n";
	        pub.authors.forEach(function(author, index, array) {
	        	data += "    		<a href=\"" + author.link + "\">" + addHighlight(author.name) + "</a>";
	        	if(index + 1 < array.length) {
	        		data += ",&nbsp;";
	        	}
	        	data += "\n";
	    	});
	        data += "    	</p>\n";
	        data += "    	<p class=\"publication-venue\">\n";
	        data += "    		" + addHighlight(pub.venue) + "&nbsp;\n";
	        if(pub.award) {
	        	data += "    		| <span style=\"color:#c25059\">" + addHighlight(pub.award) + " <i class=\"fa fa-trophy\" aria-hidden=\"true\"></i></span>&nbsp;\n";
	    	}
	    	if(pub.total_papers_accepted && pub.total_papers_submitted) {
	    		data += "    		| <span style=\"font-style: bold\">Acceptance Rate: " + (pub.total_papers_accepted / pub.total_papers_submitted * 100).toFixed(0) + "% (" + pub.total_papers_accepted + " / " + pub.total_papers_submitted + ")</span>&nbsp;\n";
	    	}
	    	if(pub.to_appear) {
		        data += "    		| <span style=\"font-style: italic\">To Appear</span>&nbsp;\n";
		    }
	        data += "    	</p>\n";
	        if(pub.keywords.length > 0)
	        {
		        data += "    	<p class=\"publication-keywords\">\n";
		        data += "    	keywords:&nbsp;\n";
		        pub.keywords.forEach(function(keyword, index, array) {
			        data += "    		" + addHighlight(keyword.toLowerCase());
			        if(index + 1 < array.length) {
			        	data += ",&nbsp;";
			    	}
			        data += "\n";
			    });
			}
	        data += "    	</p>\n";
	        data += "    	<div class=\"publication-download\">Download: <a href=\"" + pub.pdf + "\">[pdf]</a> | Export <a data-toggle=\"popover\" data-html=\"true\" data-trigger=\"manual\" tabindex=\"0\" title=\"\Citation\" data-content=\"" + createCitationText(pub) + "\" style=\"cursor:pointer\">[Citation]</a></div>\n";
	        data += "    </div>\n";
	        data += "</div>\n";
		});
	});
	content.innerHTML = data;
	$('[data-toggle="popover"]').popover()

	// Manual trigger to get around idiosyncrasies of bootstrap's popover control
	$('[data-toggle="popover"]').click(function() {

		// prevent multiple popovers from being open at once
		var popovers = $('[data-toggle="popover"]')
		for(var i = 0; i < popovers.length; i++) {
			if(popovers[i] != this) // ignore the current popover
				$(popovers[i]).popover('hide');
		}

		// toggle this popover
		$(this).popover('toggle');
	});
}

// this function isn't called, but can be used to help debug
function showCitation(index) {
	var text = createCitationText(publications[index]);
	alert(text);
}

// combines and formats the citation metadata for display
function createCitationText(pub) {
	var text = "";
	
	// authors
	pub.authors.forEach(function(author, index, array) {
		text += author.last_name + ", " + author.first_name.substring(0,1) + ". ";
		if(author.middle_name && author.middle_name.length > 0)
			text += author.middle_name.substring(0,1) + ". ";
		text = text.substring(0, text.length-1) + ", "; // trim last space, add comma
	});
	if(text.length > 0) text = text.substring(0, text.length - 2); // trim last comma and space

	// year
	text += " (" + pub.date.getFullYear() + "). ";

	// title
	text += pub.title + ". ";

	// venue
	text += "<i>" + pub.venue + "</i>. "

	// pages
	if(pub.to_appear) {
		if(pub.num_pages) {
			text += pub.num_pages + " pages.";
		}
		text += " <i>To Appear</i>.";
	} else if(pub.start_page && pub.end_page) {
		text += pub.start_page + "&ndash;" + pub.end_page + ".";
	}

	return text;
}