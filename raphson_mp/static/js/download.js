async function performSearch() {
    const searchQuery = document.getElementById('search-query');

    if (searchQuery.value == '') {
        return;
    }

    const searchButton = document.getElementById('search-button');
    const searchLoading = document.getElementById('search-loading');
    const searchTable = document.getElementById('search-table');
    const searchResults = document.getElementById('search-results');
    const downloadUrl = document.getElementById('download-url');

    searchResults.replaceChildren();
    searchButton.classList.add('hidden');
    searchLoading.classList.remove('hidden');

    try {
        const response = await jsonPost('/download/search', {query: searchQuery.value});
        const json = await response.json();

        for (const result of json.results) {
            const tdTitle = document.createElement('td');
            tdTitle.textContent = result.title;
            const tdViews = document.createElement('td');
            tdViews.textContent = formatLargeNumber(result.view_count);
            const tdDuration = document.createElement('td');
            tdDuration.textContent = result.duration_string;
            const tdChannel = document.createElement('td');
            tdChannel.textContent = result.channel_name + ' (' + formatLargeNumber(result.channel_subscribers) + ')';

            const row = document.createElement('tr');
            row.style.cursor = 'pointer';
            row.append(tdTitle, tdViews, tdDuration, tdChannel);
            searchResults.append(row);

            row.addEventListener('click', () => downloadUrl.value = result.url);
        }
        searchTable.classList.remove('hidden');
    } catch (exception) {
        console.error(exception);
        alert("Search error")
    }

    searchButton.classList.remove('hidden');
    searchLoading.classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('search-form').onsubmit = () => {
        performSearch();
        return false;
    };

    const downloadUrl = document.getElementById('download-url');
    const downloadPlaylist = document.getElementById('download-playlist');
    const downloadButton = document.getElementById('download-button');
    const downloadLoading = document.getElementById('download-loading');
    const downloadLog = document.getElementById('download-log');

    downloadButton.addEventListener('click', () => {
        downloadButton.classList.add('hidden');
        downloadLoading.classList.remove('hidden');

        downloadLog.style.backgroundColor = '';
        downloadLog.textContent = '';

        (async function(){
            const decoder = new TextDecoder();

            function handleResponse(result) {
                downloadLog.textContent += decoder.decode(result.value);
                downloadLog.scrollTop = downloadLog.scrollHeight;
                return result
            }

            const response = await jsonPost('/download/ytdl', {directory: downloadPlaylist.value, url: downloadUrl.value});
            const reader = await response.body.getReader();
            await reader.read().then(function process(result) {
                if (result.done) {
                    console.debug("stream done");
                    return reader.closed;
                }
                return reader.read().then(handleResponse).then(process)
            });

            if (downloadLog.textContent.endsWith('Done!')) {
                downloadLog.style.backgroundColor = 'darkgreen';
            } else {
                downloadLog.style.backgroundColor = 'darkred';
            }
        })().then(() => {
            downloadButton.classList.remove('hidden');
            downloadLoading.classList.add('hidden');
        }).catch(err => {
            downloadButton.classList.remove('hidden');
            downloadLoading.classList.add('hidden');
            console.error(err);
            alert('error, check console');
        });
    });
});
