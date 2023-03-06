import argparse
import json
from pathlib import Path

import toml

from tgc.rss.posts_to_feed import FeedMeta, posts_to_feed

if __name__ == '__main__':
    # Create argument parser
    parser = argparse.ArgumentParser(description='Convert posts.json to RSS feed')
    parser.add_argument('path', help='Path to the directory that contains posts.json', nargs='?', default='.')

    # Supply meta info through arguments
    parser.add_argument('--title', help='Feed title')
    parser.add_argument('--link', help='Feed link')
    parser.add_argument('--description', help='Feed description')
    parser.add_argument('--language', help='Feed language')
    parser.add_argument('--image-url', help='Feed image URL')

    # Supply meta info through config file
    parser.add_argument('-c', '--config', help='Path to rss.toml file')
    args = parser.parse_args()

    # Check if posts.json exists
    if not Path(args.path) / 'posts.json':
        print('Please execute this command in the directory that contains posts.json')
        exit(1)

    # Create meta info object
    meta = FeedMeta(
        title=args.title,
        link=args.link,
        description=args.description,
        language=args.language,
        image_url=args.image_url
    )

    # Load meta info from rss.toml
    if args.config:
        config = toml.loads(Path(args.config).read_text())
        meta = FeedMeta(**config)

    # Check necessary meta info
    if not meta.title or not meta.link or not meta.description or not meta.language or not meta.image_url:
        print('Meta is:', meta)
        print('Please supply all necessary meta info')
        exit(1)

    # Call posts_to_feed
    posts_to_feed(Path(args.path), meta)
