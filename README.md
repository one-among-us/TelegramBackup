# TelegramBackup

This is the Telegram adapter for [tg-blog](https://github.com/one-among-us/tg-blog), a front-end for displaying telegram (or any compatible) channel data as a blog.
    
Backup / convert telegram channel / chat data.

## Usage

### Installation

First, install Python `>= 3.11`. Then, run `pip install tgc`

Then, to support video/animation/sticker conversion, you have to install the following non-python dependencies:

1. Install Node 19.2 and yarn 1.22
2. `yarn global add puppeteer-lottie-cli`
3. Install `ffmpeg` using your system package manager

### Mode 1: Convert Telegram Export

If you only need a one-time export, you can use mode 1. To do this, you first need to export a channel using [tdesktop](https://github.com/telegramdesktop/tdesktop).

To convert an export file into a format supported by [tg-blog](https://github.com/one-among-us/tg-blog), you can run `tgce <export path>`

### Mode 2: Crawl Channel using MTProto API

If you have the permission to add a bot account to a channel, or invite a self-bot account, you can use the MTProto crawler for automatic incremental export updates. (**Please, do not log into your own Telegram account for crawling**, there's a very high chance of being mis-classified as spam and get banned)

Using this method, it can automatically update the channel backup incrementally, and the information will be more complete. However, it is more difficult to set up than mode 1.

#### Setup API Keys

1. Obtain `api_id` and `api_hash` by creating your Telegram application ([Official Guide](https://core.telegram.org/api/obtaining_api_id#obtaining-api-id))
   1. Log into https://my.telegram.org/apps
   2. Fill out the form to create an application
2. Choose which type of account to log in:
   1. **Bot account**: Create a bot using the [@BotFather](https://t.me/BotFather) bot.
   2. **Self-bot account**: Leave `bot_token` blank, it will prompt you to login. You should only use a self-bot when you're not the admin of the channel (because inviting a bot requires admin access). 
3. Fill in the tokens in `~/.config/tgc/config.toml` as shown below

```toml
# Telegram API id
api_id = 10000000

# Telegram API hash
api_hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# Telegram bot token (can be blank)
bot_token = "0000000000:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
```

After setting up the keys, you can proceed to setting up the channel:

#### Setup Channels to be Crawled

1. Either invite your bot to the channel or join the channel on your self-bot account
2. Forward a channel message to [@RawDataBot](https://t.me/RawDataBot) to obtain the channel ID. (You'll see a JSON response, and you can find the ID from the `forward_from_chat` field)
3. Fill in the channel info in `~/.config/tgc/config.toml` as shown below

```toml
# One export entry in a list of exports
[[exports]]
# Telegram chat id
chat_id = -1001191767119
# Output Path
path = "exports/hykilp"
```

After all setup is complete, you can proceed to running the crawler.

#### Running the Crawler

Simply run the `tgc` command.
