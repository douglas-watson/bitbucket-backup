#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Bitbucket API wrapper.  Written to be somewhat like py-github:

https://github.com/dustin/py-github

"""

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
import base64
import datetime
import time
from functools import wraps

try:
    import json
except ImportError:
    import simplejson as json

__all__ = ['AuthenticationRequired', 'to_datetime', 'BitBucket']

api_toplevel = 'https://api.bitbucket.org/'
api_base = '%s2.0/' % api_toplevel


class AuthenticationRequired(Exception):
    pass


def requires_authentication(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        username = self.bb.username if hasattr(self, 'bb') else self.username
        password = self.bb.password if hasattr(self, 'bb') else self.password
        if not all((username, password)):
            raise AuthenticationRequired("%s requires authentication" % method.__name__)
        return method(self, *args, **kwargs)
    return wrapper


def smart_encode(**kwargs):
    """Urlencode's provided keyword arguments.  If any kwargs are None, it does
    not include those."""
    args = dict(kwargs)
    for k, v in args.items():
        if v is None:
            del args[k]
    if not args:
        return ''
    return urlencode(args)


def to_datetime(timestring):
    """Convert one of the bitbucket API's timestamps to a datetime object."""
    format = '%Y-%m-%d %H:%M:%S'
    timestring = timestring.split('+')[0].strip()
    return datetime.datetime(*time.strptime(timestring, format)[:7])


class BitBucket(object):

    """Main bitbucket class.  Use an instantiated version of this class
    to make calls against the REST API."""

    def __init__(self, username='', password='', oauth_key='', oauth_secret='', verbose=False):
        self.username = username
        self.password = password
        self.oauth_key = oauth_key
        self.oauth_secret = oauth_secret
        self.verbose = verbose

    def build_request(self, url, method="GET", data=None):
        if all((self.oauth_key, self.oauth_secret)):
            try:
                import oauthlib.oauth1
            except ImportError:
                import sys
                print("You must install oauthlib if you want to use oauth `pip install oauthlib`")
                sys.exit(0)
            client = oauthlib.oauth1.Client(self.oauth_key, client_secret=self.oauth_secret)
            uri, headers, body = client.sign(url)
            request = Request(url, data, headers)
            return request
        if all((self.username, self.password)):
            auth = '%s:%s' % (self.username, self.password)
            auth = {'Authorization': 'Basic %s' % (base64.b64encode(auth.encode("utf_8")).decode("utf_8").strip())}
            request = Request(url, data, auth)
            request.get_method = lambda: method
            return request
        return Request(url)

    def load_url(self, url, method="GET", data=None):
        if self.verbose:
            print("Sending request to: [{0}]".format(url))
        request = self.build_request(url, method=method, data=data)
        result = urlopen(request).read()
        if self.verbose:
            print("Response data: [{0}]".format(result))
        return result

    def user(self, username):
        return User(self, username)

    @requires_authentication
    def emails(self):
        """Returns a list of configured email addresses for the authenticated user."""
        url = api_base + 'emails/'
        return json.loads(self.load_url(url))

    @requires_authentication
    def create_repo(self, repo_data):
        url = api_base + 'repositories/'
        return json.loads(self.load_url(url, method="POST", data=urlencode(repo_data)))

    def __repr__(self):
        extra = ''
        if all((self.username, self.password)):
            extra = ' (auth: %s)' % self.username
        return '<BitBucket API%s>' % extra


class User(object):

    """API encapsulation for user related bitbucket queries."""

    def __init__(self, bb, username):
        self.bb = bb
        self.username = username

    def repositories(self):
        return self.get_repos()['values']

    def get(self):
        if self.username is None:
            url = api_base + 'user/'
        else:
            url = api_base + 'teams/%s' % self.username
        return json.loads(self.bb.load_url(url).decode('utf-8'))

    def get_repos(self):
        if self.username is None:
            raise Exception("username missing")
        else:
            url = api_base + 'repositories/%s?pagelen=100' % self.username
        return json.loads(self.bb.load_url(url).decode('utf-8'))


    def __repr__(self):
        return '<User: %s>' % self.username

