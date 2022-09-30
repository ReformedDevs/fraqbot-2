import os
import re
import sys

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if APP_DIR not in sys.path:
    sys.path.append(APP_DIR)

from helpers.components import Fraqbot  # noqa: E402
from helpers.files import load_file  # noqa: E402
from helpers.utils import call_rest_api  # noqa: E402


class Memes(Fraqbot):
    def __init__(self, conn, cfg, token=None):
        cfg.update({'name': 'Memes'})
        super().__init__(conn, cfg, token)
        self.load_configs()

    def load_configs(self):
        self.automemes = load_file(
            os.path.join(APP_DIR, 'modules', 'data', 'autogen_memes.yaml'))
        templates = call_rest_api(
            'memes',
            'get',
            'https://api.memegen.link/templates', response='json'
        )
        templates += load_file(
            os.path.join(APP_DIR, 'modules', 'data', 'custom_memes.yaml'))

        self.templates_by_id = {t['id']: t for t in templates}
        self.templates_by_name = {t['name']: t for t in templates}
        self.re = re.compile(
            f'^({"|".join(self.templates_by_id.keys())}): ?(.*)$')

    def handle(self, message):
        content = message.data.get('content')

        if isinstance(content, str):
            if content.lower().startswith('!help memes'):
                self.handle_help(message)
                return None

            matches = [
                m for m in [
                    (i, re.search(meme['match'], content, re.IGNORECASE))
                    for i, meme in enumerate(self.automemes)
                ]
                if m[1]
            ]

            if matches:
                self.handle_auto_memes(message, matches)
            else:
                match = self.re.match(content)

                if match:
                    self.handle_meme(message, match)

    def handle_help(self, message):
        memes = sorted([
            f'{k} ({v["id"]})' for k, v in self.templates_by_name.items()])
        thread = self.api.create_thread(message)

        while memes:
            msg = '\n- {}'.format('\n- '.join(memes[:50]))
            self.api.create_message(thread['id'], msg)
            memes = memes[50:]

    def handle_meme(self, message, match):
        template = match.group(1)
        texts = re.split(r',\s*', match.group(2))

        if len(texts) == 1:
            text_1 = ' '
            text_2 = texts[0]
        elif len(texts) == 2:
            text_1 = texts[0]
            text_2 = texts[1]
        else:
            text_1 = ', '.join(texts[:-1])
            text_2 = texts[-1]

        url = self.build_url(template, text_1, text_2)
        self.reply(message, url)

    def handle_auto_memes(self, message, matches):
        for (i, match) in matches:
            meme = self.automemes[i]
            texts = []

            for text in meme['text']:
                if '${1}' in text:
                    text = text.replace('${1}', match.group(1))

                if '${2}' in text:
                    text = text.replace('${2}', match.group(2))

                texts.append(text)

            url = self.build_url(meme['template'], texts[0], texts[1])
            self.reply(message, url)

    def string_replace(self, text):
        replacements = {
            '_': '__',
            '-': '--',
            ' ': '_',
            '?': '~q',
            '%': '~p',
            '#': '~h',
            '/': '~s',
            '"': "''",
            '‘': "'",
            '’': "'",
            '“': "''",
            '”': "''"
        }

        for srch, repl in replacements.items():
            text = text.replace(srch, repl)

        return text.strip()

    def build_url(self, template, text_1, text_2):
        params = '?fong=impact'
        alt = self.templates_by_id[template].get('alt')

        if alt:
            template = 'custom'
            params += f'&alt={alt}'

        url = (f'https://api.memegen.link/images/{template}'
               f'/{self.string_replace(text_1)}'
               f'/{self.string_replace(text_2)}.jpg{params}')

        return url
