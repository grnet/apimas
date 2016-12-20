"""Standard validating constructor library

Constructors in this module validate value constraints, normalize values.

Optionally, constructors can create random conforming values.

"""
import sys
from random import choice, randint
import re

from documents import (
    register_constructor, doc_construct, doc_value,
    ValidationError, InvalidInput,
)


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
        flags = re.UNICODE
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
