# stalnks

Discord bot for tracking and predicting Animal Crossisng New Horizons turnip prices.

Prediction is powered by [ac-nh-turnip-prices](https://github.com/mikebryant/ac-nh-turnip-prices).

## User interface

When a user sends a price and optionally an indication of the period it is for (day and morning/afternoon), the bot saves it to the database and uses [ac-nh-turnip-prices](https://github.com/mikebryant/ac-nh-turnip-prices) to create and reply with the price prediction table that includes all previous prices provided by that user.

If day is not specified, it is inferred based on the bot's local time.

Sending the exact message "dump" will cause the bot to upload a copy of it's database.

## Installation

Python 3.7 or later required.

Make sure the git submodule stuff is all in order. The `ac-nh-turnip-prices` directory should exist and not be empty.

```
python3 -m venv ../venv_stalnks
. ../venv_stalnks/bin/activate
pip install -r requirements.txt
```

Install `chromium` from your distro package manager.

Install the relevant version of `chromedriver` from <https://sites.google.com/a/chromium.org/chromedriver/downloads>.

## Configuration

Copy `cfg.py.dist` to `cfg.py`.

Go to <https://discordapp.com/developers/applications> and select/create an app, then choose "Bot" from the sidebar. Generate and copy the token, filling it in to `TOKEN` in `cfg.py`.

Choose "OAuth2" from the sidebar and under the "OAuth2 URL Generator" section, tick the "bot" scope and tick the "Send Messages" and "Attach Files" text permissions.

Copy and visit the generated URL and follow the instructions to grant the bot permissions on your server.

In Discord, right click the channel you want the bot to operate in and copy ID. Fill that in as `CHANNEL_ID` in `cfg.py`.

Also in `cfg.py`, replace the `...` in `WEBROOT` with the absolute path to where you checked out this repo.

You can customise `DB` location, but the default should be fine.

## Running

```
. ../venv_stalnks/bin/activate
./main.py
```

## Architecture

`main.py` contains the top level flow for connecting to Discord using [discord.py](https://discordpy.readthedocs.io/en/latest/) and handling incoming messages as well as a background task to dump and clear the database when Sunday ticks around.

`stalnks/` contains logic for extracting the price/day/time of day from user text messages, abstraction for database access and control of the prediction webpage using [Selenium](https://selenium-python.readthedocs.io/).

## Feedback

Welcome via email, issues, pull requests or whatever else you think will get my attention.

Note that I did not write the prediction web page, please refer to [ac-nh-turnip-prices](https://github.com/mikebryant/ac-nh-turnip-prices).
