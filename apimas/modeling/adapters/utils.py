def default_constructor(predicate):
    def construct_predicate(instance, spec, loc, top_spec):
        raise NotImplementedError('construct_%s() must be implemented' % (
            predicate[1:]))
    return construct_predicate
