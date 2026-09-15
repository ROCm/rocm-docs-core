const RTD_SEARCH_SHOW_EVENT = "readthedocs-search-show";
const RTD_SEARCH_HIDE_EVENT = "readthedocs-search-hide";
const SEARCH_FIELD_QUERY = ".search-button-field.search-button__button";

let _rtdSearchOpen = false;

document.addEventListener(RTD_SEARCH_SHOW_EVENT, () => { _rtdSearchOpen = true; });
document.addEventListener(RTD_SEARCH_HIDE_EVENT, () => { _rtdSearchOpen = false; });

function toggleRtdSearch() {
    document.dispatchEvent(
        new CustomEvent(_rtdSearchOpen ? RTD_SEARCH_HIDE_EVENT : RTD_SEARCH_EVENT_EVENT)
    );
}

const searchField = document.querySelector(SEARCH_FIELD_QUERY);
if (searchField) {
    searchField.addEventListener("focusin", () => {
        document.dispatchEvent(new CustomEvent(RTD_SEARCH_SHOW_EVENT));
    });
}

document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        toggleRtdSearch();
    }
});
