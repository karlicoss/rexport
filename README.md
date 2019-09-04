Script to export your Reddit data as json: saves, upvotes, submissions etc.


# Setting up
1. `pip3 install praw`
2. In order to use Reddit API, you need to register a [custom 'personal script' app](https://www.reddit.com/prefs/apps) and get `client_id` and `client_secret` parameters.
   See more [here](https://praw.readthedocs.io/en/latest/getting_started/authentication.html).
3. In order to access user's personal data (e.g. saved posts/comments), reddit API also requires `username` and `password` parameters.
   [(yes, your Reddit password)](https://praw.readthedocs.io/en/latest/getting_started/quick_start.html#authorized-reddit-instances).
4. It might be convenient to dump these in a file like `reddit_secrets.py`, e.g. 
```
client_id = ...
clien_secret = ...
username = ...
password = ...
```

# Using
**Recommended**: `rexport.py --secrets /path/to/secrets.py`. That way you have to type less and have control over where you're keeping your plaintext reddit password.

Alternatively, you can pass auth arguments directly, e.g. `rexport.py --username <user> --password <password> --client_id <client_id> --client_secret <client_secret>`.
However, this is prone to leaking your password in shell history.

You can also import script and call `get_json` function directory to get raw json.
