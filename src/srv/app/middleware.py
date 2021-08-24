import itertools
import functools


class ResponseHeaderMiddleware:

    def __init__(self, app, *headers_pairs, **headers_map):
        self.app = app
        self.response_headers = tuple(itertools.chain(headers_pairs, headers_map.items()))

    def __call__(self, environ, start_response):
        return self.app(environ, functools.partial(self.start_response_with_headers, start_response))

    def start_response_with_headers(self, start_response, status, response_headers, exc_info=None):
        if not response_headers:
            response_headers = []

        response_headers.extend(self.response_headers)

        return start_response(status, response_headers, exc_info)
