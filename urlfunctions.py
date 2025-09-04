import urllib.parse


def url_suffix(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    _, dot, ext = parsed.path.rpartition('.')
    assert dot == '.', f'get extension from url failed: {url}'

    suffix = dot + ext
    assert suffix in ['.jpg', '.jpeg', '.png'], f'unexpected image extension: {suffix}'

    return suffix
