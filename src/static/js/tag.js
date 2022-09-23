function updateTagCheckboxes() {
    const tags = new Set();

    for (const track of state.tracks) {
        for (const tag of track.tags) {
            tags.add(tag);
        }
    }

    const newChildren = [];

    let i = 0;
    for (const tag of tags) {
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.classList.add('tag-checkbox');
        checkbox.id = 'tag-checkbox-' + i
        checkbox.checked = true;
        newChildren.push(checkbox);
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = tag;
        newChildren.push(label);
        newChildren.push(document.createElement('br'));
        i++;
    }

    document.getElementById('tag-checkboxes').replaceChildren(...newChildren);
}