"""Standard validating constructor library

Constructors in this module validate value constraints, normalize values.

Optionally, constructors can create random conforming values.

"""
import sys
from random import choice, randint
import re
import importlib

from docular import doc_get

from spec import (
    doc_spec_register_predicate,
    doc_spec_register_constructor,
    doc_spec_get,
    instance_get_val_or_skip,
    Error,
    ValidationError,
    SkipConstructor,
    Null,
)


MAXINT = sys.maxint
MININT = -sys.maxint - 1


number_spec = {
    '.number': {},
}


def construct_number(instance):
    val = instance_get_val_or_skip(instance)
    instance['='] = int(val)



integer_spec = {
    '.integer': {
        'min': {
            '.number': {
                '*': None,
            },
            'documentation': {
                '=': 'minimum permitted value',
            },
        },
        'max': {
            '.number': {
                '*': None,
            },
            'documentation': {
                '=': 'maximum permitted value',
            },
        },
        'randomize': {
            '.bool': {},
            'documentation': {
                '=': ('create a random conforming value '
                      'if instance provides no value'),
            },
        },
    },
}


def construct_integer(predicate, instance, loc):
    """Construct and validate a python int/long.

    Constructor parameters:

        min:
            minimum permitted value

        max:
            maximum permitted value

        randomize:
            create a random conforming value if instance provides no value

    """
    val = instance_get_val_or_skip(instance)
    args = instance[predicate]
    min = doc_spec_get(args, 'min')
    max = doc_spec_get(args, 'max')
    randomize = doc_spec_get(args, 'randomize')

    if val is None:
        if randomize:
            _min = MININT if min is None else min
            _max = MAXINT if max is None else max
            val = randint(_min, _max)
        else:
            return

    if isinstance(val, basestring):
        if not val.isdigit():
            m = "data given not made of integer digits"
            raise ValidationError(loc=loc, data=instance, message=m)

        val = int(val)

    elif not isinstance(val, (int, long)):
        m = "cannot make out an integer out of data given"
        raise ValidationError(loc=loc, data=val, message=m)

    if min is not None and val < min:
        m = "integer {val!r} less than min {min!r}"
        m = m.format(val=val, min=min)
        raise ValidationError(loc=loc, data=(val, min), message=m)

    if max is not None and val > max:
        m = "integer {val!r} greater than max {max!r}"
        m = m.format(val=val, max=max)
        raise ValidationError(loc=loc, data=(val, max), message=m)

    return val


string_spec = {
    '.string': {},
}


def construct_string(instance):
    val = instance_get_val_or_skip(instance)
    instance['='] = str(val)


bool_spec = {
    '.bool': {},
}


def construct_bool(instance):
    val = instance_get_val_or_skip(instance)
    instance['='] = bool(val)


text_spec = {
    '.string': {},
    '.text': {
        'minlen': {
            '.integer': {
                'min': 0,
            },
            'documentation': {
                '=': 'minimum permitted character length',
            },
        },
        'maxlen': {
            '.integer': {
                'min': 0,
            },
            'documentation': {
                '=': 'maximum permitted character length',
            },
        },
        'regex': {
            '.string': {},
            'documentation': {
                '=': 'a regular expression to be matched against the value',
            },
        },
        'alphabet': {
            '.string': {},
        },
        'excluded': {
            '.string': {},
            'documentation': {
                '=': 'a string of individually allowed characters',
            },
        },
        'encoding': {
            '.string': {},
            'documentation': {
                '=': 'if given, use it to decode string to unicode',
            },
        },
        'randomize': {
            'documentation': {
                '=': ('create a random conforming value '
                      'if instance provides no value'),
            },
            '.bool': {},
        },
    },
}


_text_default_alphabet = b''.join(chr(x) for x in xrange(256))


def construct_text(predicate, instance, loc):
    """Construct and validate a python str/unicode.

    Constructor parameters:

        minlen:
            minimum permitted character length

        maxlen:
            maximum permitted character length

        regex:
            a regular expression to be matched against the value

        alphabet:
            a string of individually allowed characters

        excluded:
            a string of individually forbidden chars

        encoding:
            if given, use it to decode string to unicode

        randomize:
            create a random conforming value if instance provides no value

    """
    text = instance_get_val_or_skip(instance)
    args = instance[predicate]
    regex = doc_spec_get(args, 'regex')
    encoding = doc_spec_get(args, 'encoding', 'utf-8')
    minlen = int(doc_spec_get(args, 'minlen', 0))
    maxlen = int(doc_spec_get(args, 'maxlen', MAXINT))
    alphabet = doc_spec_get(args, 'alphabet', None)
    excluded = doc_spec_get(args, 'excluded', '')
    randomize = doc_spec_get(args, 'randomize')

    if text is None:
        if randomize:
            if alphabet is None:
                alphabet = _text_default_alphabet

            if regex is not None:
                m = "{loc!r}: cannot randomize when 'regex' is given"
                m = m.format(loc=loc)
                raise NotImplementedError(m)

            if excluded:
                alphabet = ''.join(set(alphabet) - set(excluded))

            text = ''.join(choice(alphabet)
                           for _ in xrange(randint(minlen, maxlen)))
        else:
            return

    if isinstance(text, str) and encoding is not None:
        text = text.decode(encoding)

    elif not isinstance(text, unicode):
        m = "text data is neither str nor unicode"
        m = m.format(loc=loc, data=text, message=m)
        raise ValidationError(m)

    if regex is not None:
        pattern = re.compile(regex, re.UNICODE)
        if pattern.match(text) is None:
            m = "text data does not match regex {regex!r}"
            m = m.format(regex=regex)
            raise ValidationError(loc=loc, data=text, message=m)

    text_len = len(text)
    if text_len < minlen:
        m = "text data length {len!r} less than minlen {minlen!r}"
        m = m.format(len=len, minlen=minlen)
        raise ValidationError(loc=loc, data=text, message=m)

    if maxlen is not None and text_len > maxlen:
        m = "text data length {len!r} greater than maxlen {maxlen!r}"
        m = m.format(len=len, maxlen=maxlen)
        raise ValidationError(loc=loc, data=text, message=m)

    if alphabet is not None:
        alphabet = ''.join(set(alphabet) - set(excluded))
        for c in text:
            if c not in alphabet:
                m = "char {c!r} in text data is not in alphabet {alphabet!r}"
                m = m.format(c=c, alphabet=alphabet)
                raise ValidationError(loc=loc, data=text, message=m)

    elif excluded:
        for c in excluded:
            if c in text:
                m = "forbidden char {c!r} found in text data"
                m = m.format(c=c)
                raise ValidationError(loc=loc, data=text, message=m)

    return text


object_spec = {
    '.object': {},
    'class': {
        '.string': {},
    },
    'args': {},
}


def construct_object(predicate, instance, loc):
    classpath = doc_spec_get(instance, 'class')
    modulepath, sep, classname = classpath.partition(':')
    try:
        module = importlib.import_module(modulepath)
    except ImportError as e:
        m = "Error loading module {modulepath!r}: {msg!r}"
        m = m.format(modulepath=modulepath, msg=str(e))
        raise ValidationError(loc=loc, data=classpath, message=m)

    classtype = getattr(module, classname, None)
    if classtype is None:
        m = "Cannot find {classname!r} in module {modulepath!r}"
        m = m.format(classname=classname, modulepath=modulepath)
        raise ValidationError(loc=loc, data=classpath, message=m)

    val = doc_spec_get(instance, default=Null)
    if val is not Null:
        if not isinstance(val, classtype):
            m = ("Existing object {obtype!r} "
                 "is not an instance of {classpath!r}")
            m = m.format(obtype=type(val), classpath=classpath)
            raise ValidationError(loc=loc, data=val, message=m)
        return

    args = doc_get(instance, (predicate, 'args'))
    if args is None:
        raise SkipConstructor()

    kwargs = {k: v for k, v in args if k[0:1] not in '.=*'}
    try:
        val = classtype(**kwargs)
    except Exception as e:
        m = "Error constructing {classpath!r}: {msg!r}"
        m = m.format(classpath=classpath, msg=str(e))
        raise ValidationError(loc=loc, data=(classpath, kwargs), message=m)

    instance['='] = val


predicates = {}

constructors = {}


doc_spec_register_predicate(predicates, '.bool', bool_spec)
doc_spec_register_constructor(constructors, '.bool', construct_bool)

doc_spec_register_predicate(predicates, '.string', string_spec)
doc_spec_register_constructor(constructors, '.string', construct_string)

doc_spec_register_predicate(predicates, '.number', number_spec)
doc_spec_register_constructor(constructors, '.number', construct_number)

doc_spec_register_predicate(predicates, '.integer', integer_spec)
doc_spec_register_constructor(constructors, '.integer', construct_integer)

doc_spec_register_predicate(predicates, '.text', text_spec)
doc_spec_register_constructor(constructors, '.text', construct_text)

doc_spec_register_predicate(predicates, '.object', object_spec)
doc_spec_register_constructor(constructors, '.object', construct_object)
