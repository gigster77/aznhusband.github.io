import xml.etree.ElementTree as ET
import xbmc
from resolveurl import common


class RssSource:
    def __init__(self):
        self.net = common.Net()
        self.headers = {
            'User-Agent': common.RAND_UA,
            'Accept': '*/*'
        }

    def parse(self, rss_url, domains=None, limit=50):
        xbmc.log(f'RSS fetch: {rss_url}', xbmc.LOGDEBUG)

        r = self.net.http_GET(rss_url, headers=self.headers).content

        try:
            root = ET.fromstring(r)
        except Exception:
            xbmc.log('RSS parse failed', xbmc.LOGERROR)
            return []

        items = []
        for item in root.iter('item'):
            link = item.findtext('link')
            if not link:
                continue

            if domains and not any(d in link for d in domains):
                continue

            items.append({
                'title': item.findtext('title') or 'Stream',
                'link': link.strip(),
                'date': item.findtext('pubDate')
            })

            if len(items) >= limit:
                break

        return items

