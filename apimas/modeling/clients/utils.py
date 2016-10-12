from requests.exceptions import HTTPError


class ApimasClientException(HTTPError):
    pass
