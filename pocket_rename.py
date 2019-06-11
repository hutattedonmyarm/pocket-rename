#!/usr/bin/env python

'''Small tool to rename items in your pocket list'''

import json
import sys
import pocket

CONFIG_FILE_PATH = 'config.json'

def get_article_string(item: pocket.Article) -> str:
    """Formats the title and URL of an article

    Arguments:
        item {pocket.Article} -- The article

    Returns:
        str -- The formatted article display string
    """
    title = ''
    if item.resolved_title:
        title = f'{item.resolved_title}: '
    elif item.given_title:
        title = f'{item.given_title}: '
    return f'{title}{item.resolved_url}'

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
    while True:
        ARTICLES = APP.get_articles()
        print('Articles in list:')
        # +1 so the displayed numbmering starts at 1
        for idx, article in enumerate(ARTICLES):
            ARTICLE_STRING = get_article_string(article)
            print(f'{idx+1}. {ARTICLE_STRING}')
        SELECTED_ARTICLE = input('Select an article you wish to rename: ')
        SELECTED_INDEX = None
        while SELECTED_INDEX is None:
            ERROR_MESSAGE = 'Please select a valid number from the list'
            try:
                SELECTED_INDEX = int(SELECTED_ARTICLE) - 1
                if SELECTED_INDEX < 0 or SELECTED_INDEX >= len(ARTICLES):
                    print(ERROR_MESSAGE)
            except ValueError as error:
                print(ERROR_MESSAGE)
        SELECTED_ARTICLE = ARTICLES[SELECTED_INDEX]
        ARTICLE_STRING = get_article_string(SELECTED_ARTICLE)
        print(f'Selected article: {ARTICLE_STRING}')
        NEW_NAME = None
        while not NEW_NAME:
            NEW_NAME = input("Enter a new name: ")
        APP.rename_article(SELECTED_ARTICLE, NEW_NAME)
