def mock_constructor(predicate):
    def construct_predicate(instance, spec, loc, top_spec):
        raise NotImplementedError('construct_%s() must be implemented' % (
            predicate[1:]))
    return construct_predicate


class Adapter(object):
    CONSTRUCTOR_PREFIX = 'construct'

    PREDICATES = frozenset([
        '.endpoint',
        '.collection',
        '.resource',
        '.action',
        '.list',
        '.retrieve',
        '.create',
        '.update',
        '.delete',
        '.struct',
        '.structarray',
        '.ref',
        '.serial',
        '.integer',
        '.big_integer',
        '.string',
        '.boolean',
        '.datetime',
        '.date',
        '.blankable',
        '.required',
        '.nullable',
        '.readonly',
        '.writeonly',
        '.indexable',
    ])

    def construct(self, spec):
        raise NotImplementedError('`gen_adapter_spec()` must be implemented')

    def apply(self):
        raise NotImplementedError('`apply()` must be implemeneted')

    def get_constructors(self):
        return {predicate: getattr(
            self, self.CONSTRUCTOR_PREFIX + '_' + predicate[1:],
            mock_constructor(predicate))
                for predicate in self.PREDICATES}
