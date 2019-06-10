#!/usr/bin/env python

'''Provides communication with the Pocket API'''

__author__ = 'max.nuding@icloud.com'
__version__ = '0.1'

from urllib import request, parse, error as urllib_error
import webbrowser
import json

BASE_URL = 'https://getpocket.com/v3'

REQUEST_TOKEN_URL = '/oauth/request'
AUTHORIZE_REQUEST_URL = "https://getpocket.com/auth/authorize"
AUTHORIZE_REQUEST_TOKEN = '/oauth/authorize'

REDIRECT_URI = 'https://github.com/hutattedonmyarm/pocket-rename'

# TODO: Test if access token is valid
# TODO: Type hinting
# TODO: Docstring

class Pocket:
    consumer_key = None
    access_token = None
    username = None
    request_token = None
    def __init__(self, consumer_key, access_token = None):
        self.consumer_key = consumer_key
        self.access_token = access_token
        if not self._test_access_token():
            self._get_access_token()
    
    def _get_access_token(self, redirect_uri = REDIRECT_URI):
        parameters = { 'redirect_uri' : redirect_uri }      
        try:
            resp = self._make_request(REQUEST_TOKEN_URL, parameters=parameters)  
        except urllib_error.HTTPError as e:
            if e.code == 403:
                raise InvalidConsumerKey(self.consumer_key)
            else:
                raise PocketException(f'{e.code} - {e.reason}: {e.msg}')
        except Exception as e:
            raise PocketException(e)

        response_dict = json.loads(resp.read())
        request_token = response_dict['code']
        parameters = {
            'request_token' : request_token,
            'redirect_uri' : redirect_uri
        }
        webbrowser.open(AUTHORIZE_REQUEST_URL + '?' + parse.urlencode(parameters))

        parameters = { 'code' : request_token }
        input('Please authorize me and hit enter')
        resp = self._make_request(AUTHORIZE_REQUEST_TOKEN, parameters=parameters)
        access_token_dict = json.loads(resp.read())
        self.access_token = access_token_dict['access_token']
        self.username = access_token_dict['username']
    
    def _test_access_token(self):
        if not self.access_token:
            return False
        return True

    def get_articles(self):
        # detailType simple is probably default, but the docs make no statement regarding that
        parameters = { 'detailType': 'simple' }
        resp = self._make_request('/get', parameters=parameters).read()
        return resp

    def _make_request(self, endpoint, parameters = None, headers = None):
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
        request_headers = { 'X-Accept': 'application/json' }
        request_headers.update(headers)
        data = parse.urlencode(params).encode()
        req = request.Request(url, data=data, headers=request_headers)
        resp = request.urlopen(req)
        return resp

class PocketException(Exception):
    pass

class InvalidConsumerKey(PocketException):
    consumer_key = None
    def __init__(self, consumer_key):
        self.consumer_key = consumer_key
        super().__init__(f'Invalid consumer key: "{consumer_key}"')
