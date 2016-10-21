from documents import (
    register_constructor, doc_construct,
    ValidationError, InvalidInput,
)


@register_constructor
def construct_integer(instance, spec, loc):
    if isinstance(instance, (int, long)):
        val = instance

    elif isinstance(instance, basestr):
        if not instance.isdigit():
            m = "{loc}: {instance!r} is not an integer"
            m = m.format(loc=loc, instance=instance)
            raise ValidationError(m)

        val = int(instance)

    else:
        m = "{loc!r}: cannot make an integer out of {instance!r}"
        m = m.format(loc=loc, instance=instance)
        raise ValidationError(m)

    min = spec.get('min')
    if min is not None and val < min:
        m = "{loc}: integer {instance!r} less than min {min!r}"
        m = m.format(loc=loc, instance=instance, min=min)
        raise ValidationError(m)

    max = spec.get('max')
    if max is not None and val > max:
        m = "{loc}: integer {instance!r} greater than max {max!r}"
        m = m.format(instance=instance, min=min)
        raise ValidationError(m)

    return val


@register_constructor
def construct_text(instance, spec, loc):

    blankable = spec.get('blankable', True)
    regex = spec.get('regex', None)
    encoding = spec.get('encoding', 'utf-8')

    if isinstance(instance, str):
        text = instance.decode(encoding)

    elif isinstance(instance, unicode):
        text = instance

    else:
        m = "{loc}: text {instance!r} is neither str nor unicode"
        m = m.format(loc=loc, instance=instance)
        raise ValidationError(m)

    if not blankable and not text:
        m = "{loc}: text cannot be blank"
        m = m.format(loc=loc)
        raise ValidatorError(m)

    if regex is not None:
        flags = re.UNICODE
        pattern = re.compile(regex, re.UNICODE)
        if pattern.match(instance) is None:
            m = "{loc}: {instance!r} does not match regex {regex!r}"
            m = m.format(loc=loc, instance=instance, regex=regex)
            raise ValidationError(m)

    return text
