from copy import deepcopy
from collections import namedtuple
from apimas.errors import InvalidInput
from docular import doc_set, doc_get
from apimas.utils import normalize_path


ProcessorConstruction = namedtuple(
    "ProcessorConstruction", ["constructors", "processor"])

Null = object()


class Context(object):
    def __init__(self, d=None):
        self._d = d or {}

    def extract(self, path):
        """
        Extracts a specific key from context.

        Args:
            path (str|tuple): Key where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.

        Returns:
            The value of the desired key.
        """
        path = normalize_path(path)
        return doc_get(self._d, path)

    def save(self, path, value):
        """
        Saves a value to the context.

        Args:
            path (str|tuple): Path where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.
            value: Value to be saved to the context.
        """
        path = normalize_path(path)
        doc_set(self._d, path, value, multival=False)


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

    def __init__(self, collection_loc, action_name):
        self.collection_loc = collection_loc
        self.action_name = action_name

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
        return {k: context.extract(v) for k, v in keys.iteritems()}

    def _write_list(self, context, keys, data):
        for i, k in enumerate(keys):
            value = data[i]
            context.save(k, value)

    def _write_dict(self, context, keys, data):
        for k, v in keys.iteritems():
            value = data.get(k, Null)
            if value is Null:
                continue
            context.save(v, value)

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
        if isinstance(data, (list, tuple)) and isinstance(keys, (list, tuple)):
            assert len(data) == len(keys)
            return self._write_list(context, keys, data)
        if isinstance(data, dict) and isinstance(keys, dict):
            return self._write_dict(context, keys, data)
        raise InvalidInput('Incompatible types for \'keys\' ({!r}) and'
                           ' \'data\' ({!r})'.format(type(keys), type(data)))

    def execute(self, context_data):
        """
        Actual hook of a processor.
        Args:
            context_data (dict): Processor-specific keys extracted from
            context.
        Returns:
            Tuple of data to be written to context.

        """
        raise NotImplementedError('execute() must be implemented')

    def process(self, context):
        context_data = self.read(context)
        output = self.execute(context_data)
        if output is not None:
            self.write(output, context)
