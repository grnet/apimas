from documents import (
    register_constructor, doc_construct, doc_value,
    ValidationError, InvalidInput,
)


@register_constructor
def construct_integer(instance, spec, loc):

    val = doc_value(instance)

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

    min = spec.get('min')
    if min is not None and val < min:
        m = "{loc}: integer {val!r} less than min {min!r}"
        m = m.format(loc=loc, val=val, min=min)
        raise ValidationError(m)

    max = spec.get('max')
    if max is not None and val > max:
        m = "{loc}: integer {instance!r} greater than max {max!r}"
        m = m.format(val=val, min=min)
        raise ValidationError(m)

    return val


@register_constructor
def construct_text(instance, spec, loc):

    blankable = spec.get('blankable', True)
    regex = spec.get('regex', None)
    encoding = spec.get('encoding', 'utf-8')

    text = doc_value(instance)

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

    return text
