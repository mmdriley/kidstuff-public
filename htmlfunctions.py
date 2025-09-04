import html5lib


def text_from_html(html: str):
    parsed = html5lib.parseFragment(html)
    return ''.join(parsed.itertext())
