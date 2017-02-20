from copy import deepcopy
import requests
from requests.exceptions import HTTPError
from requests.compat import urljoin, quote
from apimas import documents as doc, exceptions as ex
from apimas.clients.auth import ApimasClientAuth
from apimas.clients.extensions import ApimasValidator


TRAILING_SLASH = '/'


def get_subdocuments(document):
    """ Get documents that are elements of lists of a parent document. """
    subdocs = {}
    for k, v in document.iteritems():
        if isinstance(v, list):
            subs = filter((lambda x: isinstance(x, dict)), v)
            if subs:
                subdocs[k] = subs
        elif isinstance(v, dict):
            for key, value in get_subdocuments(v).iteritems():
                subdocs[k + '/' + key] = value
    return subdocs


def to_cerberus_paths(data):
    """
    This utility function creates the corresponding paths of a cerberus
    validation schema which are respondible for validating the given data.

    Example:
    data = {
        'foo': {
            'bar': 'value'
        },
        'bar': 'value'
    }

    paths = ['foo/schema/bar', 'bar']

    :param data: Dictionary of data.

    :returns: A list of paths.
    """
    if not data:
        return []
    cerberus_paths = []
    for k, v in data.iteritems():
        cerberus_nodes = [k]
        if isinstance(v, list):
            continue
        if isinstance(v, dict):
            nodes = to_cerberus_paths(v)
            for node in nodes:
                cerberus_paths.append(
                    '/'.join((cerberus_nodes + ['schema', node])))
        else:
            cerberus_paths.append('/'.join(cerberus_nodes))
    return cerberus_paths


def handle_exception(func):
    """
    Handler of exceptions raised due to the response status codes.
    It catches them it raised an appropriate `ApimasClientException`.
    """
    def wrapper(*args, **kwargs):
        try:
            r = func(*args, **kwargs)
            if kwargs.pop('raise_exception', True):
                r.raise_for_status()
            return r
        except HTTPError as e:
            raise ex.ApimasClientException(
                e.message, response=e.response, request=e.request)
    return wrapper


class ApimasClient(object):
    """
    A class which defines a client for specific resource.
    All CRUD operations are supported.

    Typically, the initialization of the resource client requires the
    location of this resource to the web, resource specification and
    credentials if the resource is protected.

    TODO: Support additional actions.
    """

    def __init__(self, endpoint, schema):
        self.endpoint = endpoint
        self.validation_schema = schema
        self.api_validator = ApimasValidator(self.validation_schema)
        self.auth = None

    @handle_exception
    def create(self, raise_exception=True, headers=None, data=None):
        """
        Method for the creation of resource according to the given data.

        Example: POST endpoint/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        request_kwargs.update(self.extract_write_data(data, raise_exception))
        r = requests.post(self.endpoint, **request_kwargs)
        return r

    @handle_exception
    def update(self, resource_id, raise_exception=True, headers=None,
               data=None):
        """
        Method for the update of resource according to the specified data.

        Example: PUT endpoint/<pk>/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        data = self.validate(data or {}, raise_exception)
        request_kwargs.update(self.extract_write_data(data, raise_exception))
        r = requests.put(self.format_endpoint(resource_id), **request_kwargs)
        return r

    @handle_exception
    def partial_update(self, resource_id, raise_exception=True, headers=None,
                       data=None):
        """
        Method for the partial update of resource, i.e. only a part of the
        resource's fields are updated.

        Example: PATCH endpoint/<pk>/
        """
        request_kwargs = {
            'headers': headers,
            'auth': self.auth,
        }
        request_kwargs.update(self.extract_write_data(
            data, raise_exception, partial=True))
        r = requests.patch(self.format_endpoint(resource_id), **request_kwargs)
        return r

    @handle_exception
    def list(self, raise_exception=True, headers=None, params=None, data=None):
        """
        Method for getting a list of identical resources. Query parameters
        are supported.

        Example: GET endpoint/
        """
        r = requests.get(self.endpoint, headers=headers, params=params,
                         auth=self.auth, json=data)
        return r

    @handle_exception
    def retrieve(self, resource_id, raise_exception=True, headers=None,
                 params=None, data=None):
        """
        Method for a single resource matched with the specified resource
        id given as parameter. Query parameters are supported.

        Example: GET endpoint/<pk>/
        """
        r = requests.get(self.format_endpoint(resource_id), headers=headers,
                         params=params, auth=self.auth, json=data)
        return r

    @handle_exception
    def delete(self, resource_id, raise_exception=True, headers=None):
        """
        Method for the deletion of a specific resource.

        Example: DELETE endpoint/<pk>/
        """
        r = requests.delete(
            self.format_endpoint(resource_id), auth=self.auth,
            headers=headers)
        return r

    @handle_exception
    def head(self, resource_id=None, headers=None):
        """
        Method for making a HTTP HEAD request on a specific endpoint.
        """
        endpoint = self.endpoint if resource_id is None else\
            self.format_endpoint(resource_id)
        r = requests.head(endpoint, headers=headers, auth=self.auth)
        return r

    @handle_exception
    def options(self, headers=None):
        """
        Method for making a HTTP OPTIONS request on resource's endpoint.
        """
        r = requests.options(self.endpoint, headers=headers, auth=self.auth)
        return r

    def format_endpoint(self, resource_id):
        """
        This method concatenates the resource's endpoint with a specified
        identifier.

        Example: endpoint/<pk>/
        """
        if isinstance(resource_id, unicode):
            resource_id = resource_id.encode("utf-8")
        return urljoin(self.endpoint, quote(
            str(resource_id))) + TRAILING_SLASH

    def _validate_subdata(self, data, schema, raise_exception):
        """
        This function partially validates subdata of request.

        Subdata are considered nested data which are elements of lists.

        Example:

        data = {
            'foo': [
                {'foo': 'value'},
                {'bar': 'value'},
            ]
        }

        This function partial validates them according to their specified
        fields.

        :returns: A dictionary of validated subdata, with the path of their
        location to the parent document as keys.
        """
        subdocs = get_subdocuments(data)
        validated = {}
        schema = deepcopy(schema)
        for k, v in subdocs.iteritems():
            path = k.split('/')
            cerberus_path = []
            for u in path:
                cerberus_path.extend([u, 'schema'])
            subdata = doc.doc_pop(data, path)
            subschema = doc.doc_pop(schema, cerberus_path[:-1]) or {}
            subschema = subschema.get('schema', {}).get('schema', {})
            if not subschema:
                raise ex.ApimasClientException(
                    'Field {!r} cannot be validated'.format(str(tuple(path))))
            validated_docs = []
            for subdoc in subdata:
                validated_docs.append(self.partial_validate(
                    subdoc, raise_exception, subschema))
            validated[tuple(path)] = validated_docs
        return validated

    def partial_validate(self, data, raise_exception=True, schema=None):
        """
        Validates data that are going to be sent for a partial update of a
        resource.

        Construct a cerberus schema validator by taking into consideration
        only the fields that are included in the request.

        :param raise_exception: True if an exception should be raised when
        validation fails.
        """
        schema = schema or self.validation_schema
        cerberus_paths = to_cerberus_paths(data)
        validated_subdocs = self._validate_subdata(
            data, schema, raise_exception)
        partial_schema_paths = {
            path: doc.doc_get(schema, path.split('/'))
            for path in cerberus_paths}
        partial_schema = doc.doc_from_ns(partial_schema_paths)
        validator = ApimasValidator(partial_schema)
        is_valid = validator.validate(data)
        if raise_exception and not is_valid:
            raise ex.ApimasClientException(validator.errors)
        for k, v in validated_subdocs.iteritems():
            doc.doc_set(validator.document, k, v)
        return validator.document

    def validate(self, data, raise_exception=True):
        """
        Validates data that are going to be sent using a cerberus validation
        schema.

        :param raise_exception: True if an exception should be raised when
        validation fails.
        """
        is_valid = self.api_validator.validate(data)
        if raise_exception and not is_valid:
            raise ex.ApimasClientException(self.api_validator.errors)
        return self.api_validator.document

    def extract_files(self, data):
        """
        This functions checks if data which are going to be sent to request
        include files and it extract them.

        Then it performs two checks:
        a) It checks that the location of files is not nested.
        b) If files were detected, then it checks that request data does
        not include nested data.

        When uploading files, the `Content-Type` header of request is set
        to `multipart/form-data`.

        :param data: Dictionary of data which are going to be sent to request.

        :returns: A dictionary keyed by the name of the field and it includes
        all files to be uploaded.
        """
        paths = [path for path, val in doc.doc_iter(data)
                 if isinstance(val, file)]
        error_msg = ('Content-Type `application/json is not supported when'
                     ' uploading files`')
        if any(len(path) > 1 for path in paths):
            raise ex.ApimasClientException(error_msg)
        if paths and any(isinstance(v, (list, dict))
                         for _, v in data.iteritems()):
            raise ex.ApimasClientException(error_msg)
        return {path[-1]: doc.doc_pop(data, path) for path in paths}

    def extract_write_data(self, data, raise_exception, partial=False):
        """
        This function extracts data, sent for CREATE and UPDATE requests of
        a resource.

        This functions validates data, and then it seperates files to be
        uploaded from the rest.

        If files are present, then the `Content-Type` of request is set to
        `multipart/form-data`, otherwise `application/json`.

        :param data: Dictionary of data which are going to be sent to request.
        :param raise_exception: True if an exception should be raised when
        validation fails.
        :param partial: True if request includes a subset of resource's fields,
        False otherwise.
        """
        if partial:
            data = self.partial_validate(data or {}, raise_exception)
        else:
            data = self.validate(data or {}, raise_exception)
        files = self.extract_files(data)
        return {'data': data, 'files': files} if files else {'json': data}

    def set_credentials(self, auth_type, **credentials):
        """
        Set credentials to interact with the endpoint (
            If resource is protected) based on the selected auth type.
        """
        self.auth = ApimasClientAuth(auth_type, **credentials)
