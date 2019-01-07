// Reusable citation popover module
//
// usage: $(citationLink).citationPopover(pub)
//		pub: an object containing the publication data
(function ($) {

	$.fn.citationPopover = function (pub) {

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

		$(this).attr("data-content", createCitationText(pub));

		$(this).updateCitationPopover();

		return this;
	}

	// combines and formats the citation metadata for display
	function createCitationText(pub) {
		var text = "<div class=\"citation-links\"><a id=\"citation-link\" onclick=\"$(this).citationclick()\">Citation</a> | <a id=\"bibtex-link\" onclick=\"$(this).bibtexclick()\" >Bibtex</a></div><br/>";
	    // authors
	    text+="<div id=\"citation-text\">";
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
	    text+="</div>";
	    text+="<div id=\"bibtex-text\" style=\"display: none\">";
	    text+="@inproceedings{"+pub.authors[0].last_name;
	    if (pub.series && pub.series!="None") {
	    	text+=pub.series.split(" ")[0];
		}
	    text+=",<br/>";
	    text+=" author = {";
	    pub.authors.forEach(function(author, index, array){
			text+=author.last_name+", "+author.first_name;
			if (author.middle_name) {
				text+=" "+author.middle_name;
			}
			if (index != array.length-1){
				text+=" and ";
			}
	    });
	    text+="},<br/>";
	    text+=" title = {"+pub.title+"},<br/>";
	    if(pub.book_title && pub.book_title!="None"){
		text+=" book_title = {"+pub.book_title+"},<br/>";
	    }
	    text+=" book_title_short = {"+pub.venue+"},<br/>";
	    if(pub.series && pub.series!="None"){
		text+=" series = {"+pub.series+"},<br/>"; //Is this what series is?
	    }
	    text+=" year = {"+pub.date.getFullYear()+"},<br/>";
	    if (pub.isbn && pub.isbn!="None" && pub.isbn!="tbd") {
		text+=" isbn = {"+pub.isbn+"},<br/>";
	    }
	    if (pub.geo_location && pub.geo_location!="None") {
		text+=" location = {"+pub.geo_location+"},<br/>";
	    }
	    if (pub.page_num_start && pub.page_num_start!="None") {
		text+=" pages = {"+pub.page_num_start+"--"+pub.page_num_end+"},<br/>";
		text+=" numpages = {"+String(parseInt(pub.page_num_end)-parseInt(pub.page_num_start))+"},<br/>";
	    }
	    if (pub.url && pub.url!="None" && pub.url!="tbd"){
		text+=" url = {"+pub.url+"},<br/>";
	    }
	    if (pub.doi && pub.doi!="None" && pub.doi!="tbd"){
		text+=" doi = {"+pub.doi+"},<br/>";
	    }
	    if (pub.acmid && pub.acmid!="None" && pub.acmid!="tbd"){
		text+=" acmid = {"+pub.acmid+"},<br/>";
	    }
	    if (pub.publisher && pub.publisher!="None"){
		text+=" publisher = {"+pub.publisher+"},<br/>";
		text+=" publisher_address = {"+pub.publisher_address+"},<br/>";
	    }
	    if (pub.award && pub.award!="None"){
		text+=" award = {"+pub.award+"},<br/>";
	    }
	    if (pub.total_papers_accepted && pub.total_papers_accepted!="None") {
		text+=" total_papers_submitted = {"+pub.total_papers_submitted+"},<br/>";
		text+=" total_papers_accepted = {"+pub.total_papers_accepted+"},<br/>";
	    }
	    if (pub.video_url && pub.video_url!="None"){
		text+=" video_url = {"+pub.video_url+"},<br/>";
	    }
	    text+=" keywords = {";
	    pub.keywords.forEach(function(keyword, index, array){
		text+=keyword;
		if (index != array.length-1) {
		    text+=", "; 
		}
	    });
	    text+="}<br/>}"
	    text+="</div>";

		return text;
	}

	$.fn.citationclick = function() {
		$("#citation-text").css('display', 'block');
		$("#bibtex-text").css('display', 'none');
	}

	$.fn.bibtexclick = function() {
		$("#bibtex-text").css('display', 'block');
		$("#citation-text").css('display', 'none');
	}

	$.fn.updateCitationPopover = function() {
		$(this).popover({placement: "auto right"})

		// Manual trigger to get around idiosyncrasies of bootstrap's popover control
		$(this).click(function() {

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

}(jQuery));