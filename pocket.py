#!/usr/bin/env python

"""Provides communication with the Pocket API"""

__author__ = 'max.nuding@icloud.com'
__version__ = '0.1'

from urllib import request, parse, error as urllib_error
from typing import List, Dict, Tuple
import dataclasses
import webbrowser
import json

BASE_URL = 'https://getpocket.com/v3'

REQUEST_TOKEN_URL = '/oauth/request'
AUTHORIZE_REQUEST_URL = 'https://getpocket.com/auth/authorize'
AUTHORIZE_REQUEST_TOKEN = '/oauth/authorize'

REDIRECT_URI = 'https://github.com/hutattedonmyarm/pocket-rename'

Parameter = Dict[str, str]

# TODO: Test if access token is valid

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

class Pocket:
    """Provides access to the Pocket API"""
    consumer_key = None
    access_token = None
    username = None
    request_token = None
    def __init__(self, consumer_key, access_token=None):
        self.consumer_key = consumer_key
        self.access_token = access_token
        if not self._test_access_token():
            self._get_access_token()

    def _get_access_token(self, redirect_uri: str = REDIRECT_URI) -> None:
        parameters = {'redirect_uri' : redirect_uri}
        try:
            resp = self._make_request(REQUEST_TOKEN_URL, parameters=parameters)
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
        resp = self._make_request(AUTHORIZE_REQUEST_TOKEN, parameters=parameters)
        access_token_dict = json.loads(resp.read())
        self.access_token = access_token_dict['access_token']
        self.username = access_token_dict['username']

    def _test_access_token(self) -> bool:
        if not self.access_token:
            return False
        return True

    def get_articles(self, state: str = 'unread') -> List[Article]:
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
        resp = self._make_request('/get', parameters=parameters).read()
        resp = json.loads(resp)['list']
        articles = [Article(item_id,
                            a['given_url'],
                            a['resolved_url'],
                            a['given_title'],
                            a['resolved_title'],
                            [*a.get('tags', {})],
                            a['time_added']) for item_id, a in resp.items()]
        return articles

    def rename_article(self, article: Article, new_name: str, clean_url=True) -> Article:
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
        pass

    def add_tags(self, article: Article, tags: List[str]) -> Article:
        """Adds tags to an article
        Arguments:
            article {Article} -- The article
            tags {List[str]} -- List of tags to add
        """
        resp = self._send_action('tags_add', article, ('tags', ','.join(tags)))
        return json.loads(resp.read())

    def _send_action(self, action: str, article: Article, action_value: Tuple[str, str]):
        params = {
            'actions':
            [{
                'action': action,
                'item_id': article.item_id,
                action_value[0]: action_value[1]
            }]
        }
        return self._make_request('/send', params)

    def _make_request(self,
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
        req = request.Request(url, data=data, headers=request_headers)
        resp = request.urlopen(req)
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
