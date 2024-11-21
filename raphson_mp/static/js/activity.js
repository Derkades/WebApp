function getNowPlayingCardHtml(info) {
    const card = document.createElement('div');
    card.classList.add('box');

    const cardHeader = document.createElement('div');
    cardHeader.classList.add('box-header');
    cardHeader.textContent = info.username;
    card.append(cardHeader);

    const cardBody = document.createElement('div');
    cardBody.classList.add('activity-box-body');
    card.append(cardBody);

    const coverThumbUrl = `/track/${encodeURIComponent(info.path)}/cover?quality=low`;
    const coverFullUrl = `/track/${encodeURIComponent(info.path)}/cover?quality=high`;

    const coverImg = document.createElement('a');
    coverImg.classList.add('cover-img')
    coverImg.href = coverFullUrl;
    coverImg.style.backgroundImage = `url("${coverThumbUrl}")`;

    const imgInner = document.createElement('div');
    imgInner.classList.add('cover-img-overlay');

    if (info.paused) {
        imgInner.classList.add('icon-pause');
    }

    coverImg.append(imgInner);
    cardBody.append(coverImg);

    const infoDiv = document.createElement('div');
    cardBody.append(infoDiv);

    if (info.title && info.artists.length > 0) {
        const titleDiv = document.createElement('div');
        titleDiv.style.fontSize = '1.3em';
        titleDiv.textContent = info.title;
        const artistDiv = document.createElement('div');
        artistDiv.style.fontSize = '1.1em';
        artistDiv.textContent = info.artists.join(', ');
        infoDiv.append(titleDiv, artistDiv);
    } else {
        const fallbackDiv = document.createElement('div');
        fallbackDiv.style.fontSize = '1.1em';
        fallbackDiv.textContent = info.display;
        infoDiv.append(fallbackDiv);
    }

    const playlistDiv = document.createElement('div');
    playlistDiv.classList.add('secondary');
    playlistDiv.textContent = info.playlist;
    infoDiv.append(playlistDiv);

    const progressBar = document.createElement('div');
    progressBar.classList.add('activity-progress');
    progressBar.style.width = (100 * info.position / info.duration) + '%';
    card.append(progressBar);

    return card;
}

function createTableRow(contents) {
    const row = document.createElement('tr');
    for (const content of contents) {
        const col = document.createElement('td');
        col.textContent = content;
        row.append(col);
    }
    return row;
}

function getHistoryRowHtml(info) {
    return createTableRow([info.time_ago, info.username, info.playlist, info.display]);
}

function getFileChangeRowHtml(info) {
    return createTableRow([info.time_ago, info.action, info.playlist, info.track]);
}

const nowPlayingDiv = document.getElementById('now-playing');
const nothingPlayingText = document.getElementById('nothing-playing-text').textContent;
const historyTable = document.getElementById('tbody-history');
const fileChangesTable = document.getElementById('tbody-changes');
let data = null;

function updateNowPlayingHtml() {
    const cards = data.now_playing.map(getNowPlayingCardHtml);
    if (cards.length > 0) {
        nowPlayingDiv.replaceChildren(...cards);
    } else {
        nowPlayingDiv.textContent = nothingPlayingText;
    }
}

function updateTableHtml() {
    historyTable.replaceChildren(...data.history.map(getHistoryRowHtml));
    fileChangesTable.replaceChildren(...data.file_changes.map(getFileChangeRowHtml));
}

async function fetchData() {
    if (document.visibilityState == "hidden") {
        return;
    }

    const response = await fetch('/activity/data');
    if (response.status != 200) {
        return;
    }
    const json = await response.json();
    console.debug('fetched data:', json);
    data = json;

    updateTableHtml();
}

function quickUpdate() {
    if (data == null || document.visibilityState != "visible") {
        return;
    }

    for (const now_playing of data['now_playing']) {
        if (!now_playing.paused && now_playing.position < now_playing.duration - 1) {
            now_playing.position += 1;
        }
    }

    updateNowPlayingHtml();
}

document.addEventListener('DOMContentLoaded', async () => {
    setInterval(fetchData, 15_000);
    setInterval(quickUpdate, 1_000);
    addEventListener("visibilitychange", async () => {
        if (!document.visibilityState != "hidden") {
            await fetchData();
            quickUpdate();
        }
    });

    await fetchData();
    updateNowPlayingHtml();
});
