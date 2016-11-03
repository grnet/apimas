from requests.exceptions import HTTPError


class ApimasException(Exception):
    pass


class ApimasClientException(HTTPError):
    pass
