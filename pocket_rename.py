#!/usr/bin/env python

'''Small tool to rename items in your pocket list'''

CURSES_AVAILABLE = True

import json
import sys
import asyncio
from typing import List
try:
    import curses
except Exception:
    CURSES_AVAILABLE = False
    print('Courses is not installed, switchign to CLI', file=sys.stderr)
import pocket

Articles = List[pocket.Article]

CONFIG_FILE_PATH = 'config.json'

def cli_get_article_selection(num_articles: int) -> int:
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

async def tui_print_loading(screen, message: str = 'Loading'):
    """Prints a loaging message on the TUI

    Arguments:
        screen {ncurses.window} -- The window in which
            the loading message should be printed

    Keyword Arguments:
        message {str} -- The loading message (default: {'Loading'})
    """
    curses.curs_set(0)
    num_dots = 2
    while True:
        dots = '.' * num_dots
        screen.move(0, 0)
        screen.clrtoeol()
        screen.addstr(0, 0, f'{message}{dots}')
        screen.refresh()
        await asyncio.sleep(0.5)
        num_dots = (num_dots+1) % 4

async def cli(app: pocket.Pocket):
    """Starts the regular, non-curses CLI

    Arguments:
        app {pocket.Pocket} -- The pocket instance
    """
    while True:
        articles = await app.get_articles()
        print('Articles in list:')
        # +1 so the displayed numbmering starts at 1
        for idx, article in enumerate(articles):
            article_string = str(article)
            print(f'{idx+1}. {article_string}')
        selected_index = cli_get_article_selection(len(articles))
        selected_article = articles[selected_index]
        article_string = str(selected_article)
        print(f'Selected article: {article_string}')
        new_name = None
        while not new_name:
            new_name = input("Enter a new name: ")
        await app.rename_article(selected_article, new_name)

def tui_draw_article_list(
        pad,
        articles: Articles,
        num_rows: int,
        num_cols: int,
        col: int = 2):
    """Draws the list of articles using curses

    Arguments:
        pad {ncurses.window} -- The curses pad to draw the list in
        articles {List[pocket.Article]} -- List of articles to display
        num_rows {int} -- Height of the ncurses window
        num_cols {int} -- Width of the ncurses window

    Keyword Arguments:
        col {int} -- Column to start the list in (default: {2})
    """
    pad.addstr(0, 0, 'Articles in list:', curses.A_BOLD)
    pad.addstr(1, 0, '>')
    pad.move(1, 0)
    for idx, article in enumerate(articles):
        pad.addstr(idx+1, col, article.get_title())
        pad.addstr(': ')
        pad.addstr(article.resolved_url, curses.A_UNDERLINE)
    pad.refresh(0, 0, 0, 0, num_rows-1, num_cols-1)

def tui_get_new_name(screen, old_name_str: str) -> str:
    """Prompts the user to enter a new name and reads it using ncurses

    Arguments:
        screen {ncurses.window} -- The curses window to draw the prompt in
        old_name_str {str} -- Old name of the article

    Returns:
        str -- The entered new name
    """
    _, num_cols = screen.getmaxyx()
    lbl_old_name = 'Old name: '
    max_str_len = num_cols - len(lbl_old_name)-1
    if len(old_name_str) > max_str_len:
        old_name_str = old_name_str[:max_str_len-3] + '...'
    screen.addstr(lbl_old_name, curses.A_BOLD)
    screen.addstr(f'{old_name_str}\n')
    screen.addstr('Enter a new name: ')
    curses.echo()
    curses.curs_set(1)
    screen.refresh()
    new_name = screen.getstr(1, 18)
    curses.curs_set(0)
    return new_name

async def tui(screen, app: pocket.Pocket):
    """Starts a curses TUI

    Arguments:
        screen {ncurses.window} -- The ncurses window to start the TUI in
        app {pocket.Pocket} -- The pocket instance
    """
    col = 2
    row = 1

    # Display the loading animation while loading the articles
    loading_tui = asyncio.create_task(
        tui_print_loading(screen, 'Loading articles'))
    article_task = asyncio.create_task(
        app.get_articles())
    articles = await article_task
    # Stop loading animation
    loading_tui.cancel()

    # Create pad and draw article list
    num_rows, num_cols = screen.getmaxyx()
    num_articles = len(articles)
    col_widths = (len(str(a)) for a in articles)
    pad = curses.newpad(num_articles+1, max(col_widths)+2)
    pad.keypad(1)
    screen.move(0, 0)
    screen.clrtoeol()
    tui_draw_article_list(pad, articles, num_rows, num_cols, col)
    # Handle selection
    pad_row = 0
    # Some codes are not available on all platforms
    curses_functions = dir(curses)
    # Powershell is reporting the wrong key code
    down_keys = (curses.KEY_DOWN, curses.KEY_C2 if 'KEY_C2' in curses_functions else None)
    up_keys = (curses.KEY_UP, curses.KEY_A2 if 'KEY_A2' in curses_functions else None)
    left_keys = (curses.KEY_LEFT, curses.KEY_B1 if 'KEY_B1' in curses_functions else None)
    right_keys = (curses.KEY_RIGHT, curses.KEY_B3 if 'KEY_B3' in curses_functions else None)
    enter_keys = (curses.PADENTER if 'PADENTER' in curses_functions else None, curses.KEY_ENTER, 13, 10)
    while True:
        key = pad.getch()
        if key in down_keys and row < num_articles:
            pad.addstr(row, 0, ' ')
            row += 1
            pad.addstr(row, 0, '>')
            row_in_window = row-pad_row
            if row_in_window == num_rows and row <= num_articles:
                pad_row += 1
            pad.refresh(pad_row, 0, 0, 0, num_rows-1, num_cols-1)
        elif key in up_keys and row > 1:
            pad.addstr(row, 0, ' ')
            row -= 1
            pad.addstr(row, 0, '>')
            row_in_window = row-pad_row
            if row_in_window == 0 and row > 0:
                pad_row -= 1
            pad.refresh(pad_row, 0, 0, 0, num_rows-1, num_cols-1)
        elif key in right_keys:
            pass
        elif key in left_keys:
            #TODO Scroll for long lines
            pass
        elif key == ord('q'):
            #TODO Scroll for long lines
            return
        elif key in enter_keys:
            # Get new name from user
            pad.clear()
            pad_row = 0
            pad.refresh(pad_row, 0, 0, 0, num_rows-1, num_cols-1)
            screen.refresh()
            try:
                new_name = tui_get_new_name(screen, str(articles[row-1])).decode('utf-8')
                screen.clear()
                screen.refresh()
                # Rename article
                loading_tui = asyncio.create_task(
                    tui_print_loading(screen, 'Renaming article'))
                rename_task = asyncio.create_task(
                    app.rename_article(articles[row-1], new_name))
                await rename_task
                # Reload and display new list
                article_task = asyncio.create_task(
                    app.get_articles())
                articles = await article_task
                loading_tui.cancel()
            except KeyboardInterrupt:
                pass
            screen.clear()
            screen.refresh()
            row = 1
            tui_draw_article_list(pad, articles, num_rows, num_cols, col)
        else:
            print(f'Unknown key: {key} - {curses.keyname(key)}', file=sys.stderr)

async def tui_init(app):
    """Inits the curses library and starts the interface

    Arguments:
        app {pocket.Pocket} -- The pocket instance
    """
    screen = curses.initscr()
    curses.start_color()
    curses.raw()
    curses.cbreak()
    curses.noecho()
    try:
        await tui(screen, app)
    except Exception as error:
        print(error)
    finally:
        screen.clear()
        screen.refresh()
        screen.keypad(0)
        curses.noraw()
        curses.nocbreak()   # Turn off cbreak mode
        curses.echo()       # Turn echo back on
        curses.endwin()

async def main():
    """Main function"""
    ui = None
    app = None
    with open(CONFIG_FILE_PATH, mode='r+') as file:
        config = json.load(file)
        try:
            app = pocket.Pocket(
                config.get('POCKET', {}).get('consumer_key'),
                access_token=config.get('POCKET', {}).get('access_token'))
            await app.authorize()
            use_tui = config.get('APP', {}).get('use_tui', True)
            ui = tui_init if CURSES_AVAILABLE and use_tui else cli
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
    
    await ui(app)

if __name__ == "__main__":
    asyncio.run(main())
