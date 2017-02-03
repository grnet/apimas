from requests import Response
from requests.exceptions import HTTPError
from apimas.errors import GenericException


class ApimasException(GenericException):
    pass


class ApimasAdapterException(ApimasException):
    def __init__(self, msg, loc=(), *args, **kwargs):
        self.msg = msg
        self.loc = loc
        arglist = [msg]
        arglist.extend(args)
        kwargs['loc'] = loc
        super(ApimasAdapterException, self).__init__(*arglist, **kwargs)

    def __str__(self):
        if self.loc:
            return '{msg}, on location: ({loc})'.format(
                msg=self.msg, loc=', '.join(self.loc))
        return self.msg


class ApimasClientException(HTTPError):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if isinstance(self.response, Response):
            try:
                details = self.response.json()
            except ValueError:
                details = self.response.text
            detailed_msg = {'message': self.message, 'details': details}
            self.message = detailed_msg
