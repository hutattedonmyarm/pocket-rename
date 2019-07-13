#!/usr/bin/env python

"""Provides communication with the Pocket API"""

__author__ = 'max.nuding@icloud.com'
__version__ = '0.1'

from urllib import request, parse, error as urllib_error
from typing import List, Dict
import dataclasses
import webbrowser
import json
import asyncio
import requests

BASE_URL = 'https://getpocket.com/v3'

REQUEST_TOKEN_URL = '/oauth/request'
AUTHORIZE_REQUEST_URL = 'https://getpocket.com/auth/authorize'
AUTHORIZE_REQUEST_TOKEN = '/oauth/authorize'

REDIRECT_URI = 'https://github.com/hutattedonmyarm/pocket-rename'

Parameter = Dict[str, str]
Bytes = List[bytes]

@dataclasses.dataclass
class Article:
    """A Pocket Article"""
    item_id: str
    given_url: str
    resolved_url: str
    given_title: str
    resolved_title: str
    tags: List[str]
    time_added: str

    def get_title(self):
        title = '<Unnamed>'
        if self.resolved_title:
            title =  self.resolved_title
        elif self.given_title:
            title = self.given_title
        return title
    def __str__(self):
        return f'{self.get_title()}: {self.resolved_url}'

class Pocket:
    """Provides access to the Pocket API"""
    consumer_key = None
    access_token = None
    username = None
    request_token = None
    def __init__(self, consumer_key, access_token=None):
        self.consumer_key = consumer_key
        self.access_token = access_token

    async def authorize(self):
        """Authorizes with Pocket"""
        token_valid = await self._test_access_token()
        if not token_valid:
            await self._get_access_token()

    async def _get_access_token(self, redirect_uri: str = REDIRECT_URI) -> None:
        """Fetches an access token from the Pocket API

        Keyword Arguments:
            redirect_uri {str} -- Redirect URI to be called by Pocket (default: {REDIRECT_URI})

        Raises:
            InvalidConsumerKey: App Consumer Key in invalid
            PocketException: Other Pocket exceptions
        """
        parameters = {'redirect_uri' : redirect_uri}
        try:
            resp = (await self._make_request(REQUEST_TOKEN_URL, parameters=parameters)).text
        except urllib_error.HTTPError as http_exception:
            if http_exception.code == 403:
                raise InvalidConsumerKey(self.consumer_key)
            else:
                raise PocketException(
                    f'{http_exception.code} - {http_exception.reason}: {http_exception.msg}')
        except Exception as exception:
            raise PocketException(exception)

        response_dict = json.loads(resp.read())
        request_token = response_dict['code']
        parameters = {
            'request_token' : request_token,
            'redirect_uri' : redirect_uri
        }
        webbrowser.open(AUTHORIZE_REQUEST_URL + '?' + parse.urlencode(parameters))

        parameters = {'code' : request_token}
        input('Please authorize me and hit enter')
        resp = (await self._make_request(AUTHORIZE_REQUEST_TOKEN, parameters=parameters)).text
        access_token_dict = json.loads(resp.read())
        self.access_token = access_token_dict['access_token']
        self.username = access_token_dict['username']

    async def _test_access_token(self) -> bool:
        """Checks if the access token is valid

        Returns:
            bool -- True if valid, False if not
        """
        if not self.access_token:
            return False
        parameters = {
            'count': 1
        }
        try:
            _ = await self._make_request('/get', parameters=parameters)
        except InvalidAccessToken:
            return False
        return True

    @staticmethod
    def _async_post_wrapper(url: str, data: Bytes, headers: Parameter) -> requests.Response:
        """Wraps a POST request to take only positional arguments

        Arguments:
            url {str} -- URL to POST to
            data {Bytes} -- UTF-8 encoded json with the body
            headers {Parameter} -- Header dictionary

        Returns:
            requests.Response -- Server response
        """
        return requests.post(url, data=data, headers=headers)

    @staticmethod
    def _parse_article(item_id: str, article_data: Dict[str, any]) -> Article:
        title = article_data.get('resolved_title')
        if not title:
            title = article_data.get('title')

        return Article(item_id,
                       article_data['given_url'],
                       article_data['resolved_url'],
                       article_data.get('given_title'),
                       title,
                       [*article_data.get('tags', {})],
                       article_data.get('time_added'))

    async def get_articles(self, state: str = 'unread') -> List[Article]:
        """Fetches all unread items from pocket

        Keyword Arguments:
            state {str} -- filter items by state:
                'unread', 'archive', or 'all' (default: {'unread'})

        Returns:
            List[Article] -- A list of pocket articles
        """
        # detailType simple is probably default, but the docs make no statement regarding that
        parameters = {
            'detailType': 'complete',
            'state': state
        }
        resp = (await self._make_request('/get', parameters=parameters)).text
        resp = json.loads(resp)['list']
        articles = [self._parse_article(item_id, a) for item_id, a in resp.items()]
        return articles

    async def rename_article(self, article: Article, new_name: str, clean_url=True) -> Article:
        """Renames a Pocket article by removing and readding it,
        while keeping the original tags and the timemstamp

        Arguments:
            article {Article} -- The article to be renamed
            new_name {str} -- The new title of the article

        Keyword Arguments:
            clean_url {bool} -- Replace the original url with Pocket's
            resolved url (default: {True})

        Returns:
            Article -- The new article
        """
        tags = article.tags
        url = article.resolved_url if clean_url else article.given_url
        time_added = article.time_added
        await self.remove_item(article)
        return await self.add_item(url, new_name, tags, time_added)


    async def add_tags(self, article: Article, tags: List[str]) -> bool:
        """Adds tags to an article
        Arguments:
            article {Article} -- The article
            tags {List[str]} -- List of tags to add
        Returns:
            bool -- Success
        """
        action = {
            'item_id': article.item_id,
            'tags': ','.join(tags)
        }
        return (await self._send_action('tags_add', action))[0]

    async def remove_item(self, article: Article) -> bool:
        """Removes an article from the list
        Arguments:
            article {Article} -- The article to remove
        Returns:
            bool -- Success
        """
        action = {'item_id': article.item_id}
        return (await self._send_action('delete', action))[0]

    async def add_item(self,
                       url: str,
                       title: str = None,
                       tags: List[str] = None,
                       time_added: str = None) -> Article:
        """Adds an item to the list

        Arguments:
            url {str} -- The URL of the item

        Keyword Arguments:
            title {str} -- The title of the new item.
            Will be ignored if Pocket is able to parse the title itself (default: {None})
            tags {List[str]} -- A list of tags for the item (default: {None})
            time_added {str} -- Timestamp when this item was added (default: {None})

        Returns:
            Article -- The newly added Pocket article
        """
        params = {'url': url}
        if title:
            params['title'] = title
        if tags:
            params['tags'] = ','.join(tags)
        if time_added:
            params['time'] = time_added
            # Adding with a timestamp is only possible using the /send endpoint,
            # and not the /add endpoint
            return await self._add_item_timestamp(params)
        # The item returned by the /add endpoint is different from the regular one
        # Might be better to go agains Pocket's recommendation and also use the /send endpoint here
        resp = await self._make_request('/add', params)
        item = json.loads(resp.text)['item']
        return self._parse_article(item['item_id'], item)

    async def _add_item_timestamp(self, params: Dict[str, str]) -> Article:
        """Adds an item with a timestamp to the list

        Arguments:
            params {Dict[str, str]} -- Item paramemters (url, title, time)

        Returns:
            Article -- The added item
        """
        new_item = (await self._send_action('add', params))[0]
        article = self._parse_article(new_item['item_id'], new_item)
        return article

    async def _send_action(self,
                           action_name: str,
                           action: Dict[str, str] = None) -> List[bool]:
        action['action'] = action_name
        params = {'actions': [action]}
        resp = await self._make_request('/send', params)
        resp_text = resp.text
        return json.loads(resp_text)['action_results']

    async def _make_request(self,
                            endpoint: str,
                            parameters: Parameter = None,
                            headers: Parameter = None) -> request.Request:
        # Handles relative and absolute (e.g. for authentication) endpoints
        url = BASE_URL+endpoint if endpoint.startswith('/') else endpoint
        # Using empty dictionaries as default values causes all sorts of troubles in python
        # So 'None' is used with an initialization to an empty dict
        parameters = {} if parameters is None else parameters
        headers = {} if headers is None else headers
        params = {
            'access_token' : self.access_token,
            'consumer_key' : self.consumer_key
        }
        params.update(parameters)
        request_headers = {
            'X-Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        request_headers.update(headers)
        data = json.dumps(params).encode('utf-8')
        try:
            # Requests is blocking, so it's run like that
            loop = asyncio.get_event_loop()
            # run_in_executor doesn't take keyword arguments,
            # => run through a wrapper which takes them positionally
            resp = await loop.run_in_executor(
                None,
                self._async_post_wrapper,
                url,
                data,
                request_headers)
        except urllib_error.HTTPError as http_exception:
            if http_exception.code == 401:
                raise InvalidAccessToken(self.access_token)
            else:
                raise PocketException(
                    f'{http_exception.code} - {http_exception.reason}: {http_exception.msg}')
        return resp

class DataClassJSONEncoder(json.JSONEncoder):
    """JSON Encoder to encode dataclasses"""
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

class PocketException(Exception):
    """General Pocket Exception"""

class InvalidConsumerKey(PocketException):
    """Invalid Consumer Key Exception"""
    consumer_key = None
    def __init__(self, consumer_key):
        self.consumer_key = consumer_key
        super().__init__(f'Invalid consumer key: "{consumer_key}"')

class InvalidAccessToken(PocketException):
    """Invalid Access Token Exception"""
    access_token = None
    def __init__(self, access_token):
        self.access_token = access_token
        super().__init__(f'The provided "{access_token}" is invalid')
