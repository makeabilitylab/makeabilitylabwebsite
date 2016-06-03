// Note: this code depends on a variable called "talks" that contains
// 		 all of the talks data in json format. It should be initialized in
//		 the Django template file.

// variables to hold the templates, since they will be removed from the DOM after initialization
var groupTemplate, talkTemplate;

// dictionary for abbreviated talk types
// TODO: this should probably go in the model instead of here
var talkTypeCodes = {
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

	// preserve the template designs so that they're not lost when updating the display
	groupTemplate = $(".group-template").clone();
	talkTemplate = $(".talk-template").clone();

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

	// initialize the filter bar module with the talk data
	preprocessTalks();
	$('#fixed-side-bar').fixedSideBar();
	$('#filter-bar').filterBar({
		items: talks, 
		categories: ["Year", "Keyword", "Project", "None"],
		groupsForCategory: {
			"Year": groupTalksByYear(),
			"Keyword": groupTalksByKeyword(),
			"Project": groupTalksByProject(),
			"None": [{"name": "Chronological List", items: talks}]
		},
		passesFilter: passesFilter,
		displayGroupHeader: formatGroup,
		displayItem: formatTalk,
		afterDisplay: afterDisplay
	});
	$('#filter-bar').applyFilter();
});

// run some additional processing on the talks
function preprocessTalks() {
	var talkTypeCount = {};

	// sort by date
	talks.sort(function(a, b) {
		return a.date - b.date;
	});

	// group into talk types, initialize talk ids (e.g., C.1 for first conference paper)
	talks.forEach(function(talk, index, array) {
		if(!(talk.talk_type in talkTypeCount)) {
			talkTypeCount[talk.talk_type] = 1;
		} else {
			talkTypeCount[talk.talk_type]++;
		}

		talk.id = "[" + talkTypeCodes[talk.talk_type] + "." + talkTypeCount[talk.talk_type] + "]";
	});
	talks.reverse(); // most recent first

	// connect the array index to the dictionary objects for reverse lookup
	talks.forEach(function(talk, index, array) {
		talk["index"] = index;
	});
}

// returns a list of talks grouped by year, sorted with the most recent year first
function groupTalksByYear()
{
	var tempGroups = {};
	talks.forEach(function(talk, index, array) {
		var group = talk.date.getFullYear().toString();
		if(!(group in tempGroups)) {
			tempGroups[group] = [];
		}
		tempGroups[group].push(talk);
	});

	var groups = []
	for(group in tempGroups) {
		groups.push({"name": group, "items": tempGroups[group]});
	}

	// years are sorted chronologically, all of the other groupings are sorted by frequency
	groups.sort(function(a,b) { return parseInt(b.name) - parseInt(a.name) });

	return groups;
}

// returns a list of talks grouped by keyword, sorted with the most frequent keyword first
// note: a talk can appear in more than one group
function groupTalksByKeyword()
{
	var tempGroups = {};
	talks.forEach(function(talk, index, array) {
		var keywordGroups = talk.keywords;
		keywordGroups.forEach(function(group, index, array) {
			if(!(group in tempGroups)) {
				tempGroups[group] = [];
			}
			tempGroups[group].push(talk);
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

// returns a list of talks grouped by project, sorted with the most frequent project first
// note: a talk can appear in more than one group
function groupTalksByProject()
{
	var tempGroups = {};
	talks.forEach(function(talk, index, array) {
		var projectGroups = talk.projects;
		projectGroups.forEach(function(group, index, array) {
			if(!(group in tempGroups)) {
				tempGroups[group] = [];
			}
			tempGroups[group].push(talk);
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
// in the title, speakers, venue, keywords, or projects
function passesFilter(talk, filter) {
	filter = filter.toLowerCase();
	var passes = false;
	if(!filter || filter.length == 0) passes = true;

	if(talk.title.toLowerCase().indexOf(filter) >= 0) passes = true;
	talk.speakers.forEach(function(speaker, index, array) { 
		if(speaker.name.toLowerCase().indexOf(filter) >= 0) passes = true; 
	});
	talk.keywords.forEach(function(keyword, index, array) { if(keyword.toLowerCase().indexOf(filter) >= 0) passes = true; });
	talk.projects.forEach(function(project, index, array) { if(project.toLowerCase().indexOf(filter) >= 0) passes = true; });

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

// helper function to populate the template with the talk data
function formatTalk(talk, filter) {
	if(filter) filter = filter.toLowerCase();

	var talkData = talkTemplate.clone();
	talkData.find(".talk-id").html(talk.id);
	talkData.find(".talk-thumbnail-link").attr("href", talk.pdf);
	talkData.find(".talk-thumbnail-image").attr("src", talk.thumbnail);
	talkData.find(".talk-title").html(addHighlight(talk.title));
	
	//Insert links if available
	if (talk.pdf != "") {
		talkData.find(".talk-pdf-link").attr("href", "../../media/" + talk.pdf);
	} else {
		talkData.find(".talk-pdf-link").remove();
		talkData.find(".decor_pdf").remove();
	}
	
	if (talk.pptx != "") {
		talkData.find(".talk-pptx-link").attr("href", "../../media/" + talk.pptx);
	} else {
		talkData.find(".talk-pptx-link").remove();
		talkData.find(".decor_pptx").remove();
	}
	
	if (talk.slideshare != "") {
		talkData.find(".talk-slideshare-link").attr("href", talk.slideshare);
	} else {
		talkData.find(".talk-slideshare-link").remove();
		talkData.find(".decor_slideshare").remove();
	}
	
	if (talk.video != "") {
		talkData.find(".talk-video-link").attr("href", talk.video);
	} else {
		talkData.find(".talk-video-link").remove();
	}
	
	
	//Human Readable Date
	//TODO: Easier way to do this?
	var monthNames = ["January", "February", "March", "April", "May", "June",
  						"July", "August", "September", "October", "November", "December"
						];
						
	var dd = talk.date.getDate()+1;
	var mm = monthNames[talk.date.getMonth()];
	var yy = talk.date.getFullYear();
	var showDate = mm + " " + dd + ", " + yy;
	talkData.find(".talk-date").html(addHighlight(showDate));
	
	//Location Data
	talkData.find(".talk-location").html(addHighlight(talk.location));

	var speakers = talkData.find(".talk-speakers");
	var speakerTemplate = speakers.find(".talk-speaker");
	var speakerLastTemplate = speakers.find(".talk-speaker-last");
	speakers.html("");
	talk.speakers.forEach(function(speaker, index, array) {
		var speakerData = index + 1 < array.length ? speakerTemplate.clone() : speakerLastTemplate.clone();
		speakerData.find("a").attr("href", speaker.link);
		speakerData.find("a").html(addHighlight(speaker.name, filter));
		speakers.append(speakerData);
	});

	talkData.find(".talk-venue").html(addHighlight(talk.location, filter));

	if(talk.award) { 
		talkData.find(".talk-award-text").html(addHighlight(talk.award, filter));
	} else {
		talkData.find(".talk-award").css("display", "none");
	}

    if(talk.total_papers_accepted && talk.total_papers_submitted) {
    	talkData.find(".publication-acceptance-rate-text").html("Acceptance Rate: " + (talk.total_papers_accepted / talk.total_papers_submitted * 100).toFixed(0) + "% (" + talk.total_papers_accepted + " / " + talk.total_papers_submitted + ")");
	} else {
		talkData.find(".talk-acceptance-rate").css("display", "none");
	}

	if(talk.to_appear) {
        talkData.find(".talk-to-appear").css("display", "block");
    } else {
    	talkData.find(".talk-to-appear").css("display", "none");
    }

    if(talk.keywords.length > 0)
    {
    	var keywords = talkData.find(".talk-keywords");
		var keywordTemplate = keywords.find(".talk-keyword");
		var keywordLastTemplate = keywords.find(".talk-keyword-last");
		keywords.html("");	
        talk.keywords.forEach(function(keyword, index, array) {
        	var keywordData = index + 1 < array.length ? keywordTemplate.clone() : keywordLastTemplate.clone();
			keywordData.find(".publication-keyword-text").html(addHighlight(keyword.toLowerCase(), filter));
			keywords.append(keywordData);
	    });
	} else {
		talkData.find(".talk-keywords").css("display", "none");
	}

	talkData.find(".talk-download-link").attr("href", talk.pdf);

	return talkData[0].outerHTML;
}

// called after initialization or whenever the filter is reapplied
function afterDisplay() {
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