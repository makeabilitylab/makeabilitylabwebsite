// Note: this code depends on a variable called "videos" that contains
// 		 all of the talks data in json format. It should be initialized in
//		 the Django template file.

// variables to hold the templates, since they will be removed from the DOM after initialization
var groupTemplate, videoTemplate;

var group_category_none_name = "Chronological List"

// initialization code that's called when the window has finished loading
$(window).load(function () {

	// preserve the template designs so that they're not lost when updating the display
	groupTemplate = $(".group-template").clone();
	videoTemplate = $(".video-template").clone();


	// initialize the filter bar module with the video data
	$('#fixed-side-bar').fixedSideBar();
	$('#filter-bar').filterBar({
		items: videos,
		categories: ["Year", "Project", "Talks", "None"],
		groupsForCategory: {
			"Year": groupVideosByYear(),
			"Project": groupVideosByProject(),
			"Talks": groupVideosByTalk(),
			"None": groupVideosByNone(),
		},
		defaultCategory: "None",
		passesFilter: passesFilter,
		displayGroupHeader: formatGroupHeader,
		displayItem: formatVideo,
	    afterDisplay: afterDisplay,
	    keywords: [] // empty list currently because videos don't currently have keyword associations
	});

	if(initialFilter && initialFilter.length > 0 && initialFilter != "None")
		$('#filter-textbox').val(initialFilter);
	$('#filter-bar').applyFilter();
});

// returns a list of videos in reverse chronological order (most recent video first)
function groupVideosByNone() {
	var tempGroup = {};
	tempGroup[group_category_none_name] = [];
	videos.forEach(function(video, index, array) {
		tempGroup[group_category_none_name].push(video);
	});
	tempGroup[group_category_none_name].sort(function(a, b) { return b.date - a.date });

	var groups = []
	groups.push({"name": group_category_none_name, "items": tempGroup[group_category_none_name]});

	return groups;
}

// returns a list of videos grouped by year, sorted with the most recent year first
// TODO: this is same function as in talks.js (and possibly publications.js). Consolidate?
function groupVideosByYear()
{
	var tempGroups = {};
	videos.forEach(function(video, index, array) {
		var group = video.date.getFullYear().toString();
		if(!(group in tempGroups)) {
			tempGroups[group] = [];
		}
		tempGroups[group].push(video);
	});

	return sortGroupsByDate(tempGroups);
}

// returns a list of videos grouped by project, sorted with the most frequent project first
// note: a video can appear in more than one group
// TODO: this is same function as in talks.js (and possibly publications.js). Consolidate? Actually, not the same because
// videos can only belong to one and only one group currently. If this switches to many-to-one, then we have to update this
// to be more like talks.js
function groupVideosByProject()
{
	// tempGroups holds all videos that are contained under the same project
	var tempGroups = {};
	videos.forEach(function(video, index, array) {
		group = video.project_short_name;
		//filter out the videos unaffiliated with projects
		if(video.project_short_name !== "") {
			if(!(group in tempGroups)) {
				tempGroups[group] = [];
			}
			tempGroups[group].push(video);
		}
	});
	return sortGroupsByDate(tempGroups);
}

function groupVideosByTalk()
{
	var tempGroups = {};
	videos.forEach(function(video, index, array) {
		group = video.talk;
		if(video.talk !== "") {
            if (!(group in tempGroups)) {
                tempGroups[group] = [];
            }
            tempGroups[group].push(video);
        }
	});
	return sortGroupsByDate(tempGroups);
}

//sorts groups by the date of the first item, sorts items inside each group by date in reverse chronological order (earliest first)
function sortGroupsByDate(unsortedGroups)
{
	var groups = []
	for(group in unsortedGroups) {
		//sort all the items in each group in reverse chronological order
		unsortedGroups[group].sort(function(a, b) { return b.date - a.date});
		groups.push({"name": group, "items": unsortedGroups[group]});
	}

	// groupings are sorted by the date of the most recent item in the group
	groups.sort(function(a,b) { return b.items[0].date - a.items[0].date });
	return groups;
}


// returns true if the publication contains the text entered into the filter box anywhere
// in the title, speakers, venue, keywords, or projects
function passesFilter(video, filter) {
	filter = filter.toLowerCase();
	var passes = false;

	if(!filter || filter.length == 0) passes = true;

	if(video.title.toLowerCase().indexOf(filter) >= 0) passes = true;
	if(video.caption.toLowerCase().indexOf(filter) >= 0) passes = true;
	if(video.project_short_name.toLowerCase().indexOf(filter) >= 0) passes = true;

	return passes;
}

// adds html markup to the specified text wherever it matches the filter, applying the highlight style
// TODO: this is same function as in talks.js (and possibly publications.js). Consolidate?
function addHighlight(text, filter) {
	var result = text;
	if(filter && filter.length > 0)
		result = text.replace(new RegExp('(' + filter + ')', 'gi'), "<span class=\"highlight\">$1</span>");
	return result;
}

// helper function to populate the template with the group data
// TODO: this is same function as in talks.js (and possibly publications.js). Consolidate?
function formatGroupHeader(group) {
	var groupData = groupTemplate.clone();

	if (group == group_category_none_name){
		// hide the heading and bottom border for when none is selected as a grouping category
		groupData.css("border-bottom", "none");
		groupData.css("margin-bottom", "11px");
	}
	else {
        groupData.attr("name", group.toLowerCase().replace(new RegExp(" ", "g"), "-"));
        groupData.html(group);
    }

	return groupData[0].outerHTML;
}

function formatVideo(video, filter){
	if(filter) filter = filter.toLowerCase();

	var videoData = videoTemplate.clone();
	videoData.find(".artifact-title").html(addHighlight(video.title, filter));
	videoData.find(".artifact-venue").html(addHighlight(video.caption, filter));
	videoData.find(".video").attr("src", video.url_embeddable);
	videoData.find(".video-link").attr("href", video.url);

	if(video.url){
		videoData.find(".video-link").attr("href", video.url);
	}
	else{
		videoData.find(".video-link").remove();
		videoData.find(".decor_video").remove();
	}

	if(video.pub_url){
		videoData.find(".video-paper-link").attr("href", video.pub_url);
	}
	else{
		videoData.find(".video-paper-link").remove();
		videoData.find(".decor_pdf").remove();
	}

	return videoData[0].outerHTML;
}

// called after initialization or whenever the filter is reapplied
function afterDisplay() {
	// Empty for now
}

//Code to use isotope for filtering from http://codepen.io/desandro/pen/wfaGu
// TODO: All of this directly copy/pasted from talks.js. Lots of redundancy here. Could be refactored
// TODO: is this code even necessary? I don't think so...

// init Isotope
var $grid = $('.video-list').isotope({
  itemSelector: '.video-template',
  layoutMode: 'fitRows',
  filter: function() {
    return qsRegex ? $(this).text().match( qsRegex ) : true;
  }
});


// use value of search field to filter
var $quicksearch = $('#filter-textbox').keyup( debounce( function() {
  qsRegex = new RegExp( $quicksearch.val(), 'gi' );
  $grid.isotope();
}, 200 ) );

// debounce so filtering doesn't happen every millisecond
function debounce( fn, threshold ) {
  var timeout;
  return function debounced() {
    if ( timeout ) {
      clearTimeout( timeout );
    }
    function delayed() {
      fn();
      timeout = null;
    }
    timeout = setTimeout( delayed, threshold || 100 );
  }
}

$(window).resize(debounce(function() {
	// hack to force the ellipsis to redraw, so that it's in the correct position
	$.each($('.line-clamp'), function(index, item) {
		$(item).hide().show(0);
	});
}));