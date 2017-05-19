from apimas.errors import InvalidInput


def _normalize_keys(keys):
    if isinstance(keys, str):
        return keys.split('/')
    return keys


class BaseProcessor(object):
    """
    Interface for implementing apimas processors.

    The interface of processors is very simple. It is called via its method
    `process()`, it reads some keys from the context of request, it executes
    arbitrary code and then writes its output back to the context of request.

    Each processor has to specify the following attributes:
        * name (str): Identifier of the processor, i.e. its module path.
        * READ_KEYS (dict): Human readable keys which are mapped to the actual
             keys of context from which processor reads.
        * WRITE_KEYS (dict): Human readable keys which are mapped to the actual
             keys of the context to which processor writes.
    """

    name = 'apimas.components.BaseProcessor'

    def __init__(self, spec, **kwargs):
        self.spec = spec

    def extract(self, context, key):
        """
        Extracts a specific key from context.

        Args:
            context: Context from which processor reads.
            key (str|tuple): Key where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.

        Returns:
            The value of the desired key.
        """
        key = _normalize_keys(key)
        for k in key:
            try:
                context = context.get(k)
            except (AttributeError, IndexError, KeyError):
                try:
                    context = getattr(context, k)
                except AttributeError:
                    return None
        return context

    def save(self, context, key, value):
        """
        Saves a value to the context.

        Args:
            context: Context to which processor writes.
            key (str|tuple): Key where desired value is located, either
                string or tuple format (e.g. `foo/bar` or `('foo', bar')`.
            value: Value to be saved to the context.
        """
        if context is None:
            raise InvalidInput(
                'Cannot save to context. Context is `NoneType`')
        key = _normalize_keys(key)
        attr = key[-1]
        while True:
            inst = context if not key else self.extract(context, key)
            if isinstance(inst, dict):
                inst.update(value)
                break
            else:
                try:
                    setattr(inst, attr, value)
                    break
                except AttributeError:
                    attr = key[-1]
                    value = {key[-1]: value}
                    key = key[:-1]

    def read(self, context):
        """
        Gets a subset of context based on the `READ_KEYS` specified
        by the processor.

        Args:
            context: Context from which processor reads.

        Returns:
            dict: Dictionary of human readable keys mapped to the extracted
                values of context.

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
        return {k: self.extract(context, v)
                for k, v in self.READ_KEYS.iteritems()}

    def write(self, data, context):
        """
        Writes data to the context based on the `WRITE_KEYS` specified
        by the processor.

        Args:
            data (dict): Data keyed by human readable identifiers which are
                saved to the actual keys of the context.
            content: Context to which processor writes.

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
        for k, v in self.WRITE_KEYS.iteritems():
            value = data.get(k)
            self.save(context, v, value)

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

    def handle_error(self, processor, processor_args, ex):
        """
        Handles any error occcured in handler or processors.

        Args:
            component (str): Identifier of handler/processor in which error
                occured.
            proc_args (tuple): Args with which handler/processors was called
                 by apimas.
            ex (Exception): Error instance raised by handler of processors.
        """
        raise NotImplementedError('handle_error() must be implemented')
