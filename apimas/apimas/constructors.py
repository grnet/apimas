"""Standard validating constructor library

Constructors in this module validate value constraints, normalize values.

Optionally, constructors can create random conforming values.

"""
import itertools
import sys
from random import choice, randint
import re

from apimas.documents import register_constructor, doc_value
from apimas.errors import ValidationError, ConflictError
from apimas.decorators import (
    last as last_d, after as after_d, conditional as cond_d)


MAXINT = sys.maxint
MININT = -sys.maxint - 1


def construct_integer(instance, spec, loc, context):
    """Construct and validate a python int/long.

    Args:
        instance (dict or int):
            Current input instance
        spec (dict):
            Specification for the current input instance
        spec/min:
            minimum permitted value
        spec/max:
            maximum permitted value
        spec/.randomize:
            create a random conforming value if instance provides no value
        loc (tuple of str):
            Path location of the current instance within the
            top-level instance being constructed.
        context (dict):
            The context of the construction. Contains keys:
            - top_spec
              The specification for the top-level instance. This can be used by
              the constructor to gain access to arbitrary parts of the
              specification to fulfill any dependencies.  Note that outside its
              own node, a constructor may only have spec access. It may never
              have access to instance nodes outside its own.
            - cons_round
              The number of the construction round resulting from constructors
              raising DeferConstructor. Construction at each node starts at
              round 0.
              Constructors can use this to place themselves in a specific round
              to wait for dependencies without having to explicitly state their
              dependencies.
            - constructors
              A set containing the full name paths for the constructors already
              completed for this node. Constructors can check this to defer for
              their dependencies.
            - sep
              The separator used for constructor names, '.' by default.

    Returns:
        integer:
            The constructed integer/long instance.

    """
    min = spec.get('min', None)
    max = spec.get('max', None)
    val = doc_value(instance)

    if val is None and '.randomize' in spec:
        _min = MININT if min is None else min
        _max = MAXINT if max is None else max
        val = randint(_min, _max)

    if isinstance(instance, basestring):
        if not instance.isdigit():
            m = "{loc}: {instance!r} is not an integer"
            m = m.format(loc=loc, instance=instance)
            raise ValidationError(m)

        val = int(instance)

    elif not isinstance(val, (int, long)):
        m = "{loc!r}: cannot make an integer out of {val!r}"
        m = m.format(loc=loc, val=val)
        raise ValidationError(m)

    if min is not None and val < min:
        m = "{loc}: integer {val!r} less than min {min!r}"
        m = m.format(loc=loc, val=val, min=min)
        raise ValidationError(m)

    if max is not None and val > max:
        m = "{loc}: integer {instance!r} greater than max {max!r}"
        m = m.format(val=val, min=min)
        raise ValidationError(m)

    return val


def construct_text(instance, spec, loc, context):
    """Construct and validate a python str/unicode.

    Args:
        instance (dict or int):
            Current input instance
        spec (dict):
            Specification for the current input instance
        spec/minlen:
            minimum permitted character length
        spec/max:
            maximum permitted character length
        spec/regex:
            a regular expression to be matched against the value
        spec/exclude_chars:
            a string of individually forbidden chars
        spec/.randomize:
            create a random conforming value if instance provides no value
        loc (tuple of str):
            Path location of the current instance within the
            top-level instance being constructed.
        context:
            The context of the construction. Contains keys:
            - top_spec
              The specification for the top-level instance. This can be used by
              the constructor to gain access to arbitrary parts of the
              specification to fulfill any dependencies.  Note that outside its
              own node, a constructor may only have spec access. It may never
              have access to instance nodes outside its own.
            - cons_round
              The number of the construction round resulting from constructors
              raising DeferConstructor. Construction starts at round 0.
              Constructors can use this to place themselves in a specific round
              to wait for dependencies without having to explicitly state their
              dependencies.
            - constructors
              A set containing the full name paths for the constructors already
              completed for this node. Constructors can check this to defer for
              their dependencies.
            - sep
              The separator used for constructor names, '.' by default.

    Returns:
        text:
            The constructed text instance.

    """
    blankable = spec.get('blankable', True)
    regex = spec.get('regex', None)
    encoding = spec.get('encoding', 'utf-8')
    minlen = int(spec.get('minlen', 0))
    maxlen = int(spec.get('maxlen', MAXINT))
    exclude_chars = spec.get('exclude_chars', '')

    text = doc_value(instance)
    if text is None and '.randomize' in spec:
        if regex is not None:
            m = "{loc!r}: cannot '.randomize' when 'regex' is given"
            m = m.format(loc=loc)
            raise NotImplementedError(m)

        alphabet = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789_-")

        text = ''.join(choice(alphabet)
                       for _ in xrange(randint(minlen, maxlen)))

    if isinstance(text, str):
        text = text.decode(encoding)

    elif not isinstance(text, unicode):
        m = "{loc}: text {text!r} is neither str nor unicode"
        m = m.format(loc=loc, text=text)
        raise ValidationError(m)

    if not blankable and not text:
        m = "{loc}: text cannot be blank"
        m = m.format(loc=loc)
        raise ValidationError(m)

    if regex is not None:
        pattern = re.compile(regex, re.UNICODE)
        if pattern.match(text) is None:
            m = "{loc}: {text!r} does not match regex {regex!r}"
            m = m.format(loc=loc, text=text, regex=regex)
            raise ValidationError(m)

    text_len = len(text)
    if text_len < minlen:
        m = "{loc}: {text!r}: minimum length {minlen!r} breached"
        m = m.format(loc=loc, text=text, minlen=minlen)
        raise ValidationError(m)

    if maxlen is not None and text_len > maxlen:
        m = "{loc}: {text!r}: maximum length {maxlen!r} exceeded"
        m = m.format(loc=loc, text=text, maxlen=maxlen)
        raise ValidationError(m)

    if exclude_chars:
        for c in exclude_chars:
            if c in text:
                m = "{loc!r}: {text!r}: forbidden char {c!r} found"
                m = m.format(loc=loc, text=text, c=c)
                raise ValidationError(m)

    return text


register_constructor(construct_integer, 'integer')
register_constructor(construct_text, 'text')


class Constructor(object):
    """
    This interface defines the behaviour of class-like constructors.

    Typically, these constructors are initialized and parameterized with some
    arguments which change the behaviour and logic of construction process.

    Then, the initialized objects are treated as callables. The actual
    implementation of construction is at method `construct()`.

    Args:
        last (bool): (optional) `True` if constructor should be executed after
            all constructors of the same node; `False` otherwise. Default is
            `False`.
        after (list): (optional) List of constructors after which the current
            constructor should be executed. Default is empty list.
        conditionals (list): (optional) List of constructors which are required
            to be present to run this constructor.
        pre_hook (callable): (optional) A callable which runs before the
            execution of this constructor. The return value of this callable
            (if any) is passed to the hook of construction.
        post_hook (callable): (optional) A callable which runs after the
           execution of this constructor.
    """
    def __init__(self, last=False, after=None, conditionals=None,
                 pre_hook=None, post_hook=None):
        self.last = last
        self.after = after or []
        self.conditionals = conditionals or []
        self.pre_hook = pre_hook
        self.post_hook = post_hook

        if self.pre_hook:
            assert callable(pre_hook), (
                    "'pre_hook' parameter should be a callable")
        if self.post_hook:
            assert callable(post_hook), (
                    "'post_hook' parameter should be a callable")
        assert not (last and after), ('`last` and `after` are mutually'
                ' exclusive')

        if self.last:
            # Attach `last` decorator at `construct()` runtime.
            setattr(self, 'construct', last_d(self.construct))

        if self.after:
            # Attach `after` decorator at `construct()` runtime.
            setattr(self, 'construct', after_d(after)(self.construct))

        if self.conditionals:
            # Attach `conditionals` decorator at `construct()` runtime.
            setattr(self, 'construct', cond_d(conditionals)(self.construct))

    def construct(self, context, **meta):
        """
        The actual hook of construction.

        This should be implemented by other constructors.
        """
        raise NotImplementedError('construct() must be implemented')

    def __call__(self, context):
        meta = {}
        if self.pre_hook:
            meta = self.pre_hook(context)
        instance = self.construct(context=context, **meta)
        if self.post_hook:
            # Post hook gets the newly created instance and the context.
            instance = self.post_hook(context, instance)
        return instance


class Object(Constructor):
    """
    Construct an instance of a specified class.

    This class can be specified on the spec, instance, or both. Also, class
    may take spec or instance as a single argument or as keyword arguments.

    Args:
        cls: Class of the constructed object.
        args_spec (bool): `True` if class takes spec as argument;
            `False` otherwise.
        kwargs_spec (bool): `True` if class takes the keys of spec
            as arguments; `False` otherwise. In this case spec *must* be
            a `dict`.
        args_instance (bool): `True` if class takes instance as argument;
            `False` otherwise.
        kwargs_instance (bool): `True` if class takes the keys of instance
            as arguments. In this case, instance *must* be a `dict`.
        args_spec_name (str): (optional) Name of the argument of spec. This
            combine with `args_spec=True`. Default is 'spec'.
        args_instance_name (str): (optional) Name of the argument of instance.
            This combine with `args_instance=True`. Defaullt is `instance`.
        kwargs_spec_mapping (dict): (optional) Map keys of spec to the actual
            names of the arguments that class takes. It combine with
            `kwargs_spec=True`. If spec key is not found then the name of
            argument is set as the key.

    Examples:
        A class that takes spec a single argument named 'foo'.

        >>> from apimas.constructors import Object
        >>> from apimas.testing.helpers import create_mock_constructor_context
        >>> class MyClass(object):
        ...     def __init__(self, foo):
        ...         self.foo = foo
        >>> spec = 'blah blah'
        >>> context = create_mock_constructor_context(instance=instance)
        >>> obj_constructor = Object(args_spec=True, args_spec_name='foo')
        >>> obj = obj_constructor.construct(context)
        >>> obj.foo
        'blah blah'

        A class that takes the keys of spec as arguments.
        >>> from apimas.constructors import Object
        >>> from apimas.testing.helpers import create_mock_constructor_context
        >>> class MyClass(object):
        ...     def __init__(self, foo, bar):
        ...         self.foo = foo
        ...         self.bar = bar
        >>> spec = {'a': 10, 'b': 'blah blah'}
        >>> context = create_mock_constructor_context(instance=instance)
        >>> kwargs_spec_mapping = {'a': 'foo', 'b': 'bar'}
        >>> obj_constructor = Object(kwargs_spec=True,
        ...                          kwargs_spec_mapping=kwargs_spec_mapping)
        >>> obj = obj_constructor.construct(context)
        >>> obj.foo, obj.bar
        (10, 'blah blah')

    """
    def __init__(self, cls, args_spec=False, kwargs_spec=False,
                 args_instance=False, kwargs_instance=False,
                 args_spec_name='spec', args_instance_name='instance',
                 kwargs_spec_mapping=None, *args, **kwargs):
        super(Object, self).__init__(*args, **kwargs)
        self.cls = cls
        self.args_spec = args_spec
        self.kwargs_spec = kwargs_spec

        assert not (self.kwargs_spec and self.args_spec), (
            '`kwargs_spec` and `args_spec` are mutually exclusive')

        self.args_instance = args_instance
        self.kwargs_instance = kwargs_instance

        assert not (self.kwargs_instance and args_instance), (
            '`kwargs_instance` and `args_instance` are mutually exclusive')

        self.args_spec_name = args_spec_name
        self.args_instance_name = args_instance_name
        self.kwargs_spec_mapping = kwargs_spec_mapping or {}

    def _build_as_args(self, instance, spec):
        kwargs = {}
        if self.args_instance:
            kwargs[self.args_instance_name] = instance
        if self.args_spec:
            kwargs[self.args_spec_name] = spec
        return kwargs

    def _build_as_kwargs(self, instance, spec):
        kwargs = {}
        if self.kwargs_spec:
            assert isinstance(spec, dict), (
                'spec must be a \'dict\' if `kwargs_spec` is set as `True`,'
                ' {!r}.'.format(type(spec)))
            kwargs.update({self.kwargs_spec_mapping.get(k, k): v
                           for k, v in spec.iteritems() if k != '.meta'})
        if self.kwargs_instance:
            assert isinstance(instance, dict), (
                'instance must be a \'dict\' if `kwargs_instance` is set as'
                ' `True`, not {!r}'.format(type(instance)))
            kwargs.update(instance)
        return kwargs

    def construct(self, context, **meta):
        instance = context.instance
        spec = context.spec
        args = self._build_as_args(instance, spec)
        kwargs = self._build_as_kwargs(instance, spec)
        conflict_keys = []
        for p, u in itertools.combinations([args, kwargs, meta], 2):
            conflict_keys.extend(set(p.keys()).intersection(u.keys()))
        if conflict_keys:
            raise ConflictError('Multiple occurences of keys: ({!s})'.format(
                ','.join(set(conflict_keys))))
        kwargs.update(args)
        # Pass meta, i.e. the return value of the 'pre_hook' callable as
        # extra keyword arguments to the class.
        kwargs.update(meta)
        return self.cls(**kwargs)


class Flag(Constructor):
    """
    This constructor attaches a flag at the current instance.

    Specifically, it adds a new key to instance with a value set as `True`.

    Args:
        flag_name (str): Name of the flag (i.e. key) to be added to the
            intance.

    Examples:
        >>> from apimas.constructors import Flag
        >>> from apimas.testing.helpers import create_mock_constructor_context
        >>> instance = {'foo': 'bar'}
        >>> context = create_mock_constructor_context(instance=instance)
        >>> flag_constructor = Flag('myflag')
        >>> flag_constructor.construct(context)
        {'boo': 'bar', 'myflag': True}
    """
    def __init__(self, flagname, *args, **kwargs):
        self.flagname = flagname
        super(Flag, self).__init__(*args, **kwargs)

    def construct(self, context, **meta):
        if self.flagname in context.instance:
            msg = 'Key {!r} already exists in the instance'
            raise ConflictError(msg.format(self.flagname))
        doc = {self.flagname: True}
        context.instance.update(doc)
        return context.instance


class Dummy(Constructor):
    """
    A naive constructor that simply returns the current instance.
    """

    def construct(self, context, **meta):
        return context.instance
