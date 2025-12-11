// Define which projects should be hidden from search in other projects
const hiddenProjects = ['amd-rocm-programming-guide-internal', 'amd-rocm-programming-guide'];

// Get the current project slug from the page
function getCurrentProject() {
    // Read the Docs typically stores this in the page's data attributes or meta tags
    // Option 1: From meta tag
    const metaProject = document.querySelector('meta[name="readthedocs-project-slug"]');
    if (metaProject) {
        return metaProject.getAttribute('content');
    }
    
    // Option 2: From window.READTHEDOCS_DATA if available
    if (window.READTHEDOCS_DATA && window.READTHEDOCS_DATA.project) {
        return window.READTHEDOCS_DATA.project;
    }
    
    // Option 3: Parse from URL (adjust pattern as needed)
    const match = window.location.hostname.match(/^([^.]+)/);
    return match ? match[1] : null;
}

// Filter search results based on current project
document.addEventListener('readthedocs-search-results', (event) => {
    const currentProject = getCurrentProject();
    
    if (event.detail && event.detail.results && currentProject) {
        event.detail.results = event.detail.results.filter(result => {
            // If we're on a hidden project, show ONLY results from that project
            if (hiddenProjects.includes(currentProject)) {
                return result.project === currentProject;
            }
            
            // If we're on any other project, hide all hidden project results
            return !hiddenProjects.includes(result.project);
        });
    }
});

// Your existing trigger code
document.querySelector(".search-button-field.search-button__button")
    .addEventListener("focusin", () => {
        const event = new CustomEvent("readthedocs-search-show");
        document.dispatchEvent(event);
    });