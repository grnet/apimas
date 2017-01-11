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
        '.biginteger',
        '.string',
        '.email',
        '.boolean',
        '.datetime',
        '.date',
        '.file',
        '.identity',
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
        '.biginteger',
        '.float',
        '.string',
        '.email',
        '.boolean',
        '.datetime',
        '.date',
        '.file',
        '.identity',
    ])

    PROPERTIES = frozenset([
        '.blankable',
        '.required',
        '.nullable',
        '.readonly',
        '.writeonly',
    ])

    def construct(self, spec):
        raise NotImplementedError('`gen_adapter_spec()` must be implemented')

    def apply(self):
        raise NotImplementedError('`apply()` must be implemeneted')

    def get_constructors(self):
        return {predicate[1:]: getattr(
            self, self.CONSTRUCTOR_PREFIX + '_' + predicate[1:],
            utils.default_constructor(predicate))
                for predicate in self.PREDICATES}
