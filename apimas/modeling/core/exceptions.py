from requests import Response
from requests.exceptions import HTTPError


class ApimasException(Exception):
    pass


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
