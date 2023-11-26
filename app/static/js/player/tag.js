function updateTagCheckboxes() {
    const tagsSet = new Set();

    for (const track of Object.values(state.tracks)) {
        for (const tag of track.tags) {
            tagsSet.add(tag);
        }
    }

    const tags = [...tagsSet].sort();

    const newChildren = [];

    let i = 0;
    for (const tag of tags) {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('tag-checkbox');
        checkbox.id = 'tag-checkbox-' + i;
        checkbox.dataset.tag = tag;
        checkbox.checked = true;
        newChildren.push(checkbox);
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        const link = document.createElement('a');
        link.textContent = tag;
        link.onclick = event => {
            event.preventDefault();
            browse.browseTag(tag);
        };
        label.appendChild(link);
        newChildren.push(label);
        newChildren.push(document.createElement('br'));
        i++;
    }

    document.getElementById('tag-checkboxes').replaceChildren(...newChildren);
}

eventBus.subscribe(MusicEvent.TRACK_LIST_CHANGE, updateTagCheckboxes);

function getTagFilter() {
    const mode = document.getElementById('tag-mode').value;
    const tags = [];
    for (const checkbox of document.getElementsByClassName('tag-checkbox')) {
        if (checkbox.checked && mode === 'allow' || !checkbox.checked && mode == 'deny') {
            tags.push(checkbox.dataset.tag);
        }
    }

    return {tag_mode: mode, tags: tags.join(';')};
}
