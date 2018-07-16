# Isotope Implementation
This is a collection of scripts that implement sorting, filtering, sidebars, and headers for Isotope.

# Rquired Scripts
For this implementation, these scripts must be included in the HTML:
1. isotope.pkgd.min.js
2. isotope-init.js

This implementation is dependant on isotope, which is why ```isotope.pkgd.min.js``` is required. The ```isotope-init.js``` sets up important JS variables and sets up the isotope grid.

# General HTML requirements
- There must be a div with the id "isotope_data_container" in the HTML page. In this, you must put all relevant configuration data. 
(See isotope-init.js for all the data that needs to be inserted here). 
Data must be in the form ```<Property>(<value>,<valueType>)``` where ```<valueType>``` can be "str", "int", or "float".
Multiple properties can be inserted in this fashion, e.g.
    ```
    <div id="isotope_data_container">
        sortFilterContainer(.sortingAndFiltering,str)
        gridName(.grid,str)
        headerClass(h1,str)
        headerStyle(margin: 0; background: white;,str)
        filteringKeywordContainer(#keywords-all,str)
        sortingKeywordContainer(#keywords-sorting,str)
        sideBarContainer(#fixed-side-bar,str)
        scrollTop(175,int)
    </div>
    ```
    These properties are used by ```isotope.init.js``` to configure settings 
    (for example, gridName(.grid,str) tells ```isotope.init.js``` that the container for 
    all our items to be sorted is named ```.grid```)
    The properties required are dependant on what isotope scripts are being used.
    For example, if the ```isotope-header-creator.js``` is being used, then headerClass and headerStyle are required.
    ```isotope.init.js``` will throw errors if it cannot find the properties required.

# Requirements for item container and items to be sorted/filtered
- Set the container for the items to be filtered using 
```gridName(<container-class-name>,str)``` in the ```isotope_data_container```
- Everything inside the grid class must be class 'item'
-Inside each item there must be at minimum two divs:
   - one for containing the sort-filter data (sortFilterContainer)
     - set this property using ```sortFilterContainer(<container-class-name>,str)``` in the ```isotope_data_container```
     - set the text of the sortFilterContainer to a series of ```<Property>(<value>,<valueType>)``` or ```<Property>()```.
       Use Django to fill in data, or do it manually. 
       For a specific item the data should look something like this: 
       ```Year(2018,int)Project(Sidewalk,str)Accessibility()```
        - Note that Properties with empty braces and no data cannot be sorted, only filtered.
   - one for containing the date (which is assumed to be .Date)
     - set the text of Date to a number concatenating the year, month, and then day. For example, 7/16/2018 becomes 2018716.
   - If you do not wish this data to be seen, set their styles to display:none.

# Requirements for the filterBar
- Set the container for the filterBar using
```sideBarContainer(<container-class-name>,str)```
- Inside this container, keep the filteringKeywordContainer and sortingKeywordContainer. 
If sorting and filtering have the same keywords, then put the sorting div inside the filtering div. 
Do not set the filteringKeywordContainer and sortingKeywordContainer to the same div.

- for the ```<a></a>``` inside the sortingKeywordContainer, sorting expects there to be a sorting-order attribute.
This tells the sorting which direction to sort in (ascending or descending). True is ascending, false is descending.