#!/usr/bin/env python

'''Small tool to rename items in your pocket list'''

import json
import sys
import pocket


CONFIG_FILE_PATH = 'config.json'

if __name__ == "__main__":
    with open(CONFIG_FILE_PATH, mode='r+') as f:
        CONFIG = json.load(f)
        try:
            APP = pocket.Pocket(
                CONFIG.get('POCKET', {}).get('consumer_key'),
                access_token=CONFIG.get('POCKET', {}).get('access_token'))
        except pocket.PocketException as pocket_exception:
            print(f'Error authenticating with pocket: {pocket_exception}')
            sys.exit(1)
        except Exception as exception:
            print(f'An unknown error occured: {exception}')
            sys.exit(1)
        CONFIG['POCKET']['access_token'] = APP.access_token
        # Seek to the beginning to overwrite the existing config
        # Otherwise json.dump would just append,
        # because we have read at the beginning and moved the stream position
        f.seek(0)
        json.dump(CONFIG, f, indent=4)
    print(APP.get_articles())
