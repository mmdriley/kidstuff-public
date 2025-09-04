#! /usr/bin/env python3

from datetime import datetime, timedelta

# Look for pictures posted up to 10 days ago. Both endpoints are inclusive.
since = datetime.now() - timedelta(days=10)
until = datetime.now()

print('SINCE=' + since.strftime('%Y-%m-%d'))
print('UNTIL=' + until.strftime('%Y-%m-%d'))
