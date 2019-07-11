#!/usr/bin/env python

'''Small tool to rename items in your pocket list'''

import json
import sys
import asyncio
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

def get_article_selection(num_articles: int) -> int:
    """Prompts the user to select an article from the list
    and returns the selected list index

    Arguments:
        num_articles {int} -- Number of articles

    Returns:
        int -- Selected list index
    """
    selected_index = None
    error_message = 'Please select a valid number from the list'
    while selected_index is None:
        selected_article = input('Select an article you wish to rename: (q to quit) ')
        if selected_article is 'q':
            sys.exit(0)
        try:
            selected_index = int(selected_article) - 1
            if selected_index < 0 or selected_index >= num_articles:
                selected_index = None
                print(error_message)
        except ValueError:
            print(error_message)
    return selected_index

async def main():
    """Main function"""
    with open(CONFIG_FILE_PATH, mode='r+') as file:
        config = json.load(file)
        try:
            app = pocket.Pocket(
                config.get('POCKET', {}).get('consumer_key'),
                access_token=config.get('POCKET', {}).get('access_token'))
            await app.authorize()
        except pocket.PocketException as pocket_exception:
            print(f'Error authenticating with pocket: {pocket_exception}')
            sys.exit(1)
        except Exception as exception:
            print(f'An unknown error occured: {exception}')
            sys.exit(1)
        config['POCKET']['access_token'] = app.access_token
        # Seek to the beginning to overwrite the existing config
        # Otherwise json.dump would just append,
        # because we have read at the beginning and moved the stream position
        file.seek(0)
        json.dump(config, file, indent=4)
    while True:
        articles = await app.get_articles()
        print('Articles in list:')
        # +1 so the displayed numbmering starts at 1
        for idx, article in enumerate(articles):
            article_string = get_article_string(article)
            print(f'{idx+1}. {article_string}')
        selected_index = get_article_selection(len(articles))
        selected_article = articles[selected_index]
        article_string = get_article_string(selected_article)
        print(f'Selected article: {article_string}')
        new_name = None
        while not new_name:
            new_name = input("Enter a new name: ")
        await app.rename_article(selected_article, new_name)

if __name__ == "__main__":
    asyncio.run(main())
