from documents import (
    register_constructor, doc_construct, doc_value,
    ValidationError, InvalidInput,
)

from random import choice, randint
import re


@register_constructor
def construct_integer(instance, spec, loc, top_spec):

    min = spec.get('min', None)
    max = spec.get('max', None)
    val = doc_value(instance)

    if val is None and '.randomize' in spec:
        _min = -2**32 if min is None else min
        _max = 2**32 if max is None else max
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


@register_constructor
def construct_text(instance, spec, loc, top_spec):

    blankable = spec.get('blankable', True)
    regex = spec.get('regex', None)
    encoding = spec.get('encoding', 'utf-8')
    minlen = int(spec.get('minlen', 0))
    maxlen = int(spec.get('maxlen', 2**63))
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

        text = ''.join(choice(alphabet) for _ in xrange(randint(minlen, maxlen)))

    if isinstance(text, str):
        text = text.decode(encoding)

    elif isinstance(text, unicode):
        m = "{loc}: text {text!r} is neither str nor unicode"
        m = m.format(loc=loc, text=text)
        raise ValidationError(m)

    if not blankable and not text:
        m = "{loc}: text cannot be blank"
        m = m.format(loc=loc)
        raise ValidatorError(m)

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
