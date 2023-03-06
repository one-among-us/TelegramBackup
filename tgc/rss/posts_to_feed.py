import json
from dataclasses import dataclass
from pathlib import Path

from feedgen.feed import FeedGenerator


@dataclass
class FeedMeta:
    title: str
    link: str
    description: str
    language: str


def posts_to_feed(path: Path, meta: FeedMeta):
    """
    Convert posts to RSS feed. This function will create the rss feed in the same directory as posts.json

    :param path: Path to the parent directory that contains posts.json
    :param meta: Feed meta info
    """
    fg = FeedGenerator()
    
    # Meta info
    fg.title(meta.title)
    fg.link(href=meta.link, rel='alternate')
    fg.description(meta.description)
    fg.language(meta.language)

    # Posts
    posts = json.loads((path / 'posts.json').read_text())
    for post in posts:
        fe = fg.add_entry()
        fe.id(post['id'])
        fe.description(post['text'])
        fe.pubDate(post['date'])

    fg.rss_file(path / 'feed.xml')
