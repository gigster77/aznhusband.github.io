import json
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
        self.base_headers = {
            'User-Agent': common.RAND_UA,
            'Accept': '*/*',
        }

    def get_url(self, host, media_id):
        return f'https://{host}/{media_id}'

    def get_media_url(self, host, media_id):
        page_url = self.get_url(host, media_id)

        headers = self.base_headers.copy()
        headers['Referer'] = f'https://{host}/'
        headers['Origin'] = f'https://{host}'

        # -------------------------------------------------
        # 1️⃣ Load embed page (with cookies)
        # -------------------------------------------------
        r = self.net.http_GET(page_url, headers=headers).content
        soup = BeautifulSoup(r, 'html.parser')

        # -------------------------------------------------
        # 2️⃣ Extract API endpoint from JS
        # -------------------------------------------------
        api_url = None

        for script in soup.find_all('script'):
            text = script.string
            if not text:
                continue

            if '/api/source/' in text:
                start = text.find('/api/source/')
                end = text.find('"', start)
                api_url = text[start:end]
                break

        # -------------------------------------------------
        # 3️⃣ Fallback: iframe → recursive resolve
        # -------------------------------------------------
        if not api_url:
            iframe = soup.find('iframe')
            if iframe and iframe.get('src'):
                iframe_url = urljoin(page_url, iframe['src'])
                xbmc.log(f'HDPlay fallback iframe: {iframe_url}', xbmc.LOGDEBUG)
                return common.resolve(iframe_url)

            raise ResolverError('HDPlay: No API or iframe found')

        api_url = urljoin(page_url, api_url)
        xbmc.log(f'HDPlay API: {api_url}', xbmc.LOGDEBUG)

        # -------------------------------------------------
        # 4️⃣ Call API
        # -------------------------------------------------
        api_headers = headers.copy()
        api_headers['Referer'] = page_url

        r = self.net.http_GET(api_url, headers=api_headers).content

        try:
            data = json.loads(r)
        except Exception:
            raise ResolverError('HDPlay: Invalid API response')

        sources = data.get('data') or []
        if not sources:
            raise ResolverError('HDPlay: No sources returned')

        # -------------------------------------------------
        # 5️⃣ Pick best quality (HLS preferred)
        # -------------------------------------------------
        def score(src):
            file = src.get('file', '')
            label = src.get('label', '')
            return (
                2 if file.endswith('.m3u8') else 1,
                int(''.join(filter(str.isdigit, label)) or 0)
            )

        sources.sort(key=score, reverse=True)

        for src in sources:
            file_url = src.get('file')
            if file_url and file_url.startswith('http'):
                xbmc.log(f'HDPlay stream selected: {file_url}', xbmc.LOGDEBUG)
                return file_url + helpers.append_headers(api_headers)

        raise ResolverError('HDPlay: No playable stream found')

    @classmethod
    def _is_enabled(cls):
        return True

