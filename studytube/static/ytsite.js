
function fetchVideos(page) {
    fetch(`/videos/${page}`)
        .then(response => response.json())
        .then(data => {
            const videoGrid = document.getElementById('videoGrid');
            videoGrid.innerHTML = '';  // Clear existing content
            data.videos.forEach(video => {
                const videoElement = document.createElement('div');
                videoElement.className = 'videoItem';
                videoElement.innerHTML = `
                    <a href="/video/${video.doc}">
                        <img src="https://img.youtube.com/vi/${extractVideoID(video.url)}/0.jpg" alt="${video.title}">
                        <h3>${video.title}</h3>
                    </a>
                    <p>Views: ${parseInt(video.view_count).toLocaleString()}</p>
                    <p>Upload Date: ${new Date(video.upload_date).toLocaleDateString()}</p>
                    <p>Channel: ${video.channel_name}</p>
                `;


                videoGrid.appendChild(videoElement);
            });

            setupPagination(data.total_pages, page);
        })
        .catch(error => console.error('Error:', error));
}


function extractVideoID(url) {
    const regExp = /^.*(youtu.be\/|v\/|e\/|u\/\w+\/|embed\/|v=)([^#\&\?]*).*/;
    const match = url.match(regExp);

    if (match && match[2].length === 11) {
        return match[2];
    } else {
        return null; // Handle the case where the URL does not contain a valid ID
    }
}

let currentFilter = 'ALL'; // Default to 'ALL'
let currentSearchTerm = ''; // Default to empty
let currentSort = ''; // Default sort


// PAGES


function setupPagination(totalPages, currentPage) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = ''; // Clear existing pagination buttons
    for (let i = 1; i <= totalPages; i++) {
        const pageButton = document.createElement('button');
        pageButton.innerText = i;
        pageButton.onclick = () => {
            if (currentFilter && currentFilter !== 'ALL') {
                fetchFilteredVideos(i, currentFilter);
            } else if (currentSearchTerm) {
                fetchSearchResults(i);
            } else if (currentSort) {
                fetchSortedVideos(i, currentSort);
            } else {
                fetchVideos(i);
            }
        };
        if (i === currentPage) {
            pageButton.className = 'active';
        }
        pagination.appendChild(pageButton);
    }
}


// FILTER VIDEOS


function filterVideos() {
    currentFilter = document.getElementById('tagFilter').value;
    fetchFilteredVideos(1, currentFilter); // Fetch the first page of videos with the selected filter
}


function fetchFilteredVideos(page, tag) {
  fetch(`/api/videos?page=${page}&filter_tag=${encodeURIComponent(tag)}`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        if (!data.videos) {
            throw new Error('No videos data found');
        }
        updateVideoGrid(data.videos);
        setupPagination(data.total_pages, page);
    })
    .catch(error => {
        console.error('Error:', error);
    });

}

function updateVideoGrid(videos) {
    const videoGrid = document.getElementById('videoGrid');
    videoGrid.innerHTML = '';  // Clear existing content
    videos.forEach(video => {
        const videoElement = document.createElement('div');
        videoElement.className = 'videoItem';
        videoElement.innerHTML = `
            <a href="/video/${video.doc}">
            <img src="https://img.youtube.com/vi/${extractVideoID(video.url)}/0.jpg" alt="${video.title}">
            <h3>${video.title}</h3>
            <p>Views: ${parseInt(video.view_count).toLocaleString()}</p>
            <p>Upload Date: ${new Date(video.upload_date).toLocaleDateString()}</p>
            <p>Channel: ${video.channel_name}</p>
        `;
        videoGrid.appendChild(videoElement);
    });
}



// SORTING


// Assuming you have a sort button and a dropdown for sort criteria in your HTML
document.getElementById('sortButton').addEventListener('click', function() {
    const currentSort = document.getElementById('sortDropdown').value;
    fetchSortedVideos(1, currentSort) // Fetch the first page of sorted videos
    });

    function fetchSortedVideos(page, currentSort) {
        fetch(`/api/videos?page=${page}&sort_by=${currentSort}&filter_tag=${encodeURIComponent(currentFilter)}`)
            .then(response => response.json())
            .then(data => {
                console.log("Server response:", data); // Log the response
                updateVideoGrid(data.videos);
                setupPagination(data.total_pages, page);
            })
            .catch(error => console.error('Error:', error));
    }
    

// TAG MANAGEMENT


async function fetchAndPopulateTags() {
    try {
        const response = await fetch('http://127.0.0.1:5000/api/tags');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const tags = await response.json();
        populateTagFilter(tags);
    } catch (error) {
        console.error('Error fetching tags:', error);
    }
}

function populateTagFilter(tags) {
    const tagFilter = document.getElementById('tagFilter');

    const allOption = document.createElement('option');
    allOption.value = 'ALL';
    allOption.textContent = 'ALL';
    tagFilter.appendChild(allOption);

    // Add other tags
    tags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag;
        option.textContent = tag;
        tagFilter.appendChild(option);
    });
}


// SEARCH
function searchVideos() {
    const searchTerm = document.getElementById('searchInput').value;
    fetch(`/api/search?query=${encodeURIComponent(searchTerm)}`)
        .then(response => response.json())
        .then(data => {
            updateVideoGrid(data.videos);
            setupPagination(Math.ceil(data.total_results / 20), 1); // Assuming 20 results per page
        })
        .catch(error => console.error('Error:', error));
}


window.onload = async function() {
    await fetchAndPopulateTags(); // Wait for tags to be fetched
    fetchVideos(1); // Then fetch the first page of videos
};
