# SPDX-FileCopyrightText: 2024 Martin J. Fiedler <keyj@emphy.de>
# SPDX-License-Identifier: MIT

__all__ = ['WebRequest']

import json
import logging
import time
import urllib.parse
import urllib.request

###############################################################################
# MARK: WebRequest

class WebRequest:
    "convenience wrapper around urllib.request"
    def __init__(self, url: str, get_data: dict = {}, post_data: dict = {}, json_data = None, headers: dict = {}, timeout: float = 0.1, quiet: bool = False):
        """
        Send a web request and read the response, with timeout and automatic
        JSON en-/decoding.
        - url:       The URL to request
        - get_data:  dictionary with URL parameters
        - post_data: dictionary with POST parameters in classic url-encoded format
        - json_data: JSON data to send (post_data is ignored then)
        - headers:   dictionary of additional headers to send
        - timeout:   timeout for the request, in seconds
        - quiet:     set to True to avoid logging the request

        The request is executed immediately and the following member variables
        are provided:
        - request_url:      full request URL including URL parameters
        - request_method:   "POST" or "GET"
        - request_headers:  dictionary with all headers specified to urllib
        - request_data:     POST data (bytes, not str)
        - response_status:  response status code (HTTP code)
        - response_headers: received response headers
        - response_data:    response data (bytes, not str)
        - response_json:    decoded response JSON (assuming UTF-8 character set),
                            or None if there was an error or malformed JSON
        """
        log = logging.getLogger("WebRequest")
        self.request_headers = dict(headers)
        if json_data:
            self.request_headers["Content-Type"] = "application/json"
            self.request_data = json.dumps(json_data).encode('utf-8')
        elif post_data:
            self.request_headers["Content-Type"] = "application/x-www-form-urlencoded"
            self.request_data = urllib.parse.urlencode(post_data).encode('utf-8')
        else:
            self.request_data = None
        if get_data:
            url += ("&" if ("?" in url) else "?") + urllib.parse.urlencode(get_data)
        self.request_url = url
        req = urllib.request.Request(self.request_url, data=self.request_data, headers=self.request_headers)
        try:
            self.request_method = req.method
        except AttributeError:
            self.request_method = "POST" if self.request_data else "GET"
        if not quiet:
            if self.request_data:
                log.info("%s %s [+%d bytes of data]", self.request_method, self.request_url, len(self.request_data))
            else:
                log.info("%s %s", self.request_method, self.request_url)
        self.response_status = None
        self.response_headers = {}
        self.response_data = bytes()
        self.response_json = None
        if timeout:
            timeout += time.time()
        try:
            with urllib.request.urlopen(req) as f:
                self.response_status = f.status
                self.response_headers = f.headers
                while time.time() < timeout:
                    block = f.read(4096)
                    if not block: break
                    self.response_data += block
        except EnvironmentError as e:
            log.error("%s request to %s failed - %s", self.request_method, self.request_url, str(e))
        try:
            self.response_json = json.loads(self.response_data.decode('utf-8', 'replace'))
        except json.JSONDecodeError:
            pass
