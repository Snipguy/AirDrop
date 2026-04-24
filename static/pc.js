const filesData = JSON.parse(JSON.stringify(files_data | tojson | safe )); // Clone initial data
let currentFiles = [...filesData]; // The list that will be manipulated
let sortBy = 'name'; // Default sort
let sortOrder = 'asc'; // Default order
let isSortMenuOpen = false;

// --- DOM Elements ---
const fileListContainer = document.getElementById('fileListContainer');
const searchInput = document.getElementById('searchInput');
const sortButton = document.getElementById('sortButton');
const sortMenu = document.getElementById('sortMenu');
const loadingOverlay = document.getElementById('loadingOverlay');
const ptrIndicator = document.getElementById('ptrIndicator');

// --- Helper Functions ---
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// *** getFileIcon FUNCTION ***
function getFileIcon(fileType, extension) {
    // Use fileType first, then fallback to extension for more specific icons
    switch(fileType) {
        case 'pdf': return '<i class="fas fa-file-pdf"></i>';
        case 'image': return '<i class="fas fa-image"></i>';
        case 'archive': return '<i class="fas fa-file-archive"></i>';
        case 'audio': return '<i class="fas fa-music"></i>';
        case 'video': return '<i class="fas fa-film"></i>';
        case 'document': return '<i class="fas fa-file-alt"></i>';
        case 'text': return '<i class="fas fa-file-text"></i>'; // Example for .txt
        default:
            if (extension === '.txt') return '<i class="fas fa-file-text"></i>';
            if (extension === '.js' || extension === '.html' || extension === '.css' || extension === '.py' || extension === '.go') return '<i class="fas fa-code"></i>';
            return '<i class="fas fa-file"></i>';
    }
}

function getSortDirectionIcon(type, order) {
    if (type === 'name') {
        return order === 'asc' ? '<i class="fas fa-sort-alpha-down"></i>' : '<i class="fas fa-sort-alpha-up"></i>';
    } else { // size, date
        return order === 'asc' ? '<i class="fas fa-sort-numeric-down"></i>' : '<i class="fas fa-sort-numeric-up"></i>';
    }
}

// --- Rendering Function ---
function renderFileList(filesToRender) {
    fileListContainer.innerHTML = ''; // Clear current list

    if (filesToRender.length === 0) {
        fileListContainer.innerHTML = '<p class="empty">No files found matching your search.</p>';
        return;
    }

    filesToRender.forEach(file => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        // Use 'data-' attributes to store info for potential future multi-select
        fileItem.dataset.filename = file.name;
        fileItem.dataset.type = file.type;

        const fileSizeFormatted = formatBytes(file.size_bytes);
        const fileIconHTML = getFileIcon(file.type, file.extension);


        fileItem.innerHTML = `
            <div class="file-info">
                <span class="file-icon">${fileIconHTML}</span>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-meta">
                        <span class="size">${fileSizeFormatted}</span>
                        <span class="date">${file.modified_date}</span>
                    </div>
                </div>
            </div>
            <button class="preview-btn" onclick="previewFile('/uploads/${file.name}')">Preview</button>
            <a class="download-btn" href="/api/download/${encodeURIComponent(file.name)}" download>
                <i class="fa fa-download"></i>
            </a>
        `;
        fileListContainer.appendChild(fileItem);
    });
}

// --- Sorting Function ---
function sortFiles(files, criteria, order) {
    const reverse = order === 'desc';
    let sorted = [...files]; // Work on a copy

    switch (criteria) {
        case 'size':
            sorted.sort((a, b) => (reverse ? b.size_bytes - a.size_bytes : a.size_bytes - b.size_bytes));
            break;
        case 'date':
            sorted.sort((a, b) => (reverse ? b.modified_timestamp - a.modified_timestamp : a.modified_timestamp - b.modified_timestamp));
            break;
        case 'name':
        default:
            sorted.sort((a, b) => {
                1
                const nameA = a.name.toLowerCase();
                const nameB = b.name.toLowerCase();
                if (nameA < nameB) return reverse ? 1 : -1;
                if (nameA > nameB) return reverse ? -1 : 1;
                return 0;
            });
            break;
    }
    return sorted;
}

// --- Filtering (Search) Function ---
function filterFiles(files, searchTerm) {
    if (!searchTerm) return files;
    const lowerSearch = searchTerm.toLowerCase();
    return files.filter(file => file.name.toLowerCase().includes(lowerSearch));
}

// --- Update Display ---
function updateDisplay() {
    let filtered = filterFiles(filesData, searchInput.value);
    currentFiles = sortFiles(filtered, sortBy, sortOrder);
    renderFileList(currentFiles);
}

// --- Event Listeners ---

// Search Input
searchInput.addEventListener('input', () => {
    updateDisplay();
});

// Sort Button & Menu
sortButton.addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent click from closing menu immediately
    isSortMenuOpen = !isSortMenuOpen;
    sortMenu.classList.toggle('show', isSortMenuOpen);
    if (isSortMenuOpen) {
        sortButton.querySelector('.fa-sort').style.color = '#00bcd4'; // Highlight button
    } else {
        sortButton.querySelector('.fa-sort').style.color = '#fff';
    }
});

// Close sort menu if clicking outside
document.addEventListener('click', (e) => {
    if (isSortMenuOpen && !sortMenu.contains(e.target) && !sortButton.contains(e.target)) {
        isSortMenuOpen = false;
        sortMenu.classList.remove('show');
        sortButton.querySelector('.fa-sort').style.color = '#fff';
    }
});

// Sort Menu Links
sortMenu.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const sortValue = link.dataset.sort;
        const [criteria, order] = sortValue.split('-');
        sortBy = criteria;
        sortOrder = order;

        // Update button text and icon
        sortButton.innerHTML = `<i class="${order === 'asc' ? 'fa-sort-numeric-down' : 'fa-sort-numeric-up'}"></i> ${criteria.charAt(0).toUpperCase() + criteria.slice(1)} (${order === 'asc' ? 'Asc' : 'Desc'})`;
        // If criteria is name, use alpha icons
        if (criteria === 'name') {
            sortButton.innerHTML = `<i class="${order === 'asc' ? 'fa-sort-alpha-down' : 'fa-sort-alpha-up'}"></i> ${criteria.charAt(0).toUpperCase() + criteria.slice(1)} (${order === 'asc' ? 'Asc' : 'Desc'})`;
        }
            sortButton.querySelector('i').style.color = '#00bcd4'; // Highlight active sort

        updateDisplay();
        isSortMenuOpen = false; // Close menu
        sortMenu.classList.remove('show');
    });
});

// --- Initial Display & Setup ---
function initialize() {
    // Initial sort based on default values
    console.log("Soft Kitty")
    currentFiles = sortFiles(filesData, sortBy, sortOrder);
    console.log("Warm Kitty")
    renderFileList(currentFiles);
    console.log("Little ball of fur")
    loadingOverlay.style.opacity = '0';
    setTimeout(() => loadingOverlay.style.display = 'none', 500); // Fade out and hide
}

// --- Pull-to-Refresh Logic ---
let touchstartY = 0;
let touchmove = 0;
let isPulling = false;
const minPullDistance = 50; // Min distance to trigger refresh
const refreshIndicator = document.getElementById('ptrIndicator');

document.addEventListener('touchstart', (e) => {
    touchstartY = e.touches[0].clientY;
    isPulling = true;
    refreshIndicator.style.transition = 'none'; // Disable transition while tracking pull
}, { passive: true });

document.addEventListener('touchmove', (e) => {
    if (!isPulling) return;
    touchmove = e.touches[0].clientY - touchstartY;

    // Only act if pulling down from the top of the scrollable content
    if (touchmove > 0 && window.scrollY === 0) {
        e.preventDefault(); // Prevent background scrolling
        refreshIndicator.style.marginTop = `${Math.min(touchmove - 60, 100)}px`; // Adjust indicator position
        refreshIndicator.querySelector('i').style.transform = `rotate(${Math.min(touchmove / 2, 180)}deg)`;
        refreshIndicator.querySelector('i').className = touchmove > minPullDistance ? 'fas fa-chevron-up' : 'fas fa-chevron-down';
        refreshIndicator.querySelector('span').textContent = touchmove > minPullDistance ? 'Release to refresh' : 'Pull to refresh';

        if (touchmove > minPullDistance) {
            refreshIndicator.classList.add('pulling');
        } else {
            refreshIndicator.classList.remove('pulling');
        }
    } else {
            // If not at top or scrolling up, reset indicator visual
            refreshIndicator.style.marginTop = '-60px';
            refreshIndicator.querySelector('i').className = 'fas fa-chevron-down';
            refreshIndicator.querySelector('span').textContent = 'Pull to refresh';
            refreshIndicator.classList.remove('pulling');
    }
}, { passive: false }); // passive: false needed for preventDefault

document.addEventListener('touchend', () => {
    isPulling = false;
    refreshIndicator.style.transition = 'margin-top 0.3s ease-out'; // Re-enable transition

    if (touchmove > minPullDistance) {
        refreshIndicator.classList.add('refreshing');
        refreshIndicator.querySelector('i').className = 'fas fa-sync fa-spin';
        refreshIndicator.querySelector('span').textContent = 'Refreshing...';
        refreshIndicator.style.marginTop = '0px';

        // --- Simulate a refresh ---
        // In a real app, you'd fetch new data from the server here
        // For now, we'll just re-render the current data
        setTimeout(() => {
            // Here you would re-fetch files_data from the server if it were dynamic
            // e.g., fetch('/api/files').then(res => res.json()).then(newFilesData => { ... });
            
            // For this example, we just re-sort/filter the existing data to show it works
            updateDisplay(); 
            
            refreshIndicator.classList.remove('refreshing');
            refreshIndicator.classList.remove('pulling');
            refreshIndicator.querySelector('i').className = 'fas fa-check-circle'; // Success indicator
            refreshIndicator.querySelector('span').textContent = ' Refreshed!';
            
            setTimeout(() => {
                refreshIndicator.style.marginTop = '-60px'; // Hide after a delay
            }, 1000);

        }, 1500); // Simulate network latency
    } else {
        // If not pulled enough, just reset
        refreshIndicator.style.marginTop = '-60px';
        refreshIndicator.querySelector('i').className = 'fas fa-chevron-down';
        refreshIndicator.querySelector('span').textContent = 'Pull to refresh';
    }
    touchmove = 0; // Reset pull distance
});
console.log("Hello Kitty")

// --- Initial Call ---
window.addEventListener('load', initialize);

function previewFile(filename) {
    const previewModal = document.getElementById('previewModal');
    const previewBody = document.getElementById('previewBody');

    if (!previewModal || !previewBody) {
        console.error("Error: previewModal or previewBody element not found in the DOM.");
        alert("Error: Preview functionality is not set up correctly.");
        return;
    }

    const fileUrl = `/api/download/${filename}`; // Ensure this matches your server's route
    const fileExt = filename.split('.').pop().toLowerCase();

    previewBody.innerHTML = ''; // Clear previous content
    previewModal.style.display = 'flex'; // Show modal

    if (['png','jpg','jpeg','gif','webp'].includes(fileExt)) {
        previewBody.innerHTML = `<img src="${fileUrl}" style="max-width:100%; height:auto;" alt="File Preview" />`;
        console.log(`Loading image: ${fileUrl}`);
    } else if (fileExt === 'txt') {
        console.log(`Fetching text file: ${fileUrl}`);
        fetch(fileUrl)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.text();
            })
            .then(text => {
                const escaped = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                previewBody.innerHTML = `<pre style="white-space:pre-wrap; font-family: monospace; margin: 0;">${escaped}</pre>`;
            })
            .catch(err => {
                console.error("Error previewing text file:", err);
                previewBody.innerHTML = `<p style="color:red;">Error: Could not preview file. ${err.message}</p>`;
            });
    } else {
        previewBody.innerHTML = `<p>File type (${fileExt}) not supported for preview.</p>`;
    }
}

function closePreview() {
    const previewModal = document.getElementById('previewModal');
    const previewBody = document.getElementById('previewBody');
    if (previewModal) previewModal.style.display = 'none';
    if (previewBody) previewBody.innerHTML = ''; // Clear content
}

document.addEventListener('keydown', function(event) {
    const previewModal = document.getElementById('previewModal');
    if (previewModal && previewModal.style.display === 'flex' && event.key === 'Escape') {
        closePreview();
    }
});

document.addEventListener('DOMContentLoaded', (event) => {
    const previewModal = document.getElementById('previewModal');
    if (previewModal) previewModal.style.display = 'none'; // Ensure hidden on load
});

// Add an event listener for the Escape key to close the modal
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        closePreview();
    }
});


function previewFile(filename) {
    const previewModal = document.getElementById('previewModal');
    const previewBody = document.getElementById('previewBody');

    const fileExt = filename.split('.').pop().toLowerCase();

    if (['png','jpg','jpeg','gif','webp'].includes(fileExt)) {
        previewBody.innerHTML = `<img src="${filename}" style="max-width:100%; height:auto;" />`;
    } else if (fileExt === 'txt') {
        fetch(filename)
            .then(res => res.text())
            .then(text => {
                const escaped = text.replace(/</g, "&lt;").replace(/>/g, "&gt;");
                previewBody.innerHTML = `<pre style="white-space:pre-wrap;">${escaped}</pre>`;
            })
            .catch(err => {
                previewBody.innerHTML = `<p style="color:red;">Unable to load file: ${err}</p>`;
            });
    } else {
        previewBody.innerHTML = `<p>This file type cannot be previewed.</p>`;
    }

    previewModal.style.display = 'flex';
}

function closePreview() {
    document.getElementById('previewModal').style.display = 'none';
}


// --- Placeholder for Multi-select (JS logic would go here) ---
// You'd need to:
// 1. Add a checkbox or tap-and-hold gesture to select files.
// 2. Show a "bar" at the bottom with "Download Selected", "Delete Selected" etc.
// 3. Modify the .file-item click listener to toggle selection mode.
// 4. Modify the download button logic to handle multiple files.
