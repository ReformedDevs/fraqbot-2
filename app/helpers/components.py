import json
import logging

import redis
import requests

from helpers.utils import jsearch


logger = logging.getLogger('components')


def redis_connect(host, port):
    conn = redis.StrictRedis(
        host, port, charset="utf-8", decode_responses=True)

    return conn


class Message(object):
    def __init__(self, obj):
        self.type = obj.get('type')
        self.channel = obj.get('channel')
        self.load_data(obj.get('data'))

    def load_data(self, data):
        self. data = {}

        if isinstance(data, str):
            try:
                self.data = json.loads(data)
            except Exception as e:
                logger.error(f'Error loading message data: {e}')

    def get_reply_obj(self):
        srch = ('{channel_id: channel_id,'
                'From: `""`,'
                'Content: `null`,'
                'Metadata: {'
                'Source: `null`,'
                'Dest: Metadata.Source,'
                'ID: uuid()}}')
        return jsearch(srch, self.data)


class DiscordApi(object):
    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': f'Bot {token}',
            'Content-Type': 'application/json'
        }
        self.base = 'https://discord.com/api'
        self.channels_by_id = {}

    def get_channel_by_id(self, id):
        if id in self.channels_by_id:
            return self.channels_by_id[id]

        url = f'{self.base}/channels/{id}'
        resp = requests.get(url, headers=self.headers)

        if resp.status_code == 200:
            channel = resp.json()
            self.channels_by_id[id] = channel

            return channel
        else:
            logger.error(
                f'Error getting channel: {resp.status_code}: {resp.content}')

            return None

    def join_thread(self, channel):
        url = f'{self.base}/channels/{channel}/thread-members/@me'
        resp = requests.put(url, headers=self.headers)

        if resp.status_code == 204:
            return True
        else:
            logger.error(
                f'Error joining thread: {resp.status_code}: {resp.content}')

            return None

    def create_thread(self, message, name=None):
        url = (f'{self.base}/channels/{message.data["channel_id"]}'
               f'/messages/{message.data["id"]}/threads')
        payload = {
            'name': name if name else message.data['content']
        }
        resp = requests.post(
            url, headers=self.headers, data=json.dumps(payload))

        if resp.status_code == 201:
            thread = resp.json()
            self.join_thread(thread['id'])

            return thread
        else:
            logger.error(
                f'Error creating thread: {resp.status_code}: {resp.content}')

            return None

    def create_message(self, channel, content):
        url = f'{self.base}/channels/{channel}/messages'
        payload = {'content': content}
        resp = requests.post(
            url, headers=self.headers, data=json.dumps(payload))

        if resp.status_code == 201:
            return resp.json()
        else:
            logger.error(
                f'Error creating message: {resp.status_code}: {resp.content}')

            return None


class Fraqbot(object):
    def __init__(self, conn, cfg, token=None):
        self.conn = conn
        self.name = cfg.pop('name', 'Fraqbot')
        self.filter = cfg.pop(
            'filter', {'type': 'message', 'search': '`true`'})
        self.cfg = cfg

        if token:
            self.api = DiscordApi(token)

    def handle(self, message):
        return True

    def reply(self, message, content):
        msg = message.get_reply_obj()
        msg['Content'] = content
        msg['Metadata']['Source'] = self.name
        print(json.dumps(msg, indent=2, sort_keys=True))
        self.conn.publish(
            self.cfg.get('outbound', 'discord-outbound'),
            json.dumps(msg)
        )
