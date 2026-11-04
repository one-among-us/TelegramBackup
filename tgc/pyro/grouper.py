from pathlib import Path
from hypy_utils.dict_utils import remove_nones


def group_msgs(msgs: list[dict], lookup_posts: list[dict] | None = None) -> list[dict]:
    """
    Merge message files into groups

    Conditions: Messages will be sorted by increasing ID (with the oldest message on top)

    :param msgs: Messages
    :param lookup_posts: Optional existing posts to resolve replies against
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

    # Build external lookup map for older posts
    ext_lookup: dict[int, dict] = {}
    for p in (lookup_posts or []):
        ext_lookup[p['id']] = p
        for item in (p.get('images') or []) + (p.get('files') or []):
            stem = Path(item.get('url', '')).stem
            if stem.isdigit():
                ext_lookup[int(stem)] = p

    # Change all reply references
    for m in msgs:
        if 'reply_id' not in m:
            continue
        rid = m.pop('reply_id')
        rm = reply_map.get(rid) or id_map.get(rid) or ext_lookup.get(rid)

        if rm:
            thumb = None
            if rm.get('files'):
                thumb = rm['files'][0].get('thumb')
            elif rm.get('images'):
                thumb = rm['images'][0].get('thumb')
            elif rm.get('file'):
                thumb = rm['file'].get('thumb')
            elif rm.get('image'):
                thumb = rm['image'].get('thumb')
            elif isinstance(rm.get('reply'), dict):
                thumb = rm['reply'].get('thumb')

            m['reply'] = {
                'id': rm['id'],
                'text': rm.get('text'),
                'thumb': thumb
            }
        else:
            m['reply'] = {
                'id': rid
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
