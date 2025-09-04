import json
import re
import urllib.parse

import requests


# This value is hardcoded in the website's Javascript and isn't pulled from config.
# https://github.com/mmdriley/kidstuff/blob/09769fe0/websites/tinybeans/tinybeans-frontend/services/rest-backend.js#L143
aws_region = 'us-east-1'

aws_identity = 'us-east-1:bd2e63fa-d755-42c2-b14a-66ce0b9dad05'
aws_bucket = 'tinybeans-remote-upload-prod'
client_id = 'd324d503-0127-4a85-a547-d9f2439ffeae'


def check_config_values_against_website():
    r = requests.get('https://tinybeans.com/app')
    r.raise_for_status()

    # you can't parse HTML with regular expressions
    config_pattern = re.compile(r'''<meta name="tinybeans-frontend/config/environment" content="([^"]+)">''')
    match = config_pattern.search(r.text)
    if not match:
        assert False, "Couldn't find matching `meta` tag for config"

    config = json.loads(
        urllib.parse.unquote(
            match.group(1)))

    # pretty-print decoded config
    print(json.dumps(config, indent=2))

    assert(config['aws_identity'] == aws_identity)
    assert(config['aws_bucket'] == aws_bucket)
    assert(aws_identity.startswith(aws_region + ':'))
    assert(config['clientID'] == client_id)


if __name__ == '__main__':
    check_config_values_against_website()
