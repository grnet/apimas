import json
import re
from django.conf import settings
from django.http import HttpResponse
from apimas.errors import ConflictError, ValidationError


HTTP_REGEX = re.compile(r'^HTTP_[a-zA-Z_]+$')
CONTENT_TYPE_REGEX = re.compile(r'^CONTENT_TYPE$')
CONTENT_LENGTH_REGEX = re.compile(r'^CONTENT_LENGTH$')


class DjangoWrapper(object):
    """
    A class which is actually a wrapper of the apimas actions. It is
    responsible for:
        * Conversion of the django request into apimas.
        * Execution of the action pipelines.
        * Conversion of the apimas response into django.

    It is initialized with a dict of actions which are mapped to the
    same url pattern but they use a different HTTP method.
    """
    def __init__(self, actions):
        self.actions = actions

    def get_headers(self, request):
        """
        Get headers from Django Request object.

        All HTTP headers begin with 'HTTP_' except for content_type and
        content_length.


        See: http://bit.ly/2mRWjk9

        Args:
            request: Django request object.

        Returns:
            dict: Dictionary with the headers of the request.
        """
        request_headers = {}
        regex_patterns = [HTTP_REGEX, CONTENT_TYPE_REGEX, CONTENT_LENGTH_REGEX]
        for header in request.META.iterkeys():
            if any(regex.match(header) for regex in regex_patterns):
                request_headers[header] = request.META[header]
        return request_headers

    def get_query_params(self, request):
        """ Get query parameters of the Django request object. """
        return request.GET

    def get_content_type(self, request, default=None):
        """
        Get the content type of the request based on the corresponding HTTP
        header.
        """
        return request.META.get('CONTENT_TYPE', default)

    def create_native_response(self, response):
        """
        Creates a Django `HttpResponse` object response using the apimas
        response object. The created object is actually used by the backend
        to serve the response to the client.

        Args:
            response: APIMAS response object.

        Returns:
            Django native response.
        """
        if response.get('native') is not None:
            raise ConflictError('Native Response object already exists')
        content = response.get('content')
        content_type = response.get('meta', {}).get('content_type')
        if content_type == 'application/json':
            content = json.dumps(content)
        status_code = response.get('meta', {}).get('status_code')
        headers = response.get('meta', {}).get('headers', {})

        response = HttpResponse(content=content, content_type=content_type,
                                status=status_code)
        for k, v in headers.iteritems():
            response[k] = v
        return response

    def load_application_json_body(self, body):
        if not body:
            return {}
        body_unicode = body.decode(settings.DEFAULT_CHARSET)
        try:
            return json.loads(body_unicode)
        except Exception as e:
            raise ValidationError(e)

    def split_content_type_parts(self, content_type):
        content_type_parts = []
        for part in content_type.split(';'):
            if part.strip():
                content_type_parts.append(part)
        return content_type_parts

    def get_body_and_files(self, request):
        content_type = self.get_content_type(request, '')
        content_type_parts = self.split_content_type_parts(content_type)

        if 'multipart/form-data' in content_type_parts:
            if request.method == 'POST':
                post_data, files_data = request.POST, request.FILES
            else:
                post_data, files_data = request.parse_file_upload(
                    request.META, request)
            return post_data.dict(), files_data.dict()

        elif 'application/json' in content_type_parts:
            loaded_body = self.load_application_json_body(request.body)
            files = request.FILES
            assert not files
            return loaded_body, files.dict()

        else:
            # we currently don't support any other type of input
            assert not request.body
            return {}, {}

    def _get_apimas_request(self, request, **kwargs):
        """
        Creates an APIMAS request object based on the initial django request.
        """
        params = self.get_query_params(request)
        headers = self.get_headers(request)
        body, files = self.get_body_and_files(request)
        # Merge data and the files of the request.
        data = dict(body, **files)
        meta = {
            'params': params,
            'files': files,
            'headers': headers,
            'kwargs': kwargs,
        }

        return {
            'content': data,
            'native': request,
            'meta': meta,
        }

    def execute_action(self, action, request, **kwargs):
        apimas_request = self._get_apimas_request(request, **kwargs)
        apimas_response = action.process(apimas_request)
        django_response = self.create_native_response(apimas_response)
        return django_response

    def __call__(self, request, **kwargs):
        """
        Django function-based views.

        The actual view which is mapped with a url pattern.
        """
        action = self.actions.get(request.method)
        if action:
            return self.execute_action(action, request, **kwargs)

        # Return 405 `METHOD_NOT_ALLOWED` if not any action found for the
        # particular request method.
        return HttpResponse(status=405)
