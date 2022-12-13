# TelegramBackup

Backup / convert telegram channel / chat data.

## Usage

### Installation

First, install Python `>= 3.11`. Then, run `pip install tgc`

### Convert Export for tg-blog

To convert an export file into a format supported by [tg-blog](https://github.com/one-among-us/tg-blog), you first need to install some additional dependencies for conversion:

1. Install Node 19.2 and yarn 1.22
2. `yarn global add puppeteer-lottie-cli`
3. Install ffmpeg using your system package manager

Then, you can convert an export by typing `tgce <export path>`

