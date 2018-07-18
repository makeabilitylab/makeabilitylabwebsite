//some function to find .page-number class and add in numbers

var keywords = ['1','2', '3','4'];
var actions = ['Newer', 'Older'];
var grid;
var num_items_per_page = 3;
$(window).load(function () {





    var page = 0;
    var index = 0;
    $(".grid .page-number").each(function () {

        if (index%num_items_per_page === 0){
            page++;
        }
        $(this).attr('class', page);
        index++;
    });
    
    for (i=0; i<page; i++){
        $('.pagination').append('<li>' + (i+1) +  '</li>');
    }
    
    $('#keywords ul li').each(function(){
        keywords.push($(this).text());
    });


    $grid = $('.grid').isotope({
        filter:'.1'
    });

    $('#keywords ul li').on('click', function (e) {
        handleClick(e);

    });
});


function handleClick(e)
{
    if(isKeyword(e))
    {
        var filter = getFilter($(e.target).text());
        console.log(filter);
        $grid.isotope({ filter: filter});
    }
    else
    {
        $grid.isotope({ filter: '*'});
    }
}

function isAction(e){
    if ($(e.target) && $(e.target).text()){
        for (var i=0; i<actions.length; i++){
            if ($(e.target).text() === actions[i]){
              return true;
            }
        }
    }
    return false;
}

function getFilter(keyword)
{
    return "." + keyword.replace(" ", "-").replace("/", "-");
}

function isKeyword(e)
{
    if($(e.target) && $(e.target).text())
    {
        for (var i = 0; i < keywords.length; i++)
        {
            if($(e.target).text() === keywords[i])
            {
                return true;
            }
        }
    }
    return false;
}
