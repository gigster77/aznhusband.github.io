import json
import requests
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from resolveurl import common
from resolveurl.resolver import ResolveUrl, ResolverError
from resolveurl.lib import helpers

import xbmc


class HdPlay(ResolveUrl):
    name = 'HDPlay'
    domains = ['hdplay.se', 'drive.adramas.se']
    pattern = r'(?://|\.)(hdplay\.se|drive\.adramas\.se)/(.+)'

    def __init__(self):
        self.net = common.Net()
        self.headers = {
            'User-Agent': common.RAND_UA,
            'Referer': 'https://hdplay.se/'
        }

    def get_url(self, host, media_id):
        return f'https://{host}/{media_id}'

    def get_media_url(self, host, media_id):
        url = self.get_url(host, media_id)

        response = requests.get(url, headers=self.headers, timeout=10)
        if response.status_code != 200:
            raise ResolverError(f'HDPlay HTTP error: {response.status_code}')

        soup = BeautifulSoup(response.text, 'html.parser')

        # ---------------------------------------------------------
        # 1️⃣ Try iframe embeds first (most common now)
        # ---------------------------------------------------------
        iframe = soup.find('iframe')
        if iframe and iframe.get('src'):
            iframe_url = urljoin(url, iframe['src'])
            xbmc.log(f'HDPlay iframe found: {iframe_url}', xbmc.LOGDEBUG)
            return iframe_url + helpers.append_headers(self.headers)

        # ---------------------------------------------------------
        # 2️⃣ Look for JS objects containing video URLs
        # ---------------------------------------------------------
        for script in soup.find_all('script'):
            if not script.string:
                continue

            text = script.string.strip()

            # Look for JSON-style objects
            if 'video' in text or 'sources' in text:
                try:
                    # Extract JSON-like payload safely
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    if start == -1 or end == -1:
                        continue

                    payload = text[start:end]
                    data = json.loads(payload)

                    # Common patterns
                    if isinstance(data, dict):
                        if 'video_url' in data:
                            return self._build_url(host, data['video_url'])

                        if 'sources' in data and isinstance(data['sources'], list):
                            for src in data['sources']:
                                if 'file' in src:
                                    return self._build_url(host, src['file'])

                except Exception:
                    continue

        # ---------------------------------------------------------
        # 3️⃣ Look for <video><source> tags
        # ---------------------------------------------------------
        video = soup.find('video')
        if video:
            source = video.find('source')
            if source and source.get('src'):
                return self._build_url(host, source['src'])

        xbmc.log('HDPlay: No playable media found', xbmc.LOGERROR)
        raise ResolverError('Unable to resolve HDPlay media URL')

    def _build_url(self, host, src):
        if not src.startswith('http'):
            src = urljoin(f'https://{host}', src)
        return src + helpers.append_headers(self.headers)

    @classmethod
    def _is_enabled(cls):
        return True
