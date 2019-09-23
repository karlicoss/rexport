Export your personal Reddit data: saves, upvotes, submissions etc. as JSON.

# Setting up
1. `pip3 install -r requirements.txt`
2. In use the API, you need to register a [custom 'personal script' app](https://www.reddit.com/prefs/apps) and get `client_id` and `client_secret` parameters.
   See more [here](https://praw.readthedocs.io/en/latest/getting_started/authentication.html).
3. To access user's personal data (e.g. saved posts/comments), reddit API also requires `username` and `password` parameters.
   [(yes, your Reddit password)](https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#authorized-reddit-instances).
4. It might be convenient to dump these in a file, e.g. `secrets.py`:
```
client_id = ...
client_secret = ...
username = ...
password = ...
```

# Using
**Recommended**: `./export --secrets /path/to/secrets.py`. That way you have to type less and have control over where you're keeping your plaintext tokens/passwords.

Alternatively, you can pass auth arguments directly, e.g. `./export --username <user> --password <password> --client_id <client_id> --client_secret <client_secret>`.
However, this is prone to leaking your keys in shell history.

You can also import script and call `get_json` function directory to get raw json.

# Limitations
**WARNING**: reddit API [limits your queries to 1000 entries](https://www.reddit.com/r/redditdev/comments/61z088/sample_more_than_1000_submissions_within_subreddit).

It's **highly** recommended to back up regularly and keep old versions. Easy way to achieve it is command like this: `./export --secrets secrets.py >"export-$(date -I).json"`.

Check out these links if you're interested in getting older data that's inaccessible by API:

* [here](https://www.reddit.com/r/DataHoarder/comments/d0hjs7/reddit_takeout_export_your_account_data_as_json/ezbbcxe)
* [your data is there, there are just no resources to serve it](https://www.reddit.com/r/ideasfortheadmins/wiki/faq#wiki_can_we_have_a_way_to_download_our_entire_history_even_though_reddit_cuts_off_at_a_certain_point)
* perhaps you can request all of your data under [GDPR](https://www.reddit.com/r/DataHoarder/comments/d0hjs7/reddit_takeout_export_your_account_data_as_json/eza0nsx)? I haven't tried that personally though.
* [pushshift](https://pushshift.io) can potentially help you retrieve old data


# Example output
See [./example-output.json](example-output.json), it's got some example data you might find in your data export. I've cleaned it up a bit as it's got lots of different fields many of which are probably not relevant.

However, this is pretty API dependent and changes all the time, so better check with [Reddit API](https://www.reddit.com/dev/api) if you are looking to something specific.
