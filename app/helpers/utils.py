import json
import logging
import os
import sys
import time
from uuid import uuid4

import jmespath
from jmespath import functions
import requests
import yaml


HELPERS_DIR = os.path.abspath(os.path.dirname(__file__))
if HELPERS_DIR not in sys.path:
    sys.path.append(HELPERS_DIR)


LOGGER = logging.getLogger('helpers.utils')


def now():
    return int(round(time.time()))


def call_rest_api(caller, method, url, payload=None, convert_payload=None,
                  headers=None, params=None, response=None, default=None):
    method_map = {
        'get': requests.get,
        'post': requests.post
    }

    if method not in method_map:
        LOGGER.error(f'Invalid method from {caller} to {url}:\n{method}')
        return None

    request_args = {}
    if payload:
        if convert_payload and convert_payload in ['json', yaml]:
            if convert_payload == 'json':
                payload = json.dumps(payload)
            elif convert_payload == 'yaml':
                payload = yaml.safe_dump(payload)

        request_args['data'] = payload

    if headers:
        request_args['headers'] = headers

    if params:
        request_args['params'] = params

    try:
        api_call = method_map[method](url, **request_args)
        if str(api_call.status_code).startswith('2'):
            res = api_call.text
            if response:
                if response == 'json':
                    res = json.loads(res)
                elif response == 'yaml':
                    res = yaml.safe_load(res)

            return res

        else:
            LOGGER.error(f'{api_call.status_code}: {api_call.text}')
            return default
    except Exception as e:
        LOGGER.error(str(e))
        return default


class CustomFunctions(functions.Functions):
    @functions.signature(
        {'types': ['object']}, {'types': ['string']}, {'types': ['string']})
    def _func_key_val_to_fields(self, data, key_field, val_field):
        return [
            {key_field: key, val_field: val}
            for key, val in data.items()
        ]

    @functions.signature({'types': ['string', 'null']})
    def _func_string_or_null(self, data):
        if isinstance(data, str):
            if data.strip() in ['None', 'null']:
                data = None

        return data

    @functions.signature(
        {'types': ['boolean', 'array', 'object', 'null', 'string',
                   'number', 'expref']},
        {'types': ['boolean', 'array', 'object', 'null', 'string',
                   'number', 'expref']},
        {'types': ['boolean']})
    def _func_val_or_val(self, val1, val2, condition):
        if condition:
            return val1
        else:
            return val2

    @functions.signature({'types': ['string']})
    def _func_lower(self, value):
        return value.lower()

    @functions.signature(
        {'types': ['string']},
        {'types': ['string']},
        {'types': ['number']})
    def _func_split_items(self, value, _split, count):
        if count < 1:
            return value

        items = [v.strip() for v in value.split(_split)]
        if len(items) <= count:
            return value

        return ' '.join(items[:count])

    @functions.signature({'types': ['number']}, {'types': ['number']})
    def _func_remainder(self, dividend, divisor):
        return int(dividend % divisor)

    @functions.signature()
    def _func_uuid(self):
        return str(uuid4())


def jsearch(transform, data):
    return jmespath.search(
        transform,
        data,
        options=jmespath.Options(custom_functions=CustomFunctions())
    )
