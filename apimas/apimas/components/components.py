from copy import deepcopy
from apimas.errors import InvalidInput
from apimas.documents import doc_set, doc_get
from apimas.utils import normalize_path


class BaseProcessor(object):
    """
    Interface for implementing apimas processors.

    The interface of processors is very simple. It is called via its method
    `process()`, it reads some keys from the context of request, it executes
    arbitrary code and then writes its output back to the context of request.

    Each processor has to specify the following attributes:
        * name (str): Identifier of the processor, i.e. its module path.
        * READ_KEYS: Dictionary of Human readable keys which are mapped to the
             actua; keys of context from which processor reads or a tuple
             of the actual keys.
        * WRITE_KEYS: Human readable keys which are mapped to the actual
             keys of the context to which processor writes or a tuple
             of the actual keys to write.
    """

    name = 'apimas.components.BaseProcessor'

    def __init__(self, collection, spec, **meta):
        if collection:
            self.collection = normalize_path(
                collection, right_order=True, max_splits=1)
        else:
            self.collection = collection
        self.spec = deepcopy(spec)
        self.meta = meta

    def extract(self, context, path):
        """
        Extracts a specific key from context.

        Args:
            context: Context from which processor reads.
            path (str|tuple): Key where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.

        Returns:
            The value of the desired key.
        """
        path = normalize_path(path)
        return doc_get(context, path)

    def save(self, context, path, value):
        """
        Saves a value to the context.

        Args:
            context: Context to which processor writes.
            path (str|tuple): Path where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.
            value: Value to be saved to the context.
        """
        if context is None:
            raise InvalidInput(
                'Cannot save to context. Context is `NoneType`')
        path = normalize_path(path)
        doc_set(context, path, value, multival=False)

    def read(self, context):
        """
        Gets a subset of context based on the `READ_KEYS` specified
        by the processor.

        Args:
            context: Context from which processor reads.

        Returns:
            dict: Dictionary of the extracted values of context.

        Examples:
            >>> from apimas.components import BaseProcessor
            >>> class MyProcessor(BaseProcessor):
            ...     READ_KEYS = {
            ...         'foo': 'data/foo',
            ...         'bar': 'data/bar'
            ...     }
            >>> context = {'data': {'foo': 10, 'bar': 20}}
            >>> processor = MyProcessor(spec={})
            >>> processor.read(context)
            {'foo': 10, 'bar': 20}
        """
        keys = getattr(self, 'READ_KEYS', None)
        if keys is None:
            raise InvalidInput(
                'No `READ_KEYS` are specified. Cannot read from context')
        if not isinstance(keys, (list, tuple, dict)):
            raise InvalidInput('Attribute \'READ_KEYS\' must be one of'
                               ' list, tuple or dict, not {!r}'.format(
                                    type(keys)))
        if isinstance(keys, (list, tuple)):
            keys = {k: k for k in keys}
        return {k: self.extract(context, v) for k, v in keys.iteritems()}

    def _write_list(self, context, keys, data):
        for i, k in enumerate(keys):
            value = data[i]
            self.save(context, k, value)

    def _write_dict(self, context, keys, data):
        for k, v in keys.iteritems():
            value = data.get(k)
            self.save(context, v, value)

    def write(self, data, context):
        """
        Writes data to the context based on the `WRITE_KEYS` specified
        by the processor.

        Args:
            data: Data can be in the form of args, which means that each item
                is written to the corresponding item of `WRITE_KEYS`,
                otherwise, data may be keyed by human readable identifiers
                which are saved to the actual keys of the context. Note that
                data *must* have the same type as `WRITE_KEYS`.
            context: Context to which processor writes.

        Examples:
            >>> from apimas.components import BaseProcessor
            >>> class MyProcessor(BaseProcessor):
            ...     WRITES_KEYS = {
            ...         'foo': 'data/foo',
            ...         'bar': 'data/bar'
            ...     }
            >>> context = {'data': {'foo': 10, 'bar': 20}}
            >>> data = {'foo': 'new', 'bar': 1}
            >>> processor = MyProcessor(spec={})
            >>> processor.write(data, context)
            >>> context
            {'data': {'foo': 'new', 'bar': 1}}
        """
        keys = getattr(self, 'WRITE_KEYS', None)
        if keys is None:
            raise InvalidInput(
                'No `READ_KEYS` are specified. Cannot read from context')
        if not isinstance(keys, (list, tuple, dict)):
            raise InvalidInput('Attribute \'WRITE_KEYS\' must be one of'
                               ' list, tuple or dict, not {!r}'.format(
                                    type(keys)))
        assert len(data) == len(keys)
        if isinstance(data, (list, tuple)) and isinstance(keys, (list, tuple)):
            return self._write_list(context, keys, data)
        if isinstance(data, dict) and isinstance(keys, dict):
            return self._write_dict(context, keys, data)
        raise InvalidInput('Incompatible types for \'keys\' ({!r}) and'
                           ' \'data\' ({!r})'.format(type(keys), type(data)))

    def process(self, collection, url, action, context):
        """
        Actual hook of the processor.

        Args:
            collection (str): Collection path on which action is performed.
            url (str): Action url.
            action (str): Action name.
            context (dict): Context used by processor to reads its data and
                writes its state.
        """
        raise NotImplementedError('process() must be implemeneted')


class BaseHandler(BaseProcessor):
    """
    Interface for implementing a handler.

    Handlers have the same behaviour with processors. However, handlers are
    also responsible for handling any error occured in processors or handler.
    """
    name = 'apimas.components.BaseHandler'

    def handle_error(self, component, cmp_args, ex):
        """
        Handles any error occcured in handler or processors.

        Args:
            component (str): Identifier of handler/processor in which error
                occured.
            cmp_args (tuple): Args with which handler/processors was called
                 by apimas.
            ex (Exception): Error instance raised by handler of processors.
        """
        raise NotImplementedError('handle_error() must be implemented')
