from apimas.modeling.adapters import utils


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

    TYPES = frozenset([
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
    ])

    PROPERTIES = frozenset([
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
            utils.default_constructor(predicate))
                for predicate in self.PREDICATES}
