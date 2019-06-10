import pocket
import json
import sys

config_file_path = 'config.json'

with open(config_file_path, mode='r+') as f:
    config = json.load(f)
    consumer_key = config['POCKET']['consumer_key']
    access_token = None
    try:
        access_token = config['POCKET']['access_token']
    except:
        pass
    try:
        app = pocket.Pocket(consumer_key, access_token=access_token)
    except pocket.PocketException as e:
        print(f'Error authenticating with pocket: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'An unknown error occured: {e}')
        sys.exit(1)
    config['POCKET']['access_token'] = app.access_token
    # Seek to the beginning to overwrite the existing config
    # Otherwise json.dump would just append, 
    # because we have read at the beginning and moved the stream position
    f.seek(0)
    json.dump(config, f, indent=4)

print(app.get_articles())