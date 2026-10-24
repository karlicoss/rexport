

Export your personal Reddit data: saves, upvotes, submissions etc. as JSON.

<!-- Keep this separator: Quarto otherwise moves the generated preamble below the following heading. -->

# Installing

## Basic install

Install with pip:

`pip3 install 'rexport[export,dal,optional] @ git+https://github.com/karlicoss/rexport'`

The [‘extras’](https://packaging.python.org/en/latest/tutorials/installing-packages/#installing-extras) in square brackets provide additional dependencies, feel free to omit some of them if you don’t need them:

- `export` is needed for [export functionality](#exporting)
- `dal` is needed to [access exported data](#using-the-data)
- `optional` is for nicer logging facilities and faster JSON processing

See the [`optional-dependencies`](pyproject.toml) section in `pyproject.toml` for more details.

## Advanced install options

- editable install

  You’ll need to clone the repository with submodules.

  - use `git clone --recursive`, or `git pull && git submodule update --init`
  - after that, you can use `pip3 install --editable`

- run via `uvx`

  This allows you to run rexport without installing it if you just want to quickly try it out. E.g.:

  `uvx --from 'rexport[export,dal,optional] @ git+https://github.com/karlicoss/rexport' python3 -m rexport.export ...`

  It’s a little awkward though since you can’t install tools without ‘executable scripts’ with uv at the moment.

# Exporting

## Running export

Usage:

**Recommended**: create `secrets.py` keeping your API parameters, e.g.:

    username = "USERNAME"
    password = "PASSWORD"
    client_id = "CLIENT_ID"
    client_secret = "CLIENT_SECRET"

After that, use:

    python3 -m rexport.export --secrets /path/to/secrets.py

That way you type less and have control over where you keep your plaintext secrets.

**Alternatively**, you can pass parameters directly, e.g.

    python3 -m rexport.export --username <username> --password <password> --client_id <client_id> --client_secret <client_secret>

However, this is verbose and prone to leaking your keys/tokens/passwords in shell history.

You can also import `export.py` as a module and call `get_json` function directly to get raw JSON.

I **highly** recommend checking exported files at least once just to make sure they contain everything you expect from your export.
If they don’t, please feel free to ask or raise an issue!

## Setting up API parameters

1.  Register a [custom ‘personal script’ app](https://www.reddit.com/prefs/apps) and get `client_id` and `client_secret` parameters.

    See [PRAW’s authentication documentation](https://praw.readthedocs.io/en/latest/getting_started/authentication.html) for more details.

2.  To access personal data such as saved posts and comments, Reddit’s API also requires `username` and `password`.

    Unfortunately, it requires your plaintext Reddit password. You can read more about it in [PRAW’s quick start](https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#authorized-reddit-instances).

    If you have two-factor authentication enabled, append the six-digit 2FA token to the password, separated by a colon:

    ``` python
    password = "PASSWORD:343642"
    ```

    The token will, however, be short-lived.

# API limitations

**WARNING**: Reddit’s API [limits queries to 1,000 entries](https://www.reddit.com/r/redditdev/comments/61z088/sample_more_than_1000_submissions_within_subreddit).

I **highly** recommend backing up regularly and keeping old exports. An easy way to achieve it is a command like this:

``` bash
python3 -m rexport.export --secrets /path/to/secrets.py >"export-$(date -I).json"
```

Alternatively, you can use [arctee](https://github.com/karlicoss/arctee), which automates this.

<!-- TODO link to exports post? -->

<!-- TODO link how DAL part can merge them together -->

Check out these links if you’re interested in getting older data that is inaccessible through the API:

- a [comment](https://www.reddit.com/r/DataHoarder/comments/d0hjs7/reddit_takeout_export_your_account_data_as_json/ezbbcxe) by /u/binkarus
- [Reddit admins](https://www.reddit.com/r/ideasfortheadmins/wiki/faq#wiki_can_we_have_a_way_to_download_our_entire_history_even_though_reddit_cuts_off_at_a_certain_point.3F) say the rationale behind the API limitation is performance and caching
- perhaps you can request all of your data under [GDPR](https://www.reddit.com/r/DataHoarder/comments/d0hjs7/reddit_takeout_export_your_account_data_as_json/eza0nsx); I haven’t tried that personally
- [Pushshift](https://pushshift.io) can help you retrieve old data. You can use [purarue/pushshift_comment_export](https://github.com/purarue/pushshift_comment_export) to get the data.

# Example output

See [example-output.json](example-output.json) for example data you might find in your export. I’ve cleaned it up a bit because it has many different fields, many of which are probably not relevant.

The format is API-dependent and changes over time, so check the [Reddit API](https://www.reddit.com/dev/api) if you are looking for something specific.

# Using the data

You can use this DAL (Data Access/Abstraction Layer) module to access your exported data, even offline.
I elaborate on motivation behind it [here](https://beepb00p.xyz/exports.html#dal).

- the main use case is importing it as a Python module for **programmatic access** to your data.

  You can find some inspiration in [`my.`](https://beepb00p.xyz/mypkg.html) package that I’m using as an API to all my personal data.

- to test it against your export, simply run: `python3 -m rexport.dal /path/to/export`

- you can also try it interactively in an IPython shell: `python3 -m rexport.dal /path/to/export --interactive`

## Example output

    Your most saved subreddits:
    [('orgmode', 50),
     ('emacs', 36),
     ('QuantifiedSelf', 33),
     ('AskReddit', 33),
     ('selfhosted', 29)]

# Contributing

If you want to contribute to or develop this project, check out [GitHub Actions](.github/workflows/main.yml) to see how the project is run and tested.

Generally, you should be able to run the checks via `tox`:

`uv tool run --with tox-uv tox`

## Updating README

This README is generated from a ‘literate’ Quarto [README.qmd](README.qmd) via the following command:

`tox -e quarto`

If you want to correct something, feel free to simply update `README.md`; I can reconcile the changes next time I regenerate it.
