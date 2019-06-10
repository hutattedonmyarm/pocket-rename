#!/usr/bin/env python

'''Provides communication with the Pocket API'''

__author__ = 'max.nuding@icloud.com'
__version__ = '0.1'

from urllib import request, parse, error as urllib_error
import webbrowser
import json

BASE_URL = 'https://getpocket.com/v3'

REQUEST_TOKEN_URL = BASE_URL+'/oauth/request'
AUTHORIZE_REQUEST_URL = "https://getpocket.com/auth/authorize"
AUTHORIZE_REQUEST_TOKEN = BASE_URL+'/oauth/authorize'

REDIRECT_URI = 'https://github.com/hutattedonmyarm/pocket-rename'

# TODO: Test if access token is valid
# TODO: Some kind of _make_request()
# TODO: Type hinting

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
        parameters = {
            'consumer_key' : self.consumer_key,
            'redirect_uri' : redirect_uri 
        }
        
        headers = { 'X-Accept': 'application/json' }
        data = parse.urlencode(parameters).encode()
        req =  request.Request(REQUEST_TOKEN_URL, data=data, headers=headers) # this will make the method "POST"
        try:
            resp = request.urlopen(req)
            
        except urllib_error.HTTPError as e:
            if e.code == 403:
                raise InvalidConsumerKey(self.consumer_key)
        except Exception as e:
            raise PocketException(e)

        response_dict = json.loads(resp.read())
        request_token = response_dict['code']

        parameters = {
            'request_token' : request_token,
            'redirect_uri' : redirect_uri
        }

        webbrowser.open(AUTHORIZE_REQUEST_URL + '?' + parse.urlencode(parameters))

        parameters = {
            'consumer_key' : self.consumer_key,
            'code' : request_token
        }

        input('Please authorize me and hit enter')

        data = parse.urlencode(parameters).encode()
        req = request.Request(AUTHORIZE_REQUEST_TOKEN, data=data, headers=headers)
        resp = request.urlopen(req)

        access_token_dict = json.loads(resp.read())
        self.access_token = access_token_dict['access_token']
        self.username = access_token_dict['username']
    
    def _test_access_token(self):
        if not self.access_token:
            return False
        return True

    def get_articles(self):
        url = BASE_URL+'/get'
        headers = { 'X-Accept': 'application/json' }
        parameters = {
            'access_token' : self.access_token,
            'consumer_key' : self.consumer_key,
            'detailType': 'simple '
        }
        data = parse.urlencode(parameters).encode()
        req = request.Request(url, data=data, headers=headers)
        resp = request.urlopen(req).read()
        return resp

class PocketException(Exception):
    pass

class InvalidConsumerKey(PocketException):
    consumer_key = None
    def __init__(self, consumer_key):
        self.consumer_key = consumer_key
        super().__init__(f'Invalid consumer key: "{consumer_key}"')
