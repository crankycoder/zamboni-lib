"""
raven.core.processors
~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 by the Sentry Team, see AUTHORS for more details.
:license: BSD, see LICENSE for more details.
"""


from raven.utils import varmap


class Processor(object):
    def __init__(self, client):
        self.client = client

    def get_data(self, data, **kwargs):
        return

    def process(self, data, **kwargs):
        resp = self.get_data(data, **kwargs)
        if resp:
            data = resp
        return data


class RemovePostDataProcessor(Processor):
    """
    Removes HTTP post data.
    """
    def process(self, data, **kwargs):
        if 'sentry.interfaces.Http' in data:
            data['sentry.interfaces.Http'].pop('body', None)

        return data


class RemoveStackLocalsProcessor(Processor):
    """
    Removes local context variables from stacktraces.
    """
    def process(self, data, **kwargs):
        if 'sentry.interfaces.Stacktrace' in data:
            for frame in data['sentry.interfaces.Stacktrace'].get('frames', []):
                frame.pop('vars', None)

        return data


class SanitizePasswordsProcessor(Processor):
    """
    Asterisk out passwords from password fields in frames, http,
    and basic extra data.
    """
    MASK = '*' * 8

    def sanitize(self, key, value):
        if not key:  # key can be a NoneType
            return value

        key = key.lower()
        if 'password' in key or 'secret' in key:
            # store mask as a fixed length for security
            return self.MASK

        return value

    def filter_stacktrace(self, data):
        if 'frames' not in data:
            return
        for frame in data['frames']:
            if 'vars' not in frame:
                continue
            frame['vars'] = varmap(self.sanitize, frame['vars'])

    def filter_http(self, data):
        for n in ('body', 'cookies', 'headers', 'env', 'querystring'):
            if n not in data:
                continue

            if isinstance(data[n], basestring) and '=' in data[n]:
                # at this point we've assumed it's a standard HTTP query
                querystring = [c.split('=') for c in data[n].split('&')]
                querystring = [(k, self.sanitize(k, v)) for k, v in querystring]
                data[n] = '&'.join('='.join(k) for k in querystring)
            else:
                data[n] = varmap(self.sanitize, data[n])

    def process(self, data, **kwargs):
        if 'sentry.interfaces.Stacktrace' in data:
            self.filter_stacktrace(data['sentry.interfaces.Stacktrace'])

        if 'sentry.interfaces.Http' in data:
            self.filter_http(data['sentry.interfaces.Http'])

        return data