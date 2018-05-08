from apimas.adapters import utils


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
        '.text',
        '.choices',
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
        '.actions',
    ])

    TYPES = frozenset([
        '.struct',
        '.structarray',
        '.ref',
        '.serial',
        '.integer',
        '.biginteger',
        '.float',
        '.decimal',
        '.string',
        '.text',
        '.choices',
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

    def get_constructors(self):
        return {predicate[1:]: getattr(
            self, self.CONSTRUCTOR_PREFIX + '_' + predicate[1:],
            utils.default_constructor(predicate))
                for predicate in self.PREDICATES}
