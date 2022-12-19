from hypy_utils.dict_utils import remove_nones


def group_msgs(msgs: list[dict]) -> list[dict]:
    """
    Merge message files into groups

    Conditions: Messages will be sorted by increasing ID (with the oldest message on top)

    :param msgs: Messages
    :return: Messages with file groups
    """
    # Sort messages
    msgs = sorted(msgs, key=lambda x: x['id'])

    # Find groups
    id_map = {m['id']: m for m in msgs}
    tmp_grouped: list[dict] = [d for d in msgs if 'media_group_id' in d]
    gids: set[int] = {d['media_group_id'] for d in tmp_grouped}
    groups: dict[int, list[dict]] = {g: [d for d in tmp_grouped if d['media_group_id'] == g] for g in gids}

    # Group messages
    result = []
    reply_map: dict[int, dict] = {}
    for gid, grp in groups.items():
        # Loop through each message, find the first message with text
        def find_dominant():
            for m in grp:
                if 'text' in m:
                    return m
            return grp[0]

        m = find_dominant()
        result.append(m)
        reply_map.update({a['id']: m for a in grp})

        # Group files & images into a list
        m['files'] = [a.get('file') for a in grp if 'file' in a] or None
        m['images'] = [a.get('image') for a in grp if 'image' in a] or None

        # Clean up nones
        m.pop('file', None)
        m.pop('image', None)
        if not m['files']:
            del m['files']
        if not m['images']:
            del m['images']

    # Change all reply references
    for m in msgs:
        if 'reply_id' not in m:
            continue
        rid = m.pop('reply_id')
        rm = reply_map.get(rid) or id_map[rid]

        m['reply'] = {
            'id': rm['id'],
            'text': rm.get('text'),
            'thumb': ((rm.get('files') or [None])[0] or {}).get('thumb')
        }

    # Add non-grouped messages to results
    grouped_ids = {m['id'] for v in groups.values() for m in v}
    ungrouped = [m for m in msgs if m['id'] not in grouped_ids]
    for m in ungrouped:
        if 'file' in m:
            m['files'] = [m.pop('file')]
        if 'image' in m:
            m['images'] = [m.pop('image')] or None
    result += ungrouped

    return sorted(remove_nones(result), key=lambda x: x['id'])
