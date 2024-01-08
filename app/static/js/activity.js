function getNowPlayingCardHtml(info) {
    const card = document.createElement('div');
    card.classList.add('card');

    const cardHeader = document.createElement('div');
    cardHeader.classList.add('card-header');
    cardHeader.textContent = info.username;
    card.append(cardHeader);

    const cardBody = document.createElement('div');
    cardBody.classList.add('card-body');
    cardBody.style.display = 'flex';
    card.append(cardBody);

    const imageThumb = '/track/album_cover?quality=low&path=' + encodeURIComponent(info.path);
    const imageFull = '/track/album_cover?quality=high&path=' + encodeURIComponent(info.path);

    const imgOuter = document.createElement('a');
    imgOuter.href = imageFull;
    imgOuter.style.display = 'block';
    imgOuter.style.height = '8rem';
    imgOuter.style.width = '8rem';
    imgOuter.style.borderRadius = 'var(--border-radius-amount)';
    imgOuter.style.background = `url("${imageThumb}") no-repeat center`;
    imgOuter.style.backgroundSize = 'cover';

    const imgInner = document.createElement('div');
    imgInner.style.width = '100%';
    imgInner.style.height = '100%';

    if (info.paused) {
        imgInner.style.background = `url("/static/icon/pause.svg") no-repeat center`;
        imgInner.style.backgroundSize = 'cover';
        imgInner.style.filter = 'invert(1)';
    }

    imgOuter.append(imgInner);
    cardBody.append(imgOuter);

    const infoDiv = document.createElement('div');
    infoDiv.style.marginLeft = '.5rem';
    cardBody.append(infoDiv);

    if (info.title && info.artists) {
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
        fallbackDiv.textContent = info.fallback_title;
        infoDiv.append(fallbackDiv);
    }

    const playlistDiv = document.createElement('div');
    playlistDiv.classList.add('secondary');
    playlistDiv.style.marginTop = '.5rem';
    playlistDiv.textContent = info.playlist;
    infoDiv.append(playlistDiv);

    const progressBar = document.createElement('div');
    progressBar.classList.add('card-progress');
    progressBar.style.width = info.progress + '%';
    card.append(progressBar);

    return card;
}

function getHistoryRowHtml(info) {
    const colTime = document.createElement('td');
    colTime.textContent = info.time_ago;

    const colUsername = document.createElement('td');
    colUsername.textContent = info.username;

    const colPlaylist = document.createElement('td');
    colPlaylist.textContent = info.playlist;

    const colTitle = document.createElement('td');
    colTitle.textContent = info.title;

    const row = document.createElement('tr');
    row.append(colTime, colUsername, colPlaylist, colTitle);
    return row;
}

function getFileChangeRowHtml(info) {
    const colTime = document.createElement('td');
    colTime.textContent = info.time_ago;

    const colAction = document.createElement('td');
    colAction.textContent = info.action;

    const colPlaylist = document.createElement('td');
    colPlaylist.textContent = info.playlist;

    const colTrack = document.createElement('td');
    colTrack.textContent = info.track;

    const row = document.createElement('tr');
    row.append(colTime, colAction, colPlaylist, colTrack);
    return row;
}

const nowPlayingDiv = document.getElementById('now-playing');
const nothingPlayingText = document.getElementById('nothing-playing-text').textContent;
const historyTable = document.getElementById('tbody-history');
const fileChangesTable = document.getElementById('tbody-changes');

async function updateNowPlaying() {
    if (document.visibilityState == "hidden") {
        return;
    }

    const response = await fetch('/activity/data');
    if (response.status != 200) {
        return;
    }
    const json = await response.json();
    console.debug('fetched data:', json);

    const cards = json.now_playing.map(getNowPlayingCardHtml);
    if (cards.length > 0) {
        nowPlayingDiv.replaceChildren(...cards);
    } else {
        nowPlayingDiv.textContent = nothingPlayingText;
    }

    historyTable.replaceChildren(...json.history.map(getHistoryRowHtml));

    fileChangesTable.replaceChildren(...json.file_changes.map(getFileChangeRowHtml));
}

document.addEventListener('DOMContentLoaded', () => {
    updateNowPlaying();
    setInterval(updateNowPlaying, 5_000);
    addEventListener("visibilitychange", event => {
        if (!document.hidden) {
            updateNowPlaying();
        }
    });
});
