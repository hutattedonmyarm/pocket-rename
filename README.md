Overview
---

This is a small tool to rename items in your pocket list.

Pocket does not natively support this, and neither does the API. So this works by removing the selected item and re-adding it with the entered title.

**Note that this method coems with two huge caveats:**
* **If something goes wrong while re-adding the item is deleted.** Currently there is no error handling for this, but it's on my TODO list. See #4
* **Pocket ignores the provided title when it is able to parse its own, so it keep the old title.**. Currently there is no feedback about this. See #5

Requirements
---

* Python 3.7+
* Python Requests, install using `pip install requests`
* A Pocket account (duh!)
* A Pocket developer key, see the [Pocket Docs](https://getpocket.com/developer/)
* *Optionally* curses. Not included on Windows, install using `pip install windows-curses`

An interactive curses TUI is provided if curses is installed, otherwise it falls back to a more simple CLI.

Copy the sample config and enter your Pocket consumer key. Start the app with `python pocket_rename.py` or on unix based systems make it executable with `chmod +x pocket_rename.py` and then run it usinng `./pocket_rename.py`