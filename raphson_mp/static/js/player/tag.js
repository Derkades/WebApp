async function updateTagCheckboxes() {
    const tags = await music.tags();

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

document.addEventListener('DOMContentLoaded', updateTagCheckboxes);

function getTagFilter() {
    const mode = document.getElementById('tag-mode').value;
    if (mode == 'none') {
        return {};
    }

    const tags = [];
    for (const checkbox of document.getElementsByClassName('tag-checkbox')) {
        if (checkbox.checked) {
            tags.push(checkbox.dataset.tag);
        }
    }

    return {tag_mode: mode, tags: tags};
}

function areAllCheckboxesChecked() {
    for (const checkbox of document.getElementsByClassName('tag-checkbox')) {
        if (!checkbox.checked) {
            return false;
        }
    }
    return true;
}

function setAllCheckboxesChecked(checked) {
    for (const checkbox of document.getElementsByClassName('tag-checkbox')) {
        checkbox.checked = checked;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('select-all').addEventListener('click', () => {
        setAllCheckboxesChecked(!areAllCheckboxesChecked());
    });
});
