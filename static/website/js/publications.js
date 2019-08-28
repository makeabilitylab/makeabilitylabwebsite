// Note: this code depends on a variable called "publications" that contains
// 		 all of the publication data in json format. It should be initialized in
//		 the Django template file.

// variables to hold the templates, since they will be removed from the DOM after initialization
var groupTemplate, publicationTemplate;

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
	"Doctoral Consortium": "DC",
    "Work in Progress": "WiP",
    "Late Breaking Result": "LBR",
    "Other": "O"
};

// initialization code that's called when the window has finished loading
$(window).load(function () {

	// preserve the template designs so that they're not lost when updating the display
	groupTemplate = $(".group-template").clone();
	publicationTemplate = $(".publication-template").clone();

	// initialize the filter bar module with the publication data
	preprocessPublications();
	$('#fixed-side-bar').fixedSideBar();
	$('#fixed-side-bar').fixedSideBar('#main-content');
	$('#filter-bar').filterBar({
		items: publications, 
		categories: ["Year", "Pub Type", "Project", "None"],
		groupsForCategory: {
			"Year": groupPublicationsByYear(),
			"Pub Type": groupPublicationsByType(),
			"Project": groupPublicationsByProject(),
			"None": [{"name": "Chronological List", items: publications}]
		},
		passesFilter: passesFilter,
		displayGroupHeader: formatGroup,
		displayItem: formatPublication,
	        afterDisplay: afterDisplay,
	    keywords: getAllKeywords()
	});
	
});

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

// returns a list of publications grouped by year, sorted with the most recent year first
function groupPublicationsByYear()
{
	var tempGroups = {};
	publications.forEach(function(pub, index, array) {
		var group = pub.date.getFullYear().toString();
		if(!(group in tempGroups)) {
			tempGroups[group] = [];
		}
		tempGroups[group].push(pub);
	});

	var groups = []
	for(group in tempGroups) {
		groups.push({"name": group, "items": tempGroups[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	groups.sort(function(a,b) { return parseInt(b.name) - parseInt(a.name) });

	return groups;
}

// returns a list of publications grouped by publication venue type, sorted with the most frequent type first
function groupPublicationsByType()
{
	var tempGroups = {};
	publications.forEach(function(pub, index, array) {
		var group = pub.pub_type;
		if(!(group in tempGroups)) {
			tempGroups[group] = [];
		}
		tempGroups[group].push(pub);
	});

	var groups = []
	for(group in tempGroups) {
		groups.push({"name": group, "items": tempGroups[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	groups.sort(function(a,b) { return b.items.length - a.items.length });

	return groups;
}

function getAllKeywords()
{
    var keywords=[];
    publications.forEach(function(pub, index, array){
	pub.keywords.forEach(function(keyword, index, array){
	    keywords.push(keyword);
	});
    });
    keywords = uniq(keywords);
    return keywords;
}

// Comes from here http://stackoverflow.com/questions/9229645/remove-duplicates-from-javascript-array
function uniq(a) {
    return a.sort().filter(function(item, pos, ary) {
        return !pos || item != ary[pos - 1];
    })
}

// returns a list of publications grouped by keyword, sorted with the most frequent keyword first
// note: a publication can appear in more than one group
function groupPublicationsByKeyword()
{
	var tempGroups = {};
	publications.forEach(function(pub, index, array) {
		var keywordGroups = pub.keywords;
		keywordGroups.forEach(function(group, index, array) {
			if(!(group in tempGroups)) {
				tempGroups[group] = [];
			}
			tempGroups[group].push(pub);
		});
	});

	var groups = []
	for(group in tempGroups) {
		groups.push({"name": group, "items": tempGroups[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	groups.sort(function(a,b) { return b.items.length - a.items.length });

	return groups;
}

// returns a list of publications grouped by project, sorted with the most frequent project first
// note: a publication can appear in more than one group
function groupPublicationsByProject()
{
	var tempGroups = {};
	publications.forEach(function(pub, index, array) {
		var projectGroups = pub.projects;
		projectGroups.forEach(function(group, index, array) {
			if(!(group in tempGroups)) {
				tempGroups[group] = [];
			}
			tempGroups[group].push(pub);
		});
	});

	var groups = []
	for(group in tempGroups) {
		groups.push({"name": group, "items": tempGroups[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	groups.sort(function(a,b) { return b.items.length - a.items.length });

	return groups;
}

// returns true if the publication contains the text entered into the filter box anywhere
// in the title, authors, venue, keywords, or projects
function passesFilter(pub, filter) {
	filter = filter.toLowerCase();
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

// adds html markup to the specified text wherever it matches the filter, applying the highlight style
function addHighlight(text, filter) {
	var result = text;
	if(filter && filter.length > 0)
		result = text.replace(new RegExp('(' + filter + ')', 'gi'), "<span class=\"highlight\">$1</span>");
	return result;
}


// helper function to populate the template with the group data
function formatGroup(group) {
	var groupData = groupTemplate.clone();
	groupData.attr("name", group);
	groupData.html(group);
	return groupData[0].outerHTML;
}

// helper function to populate the template with the publication data
function formatPublication(pub, filter) {
	if(filter) filter = filter.toLowerCase();
    console.log("Formatting pub "+pub.title);
	var publicationData = publicationTemplate.clone();
	publicationData.find(".publication-id").html(pub.id);
	publicationData.find(".publication-thumbnail-link").attr("href", pub.pdf);
	publicationData.find(".publication-thumbnail-image").attr("src", pub.thumbnail);
	publicationData.find(".publication-title-link").attr("href", pub.pdf);
	publicationData.find(".artifact-title").html(addHighlight(pub.title));

	var authors = publicationData.find(".publication-authors");
	var authorTemplate = authors.find(".publication-author");
	var authorLastTemplate = authors.find(".publication-author-last");
	authors.html("");
	pub.authors.forEach(function(author, index, array) {
		var authorData = index + 1 < array.length ? authorTemplate.clone() : authorLastTemplate.clone();
		authorData.find("a").attr("href", author.link);
		authorData.find("a").html(addHighlight(author.name, filter));
		authors.append(authorData);
	});


	var pubVenue = pub.venue;
	if(pub.extended_abstract === true){
		if(pubVenue.toLowerCase().indexOf("extended") < 0){
			pubVenue = "Extended Abstract " + pubVenue;
		}
	}

	publicationData.find(".publication-venue").html(addHighlight(pubVenue, filter));

    if (pub.award) {
        console.log(pub.title);
        var award_icon;
        console.log(pub.award);
        if (pub.award == "Best Paper Award") {
            award_icon = pub.best_paper;
        } else {
            award_icon = pub.honorable_mention;
        }

        publicationData.find(".publication-id").append("<img src=\"" + award_icon + "\" align=\"center\" class=\"award-icon\"/>");
        publicationData.find(".publication-thumbnail-link").append("<img src=\"" + pub.award_banner + "\" class=\"publication-award-banner\"/>");
        publicationData.find(".publication-award-text").html(addHighlight(pub.award, filter));
    } else {
        publicationData.find(".publication-award").css("display", "none");
    }
    
    if(pub.total_papers_accepted && pub.total_papers_submitted) {
    	publicationData.find(".publication-acceptance-rate-text").html("Acceptance Rate: " + (pub.total_papers_accepted / pub.total_papers_submitted * 100).toFixed(0) + "% (" + pub.total_papers_accepted + " / " + pub.total_papers_submitted + ")");
	} else {
		publicationData.find(".publication-acceptance-rate").css("display", "none");
	}

	if(pub.to_appear == true) {
        publicationData.find(".publication-to-appear-text").css("display", "inline");
    } else {
    	publicationData.find(".publication-to-appear-text").css("display", "none");
    }

    if(pub.keywords.length > 0)
    {
    	var keywords = publicationData.find(".publication-keywords");
		var keywordTemplate = keywords.find(".publication-keyword");
		var keywordLastTemplate = keywords.find(".publication-keyword-last");
		keywords.html("");	
        pub.keywords.forEach(function(keyword, index, array) {
        	var keywordData = index + 1 < array.length ? keywordTemplate.clone() : keywordLastTemplate.clone();
			keywordData.find(".publication-keyword-text").html(addHighlight(keyword.toLowerCase(), filter));
			keywords.append(keywordData);
	    });
	} else {
		publicationData.find(".publication-keywords").css("display", "none");
	}

    publicationData.find(".publication-download-link").attr("href", pub.pdf);
    if (pub.video_url) {
        publicationData.find(".publication-video-link").attr("href", pub.video_url);
    } else {
        publicationData.find(".publication-video-link-label").css("display", "none");
    }
    // publicationData.find(".publication-citation-link").attr("data-content", createCitationText(pub));
    publicationData.find(".publication-citation-link").citationPopover(pub);
    
    if (pub.url != 'None') {
   		publicationData.find(".publication-doi-link").attr("href", pub.url);
    } else {
    	publicationData.find(".publication-doi-link-label").css("display", "none");
    }

	return publicationData[0].outerHTML;
}

// called after initialization or whenever the filter is reapplied
function afterDisplay() {
	$('[data-toggle="popover"]').updateCitationPopover();
}