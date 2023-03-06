import html
import json
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path

from dateutil import parser
from feedgen.feed import FeedGenerator
from html2text import html2text
from markdown import markdown


@dataclass
class FeedMeta:
    title: str
    link: str
    description: str
    language: str
    image_url: str


def posts_to_feed(path: Path, meta: FeedMeta):
    """
    Convert posts to RSS feed. This function will create the rss feed in the same directory as posts.json

    :param path: Path to the parent directory that contains posts.json
    :param meta: Feed meta info
    """
    fg = FeedGenerator()
    
    # Meta info
    fg.id(meta.link)
    fg.title(meta.title)
    fg.link(href=meta.link, rel='alternate')
    fg.description(meta.description)
    fg.language(meta.language)
    fg.image(meta.image_url)

    # Posts
    posts = json.loads((path / 'posts.json').read_text())
    for post in posts:
        fe = fg.add_entry()
        fe.id(str(post['id']))
        fe.title(f"{meta.title} #{post['id']}")
        fe.link(href=f'{meta.link}?post={post["id"]}')
        fe.updated(parser.parse(post['date']).replace(tzinfo=timezone.utc))

        # Escape HTML tags
        # text = html2text(markdown(post.get('text') or post.get('caption') or ''), bodywidth=0)
        # text = html.escape(text.replace('\n', '<br>'))
        text = markdown(post.get('text') or post.get('caption') or '')
        fe.description(text)

    fg.rss_file(path / 'rss.xml', pretty=True)
    fg.atom_file(path / 'atom.xml', pretty=True)
