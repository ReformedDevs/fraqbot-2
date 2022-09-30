import os
import json

from helpers.components import Message
from helpers.components import redis_connect
from helpers.utils import jsearch
from modules.memes import Memes


TOKEN = os.environ.get('TOKEN')


def get_messages(conn, modules):
    sub = conn.pubsub()
    sub.subscribe('discord-inbound')

    for message in sub.listen():
        print(json.dumps(message, indent=2, sort_keys=True))
        message = Message(message)
        print(json.dumps(message.data, indent=2, sort_keys=True))

        for m in modules:
            if (
                message.type == m.filter['type']
                and jsearch(m.filter['search'], message.data)
            ):
                m.handle(message)


if __name__ == '__main__':
    conn = redis_connect('localhost', 6379)
    modules = [Memes(conn, {}, TOKEN)]

    while True:
        get_messages(conn, modules)
