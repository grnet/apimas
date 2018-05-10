"""Docular specification toolkit.

Specify, configure, and construct objects using documents.

"""

from inspect import getargspec
from collections import Sequence, MutableMapping, defaultdict
from copy import deepcopy
from types import FunctionType
from bisect import insort, bisect_right

from errors import (
    collect_error,
    Error,
    NotFound,
    ValidationError,
    InvalidInput,
    ConflictError,
)


class MergeFault(ConflictError):
    pass


Null = type('Null', (), {'__repr__': lambda self: 'Null'})()


def doc_spec_get(spec, key='=', default=None):
    if key not in spec:
        return default

    val = spec[key]
    if key == '=':
        return val

    if not isinstance(val, MutableMapping):
        return val

    if '=' not in val:
        return default

    return val['=']


def doc_spec_set(spec, key=Null, val=Null):
    if spec.get('=p'):
        m = "cannot write {key!r}={val!r} to protected spec\n"
        raise ConflictError(m)

    if key is Null:
        key = '='

    if val is Null:
        val = key
        key = '='

    oldval = spec[key] if key in spec else Null
    if key == '=':
        spec[key] = val
    else:
        spec[key] = doc_spec_normalize_val(val)

    return oldval


def doc_spec_normalize_val(val):
    if isinstance(val, MutableMapping):
        val_spec = val
    elif val is None:
        val_spec = None
    elif isinstance(val, Sequence) and not isinstance(val, basestring):
        if val:
            # assume keys are hashable
            val_spec = {key: {} for key in val}
            val_spec['=keys'] = list(val)
        else:
            val_spec = val
    else:
        val_spec = {'=': val}

    return val_spec


def doc_spec_iter(spec, what='_'):
    if not spec:
        return

    if '=d' not in spec:
        m = "document has not been compiled as spec"
        raise InvalidInput(data=spec, message=m)

    data_keys_ok = '_' in what
    pattern_keys_ok = '*' in what
    predicate_keys_ok = '.' in what

    for k in spec['=k']:
        first = k[:1]
        if first == '=':
            continue

        if first == '.':
            if not predicate_keys_ok:
                continue
        elif not data_keys_ok:
            continue

        last = k[-1:]
        if last == '*' and not pattern_keys_ok:
            continue

        yield k, spec[k]


def doc_spec_iter_values(spec):
    for key, subspec in doc_spec_iter(spec):
        yield key, doc_spec_get(subspec)


class DeferConstructor(Exception):
    """An exception raised by constructors to defer their execution."""


class SkipConstructor(Exception):
    """An exception raised by constructors to skip their execution."""


cons_context_fields = frozenset((
    'instance',
    'loc',
    'round',
    'top_spec',
    'config',
    'predicate',
    'predicates',
    'constructors',
    'constructed',
    'errs',
))


def make_constructor(constructor):
    if isinstance(constructor, FunctionType):
        fn = constructor
        fn_module = constructor.__module__
        args = getargspec(fn).args
        fn_name = constructor.func_name
    elif callable(constructor) and hasattr(constructor, '__call__'):
        fn = constructor.__call__
        args = getargspec(fn).args[1:]
        fn_name = constructor.__class__.__name__
        fn_module = constructor.__call__.__module__
    else:
        m = "{constructor!r}: not a FunctionType or callable"
        m = m.format(constructor=constructor)
        raise InvalidInput(m)

    if args == ['context']:
        return constructor

    unknown_args = set(args) - cons_context_fields
    unknown_args.discard('context')

    if unknown_args:
        m = ("{name!r}: unknown constructor arguments: {unknown_args!r}. "
             "the available context fields are {cons_context_fields!r}.")
        m = m.format(name=fn_module + '.' + fn_name,
                     unknown_args=list(unknown_args),
                     cons_context_fields=cons_context_fields)
        raise InvalidInput(m)

    def final_constructor(context):
        kwargs = {name: context[name] for name in args}
        if 'context' in kwargs:
            kwargs['context'] = context
        return fn(**kwargs)

    final_constructor.func_name = fn_name
    return final_constructor


class protected_dict(dict):

    def __setitem__(self, key, val):
        protected = '=k' in self
        if protected:
            m = "cannot write to key {key!r}, protected_dict is protected"
            m = m.format(key=key)
            raise ConflictError(m)

        return dict.__setitem__(self, key, val)

    def __delitem__(self, key):
        protected = '=k' in self
        if protected:
            m = "cannot delete key {key!r}, protected_dict is protected"
            m = m.format(key=key)
            raise ConflictError(m)

        return dict.__delitem__(self, key)

    def clear(self):
        protected = '=k' in self
        if protected:
            m = "cannot clear() frozendict"
            raise ConflictError(m)

        return dict.__clear__(self)

    def update(self, data):
        protected = '=k' in self
        if protected:
            m = "cannot update() frozendict"
            raise ConflictError(m)

        return dict.__update__(self, data)


def doc_compile_spec(source, predicates,
                     autoregister=True, merge=None,
                     loc=()):

    """Compile a source document into a new specification document.

    Args:
        spec (dict):
            A source specification document 

        predicates (dict):
            The predicate specification registry to be used to merge in
            dependencies during compilation.

        merge (callable):
            A function with two arguments, returning one,
            called to merge two differing document node values into one.
            If false, any differing values cause the compilation to abort.

        autoregister(bool):
            Any dependency that is not found in the registry
            is automatically registered with the the current node
            as its specification.

        loc (tuple):
            A tuple of path segments (byte strings) to be used as a prefix
            and passed on to recursive call so that the path from the top-level
            spec document to the current node is always available for
            introspection.

    Returns:
        dict: compiled specification document


    Source specification document form:
        A source specification document (source spec doc)
        is expected to be a dict with additional constraints:

        1. All keys are byte strings

        2. Keys starting with '=' are special, the rest are normal

        3. The special keys are:

            '='     -> an arbitrary value to be assigned to the document node
            '=keys' -> a list of any subset of the normal keys,
                       causing any iteration of the document to start
                       with those keys, in the specific given order

        4. All normal key values that are not MutableMapping are normalized
           in the following way:
            - lists are converted into source documents with keys having empty
              document values, retaining the original list order through '=keys'
            - the rest are converted into source documents that have the value
              assigned at the node level via '='


    Specification document form:
        A compiled specification document (spec doc)
        is expected to be a dict with additional constraints:

        1. All keys are byte strings

        2. Keys starting with '=' are special,
           keys ending with '*' are prefixes,
           the rest are normal.

        3. All normal and prefix keys have values that are
           compiled specification documents themselves.

        4. The special keys with a meaning are:

            '=d' -> a list of normal and prefix keys that are predicate
                    dependencies for the surrounding node
            '=x' -> an index (sorted list) for prefix keys
            '=k' -> a list of all normal and prefix keys in the merge order
            '=p' -> a boolean value which if true
                    protects the spec from any modification
            '=errs' -> a list of errors occured during compilation
            '='  -> an arbitrary value to be assigned to the document node

        5. An empty list as a value to a special key except '=' is replaced by
           the empty tuple to reduce memory consumption and access time.

        6. If key '=' does not exist and all special key values are empty
           then the specification document is represented by an empty dict or
           tuple


    Compilation specification:
        1. The compiled specification document is initialized empty

        2. The merge order of the compiled spec is created thus:
            a. The keys from the source '=keys' are placed as is at the
               beginning of the merge order.
            b. All normal keys are lexicographically sorted and placed
               next in the merge order
            c. All prefix keys are reverse lexicographically sorted
               and placed next in the merge order
            d. Multiple keys are removed by only keeping the first

        3. For each key in the merge order:
            a. Normalize the key value
            b. If the key starts with '.' it is appended as a predicate
               dependency and:
                i.  If the predicate exists in the registry, it is recursively
                    merged into the current node.
                ii. If the predicate does not exist in the registry, it is
                    ignored until the compilation of the current node is
                    complete, and then it is registered as a predicate
                    using the newly compiled node as its specification
            c. If the key does not start with '.' its value is recursively
               compiled as a specification and then merged into the current
               node.

        4. The value for '=', if it exists, is transferred directly to the
           compiled document.

    """

    spec = {}
    errs = []
    spec = doc_spec_merge(spec, source,
                          predicates=predicates,
                          extend=True, merge=merge,
                          autoregister=autoregister,
                          loc=loc, errs=errs)
    if errs:
        m = "Cannot compile spec"
        raise Error(data=spec, loc=loc, message=m, errs=errs)

    return spec


def doc_copy_spec(spec):
    new_spec = {
        k: (deepcopy(v) if k[:1] == '=' else v)
        for k, v in spec.iteritems()
    }
    new_spec.pop('=p', None)
    return new_spec


def doc_strip_spec(spec):
    if '=d' not in spec:
        m = "Document has not been compiled as spec"
        raise InvalidInput(m)

    if '=' in spec:
        return spec['=']

    doc = {}

    for key, val in spec.iteritems():
        if key[0:1] == '=':
            continue

        if val is None:
            subdoc = None
        elif '=' in val:
            subdoc = val['=']
        elif not val:
            subdoc = {}
        else:
            subdoc = doc_strip_spec(val)

        doc[key] = subdoc

    return doc


def doc_spec_register_constructor(constructors, predicate, constructor_fn):
    constructor = make_constructor(constructor_fn)
    if predicate in constructors:
        m = "{predicate!r}: constructor exists"
        m = m.format(predicate=predicate)
        raise ConflictError(m)

    constructors[predicate] = constructor


def doc_spec_init_constructor_registry(constructors, default=None):
    if default:
        default = lambda: make_constructor(default)
    registry = defaultdict(default)

    for key, constructor in constructors.iteritems():
        doc_spec_register_constructor(registry, key, constructor)
    return registry


def doc_spec_register_predicate(predicates, predicate, spec):

    if predicate in predicates:
        m = "{predicate!r}: spec exists"
        m = m.format(predicate=predicate)
        raise ConflictError(m)

    predicates[predicate] = deepcopy(spec)

    ## # add this empty predicate first to allow spec depend to itself
    ## # this will be overwritten after the compile is complete
    ## predicates[predicate] = {
    ##     '=d': (),
    ##     '=k': (),
    ##     '=x': (),
    ## }

    ## registered_spec = doc_compile_spec(spec, predicates, autoregister=False)

    ## if '=k' in spec and spec != registered_spec:
    ##     m = "Cannot register spec, it is not idempotent."
    ##     raise Error(data=(spec, registered_spec), message=m)

    ## predicates[predicate] = registered_spec


def doc_spec_registry_verify_non_shared_meta(predicates):
    meta_ids = set()

    for key in predicates.iterkeys():
        spec = predicates[key]

        for meta_name in ('=k', '=d', '=x'):
            meta_id = id(spec[meta_name])
            assert meta_id not in meta_ids
            meta_ids.add(meta_id)


def doc_spec_config(spec, config_spec, predicates,
                    merge=None, loc=()):

    instance_spec = doc_compile_spec(spec, predicates,
                                     autoregister=False, merge=merge,
                                     loc=loc)

    errs = []
    doc_spec_merge(instance_spec, config_spec,
                   predicates=predicates,
                   autoregister=False, extend=False, merge=merge,
                   loc=loc, errs=errs)

    if errs:
        m = "Error in configuring spec"
        raise Error(loc=loc, data=instance_spec, message=m, errs=errs)

    return instance_spec


def doc_spec_construct(spec_instance, predicates, constructors,
                       top_spec=None, config=(), loc=()):

    if top_spec is None:
        top_spec = spec_instance

    errs = []
    config_source = {}
    source_keys = doc_spec_get_source_keys(spec_instance)
    construct_keys = []

    for key in source_keys:
        subspec = spec_instance[key]

        if subspec is None:
            # None subspec meaning no value allowed: reproduce
            subdoc = None
        elif not subspec:
            # empty subspec meaning any value: reproduce in instance
            subdoc = {}
        else:
            # any other value must be a dict or MutableMapping form
            # that will be used as specification to construct the subdoc
            construct_keys.append(key)
            subdoc = subspec

        spec_instance[key] = subdoc

        if key[:1] == ':':
            config_source[key] = subdoc

    new_config = doc_compile_spec(config_source, predicates)
    errs = []
    new_config = doc_spec_merge(new_config, config, predicates,
                                extend=True, merge=None, autoregister=False,
                                loc=loc, errs=errs)
    errs = [x for x in errs if x.what != 'value-mismatch']
    if errs:
        m = "Construction failed in configuration"
        raise Error(message=m, loc=loc, errs=errs)

    for key in construct_keys:
        subspec = spec_instance[key]
        try:
            doc_spec_construct(subspec, predicates, constructors,
                               top_spec=top_spec,
                               config=new_config,
                               loc=loc + (key,))
        except Error as e:
            collect_error(errs, e)

    if errs:
        m = "Construction failed"
        raise Error(loc=loc, errs=errs, message=m)

    doc_spec_call_constructors(spec_instance, predicates, constructors,
                               new_config, errs, loc, top_spec)

    if errs:
        m = "Construction failed in constructors"
        raise Error(loc=loc, errs=errs, message=m)


def doc_construct(spec, config, predicates, constructors,
                  merge=None):

    spec_instance = doc_spec_config(spec, config, predicates,
                                    merge=merge)

    doc_spec_construct(spec_instance, predicates, constructors)

    return spec_instance


def doc_spec_call_constructors(instance, predicates, constructors,
                               config, errs, loc, top_spec):

    working_predicates = instance.get('=d', ())

    config_keys = [k
                   for k in doc_spec_get_source_keys(config)
                   if k in instance]
    cons_config = {k: config[k] for k in config_keys}

    # create the appearance of a spec,
    # but with disabled dependencies and prefixes
    cons_config['=d'] = ()
    cons_config['=k'] = config_keys
    cons_config['=x'] = ()

    context = {
        'instance': instance,
        'loc': loc,
        'top_spec': top_spec,
        'config': cons_config,
        'local_predicates': working_predicates,
        'predicates': predicates,
        'constructors': constructors,
        'constructed': set(),
        'round': 0,
        'errs': errs,
        'context': None,
    }

    skipped_predicates = []
    old_deferred_predicates = None
    while True:
        deferred_predicates = []
        for predicate in working_predicates:
            try:
                constructor = constructors[predicate]
            except KeyError:
                m = "cannot find constructor {predicate!r}"
                m = m.format(predicate=predicate)
                e = NotFound(loc=loc, data=predicate, message=m)
                collect_error(errs, e)
                continue

            context['predicate'] = predicate

            try:
                constructor(context=context)
                context['constructed'].add(predicate)
            except SkipConstructor:
                skipped_predicates.append(predicate)
            except DeferConstructor:
                deferred_predicates.append(predicate)
            except Error as e:
                collect_error(errs, e)
                continue

        if not deferred_predicates:
            break

        if deferred_predicates == old_deferred_predicates:
            m = "{loc!r}/{predicate!r}: constructor deadlock {deferred!r}"
            m = m.format(loc=loc, predicate=predicate,
                         deferred=deferred_predicates)
            raise InvalidInput(m)

        old_deferred_predicates = deferred_predicates
        working_predicates = deferred_predicates
        context['round'] += 1

    return skipped_predicates


def doc_spec_get_source_keys(source):
    if '=k' in source:
        return source['=k']

    keys = list(source['=keys']) if '=keys' in source else []
    keys_set = set(keys)
    prefix_keys = []
    normal_keys = []

    for k in source.iterkeys():
        s = k[:1]
        if k[-1:] == '*':
            if k not in keys_set:
                prefix_keys.append(k)
            continue
        if s == '=':
            continue
        if k not in keys_set:
            normal_keys.append(k)

    prefix_keys.sort()
    prefix_keys.reverse()
    normal_keys.sort()
    keys.extend(normal_keys)
    keys.extend(prefix_keys)
    return keys


def doc_spec_unpack(spec, loc=()):
    if not spec:
        spec = {}
    elif not '=k' in spec:
        m = "document not compiled as spec"
        raise InvalidInput(loc=loc, data=spec, message=m)

    spec['=k'] = spec.get('=k') or []
    spec['=d'] = spec.get('=d') or []
    spec['=x'] = spec.get('=x') or []

    return spec


def doc_spec_pack(spec):

    spec['=k'] = spec['=k'] or ()
    spec['=d'] = spec['=d'] or ()
    spec['=x'] = spec['=x'] or ()

    return () if not spec['=k'] and '=' not in spec else spec


def doc_spec_merge(target_spec, source, predicates,
                   extend, merge, autoregister,
                   loc, errs, top_target=None, pack=True):

    if not source:
        return target_spec

    if not target_spec or not target_spec.get('=k'):
        extend = True

    if pack:
        target_spec = doc_spec_unpack(target_spec)

    if top_target is None:
        top_traget = target_spec

    if '=p' in target_spec:
        if '=p' in top_target:
            m = "Cannot merge into protected top target"
            raise InvalidInput(loc=loc, data=top_target, message=m)

        # this will descend from top_target to target_spec,
        # copying any '=p'-protected parents in the way.
        cur_doc = top_target
        for segment in loc:
            sub_doc = cur_doc[segment]
            if '=p' in sub_doc:
                new_doc = doc_copy_spec(sub_doc)
                cur_doc[segment] = new_doc
                cur_doc = new_doc
            else:
                cur_doc = sub_doc

        target_spec = cur_doc

    # merge value

    doc_spec_merge_value(target_spec, source, merge=merge,
                         errs=errs, loc=loc)

    # merge subdocuments

    register_keys = [] if autoregister else None

    for key in doc_spec_get_source_keys(source):
        target_spec = doc_spec_merge_key(
            target_spec, source, key,
            extend=extend, merge=merge, predicates=predicates,
            loc=loc, errs=errs,
            top_target=top_target,
            register_keys=register_keys)

    if pack:
        target_spec = doc_spec_pack(target_spec)

    if register_keys:
        for key in register_keys:
            segments = key.split('.')
            for i in xrange(2, len(segments) + 1):
                predicate = '.'.join(segments[:i])
                if predicate in predicates:
                    continue
                doc_spec_register_predicate(predicates, predicate, target_spec)

    return target_spec


def doc_spec_ensure_target_key(target_spec, key,
                               extend, merge, predicates,
                               loc, errs, top_target, register_keys):

    subtarget = target_spec.get(key, Null)
    if subtarget is not Null:
        return target_spec, None

    autoregister = register_keys is not None

    # search key in wildcard prefixes and if matched
    # schedule key and prefix for recursion
    target_prefixes = target_spec['=x']
    index = bisect_right(target_prefixes, key) - 1
    if index >= 0:
        for i in xrange(index, -1, -1):
            prefix_key = target_prefixes[i]
            if key.startswith(prefix_key):
                subtarget = deepcopy(target_spec[prefix_key + '*'])
                break

    if subtarget is Null:
        if not extend:
            m = "cannot match key {key!r}"
            m = m.format(key=key)
            e = MergeFault(
                loc=loc,
                what='no-key',
                data=target_spec,
                message=m)
            collect_error(errs, e)
            return target_spec, e

        subtarget = ()

    if key[:1] == '.':
        # new key is a predicate
        segments = key.split('.')
        for i in xrange(2, len(segments) + 1):
            # require all '.'-separated subprefixes
            predicate = '.'.join(segments[:i])
            if predicate in target_spec:
                # sub-prefix already exists, don't merge a second time
                continue

            target_spec['=d'].append(predicate)
            target_spec['=k'].append(predicate)
            if predicate[-1:] == '*':
                insort(target_spec['=x'], predicate[:-1])

            target_spec[predicate] = deepcopy(subtarget)

            if predicate in predicates:
                target_spec = doc_spec_merge(
                    target_spec, predicates[predicate],
                    predicates=predicates,
                    extend=True, merge=merge,
                    autoregister=autoregister,
                    loc=loc, errs=errs,
                    top_target=top_target, pack=False)
            else:
                if register_keys is None:
                    m = "{predicate!r}: predicate not found"
                    m = m.format(predicate=predicate)
                    e = MergeFault(loc=loc, what='no-predicate',
                                   data=key, message=m)
                    collect_error(errs, e)
                else:
                    register_keys.append(predicate)

    else:
        if key[-1:] == '*':
            insort(target_spec['=x'], key[:-1])

        target_spec['=k'].append(key)
        target_spec[key] = subtarget

    return target_spec, None


def doc_spec_merge_subsource(target_spec, source, key,
                             extend, merge, predicates,
                             loc, errs, top_target, register_keys):
    subsource = source[key]
    subtarget = target_spec[key]
    autoregister = register_keys is not None

    # shouldn't reference subtarget from now on, it may have been deepcopied
    if subtarget is None:
        if subsource is not None:
            m = ("cannot assign to key {key!r} "
                 "because target specifies it must not exist")
            m = m.format(key=key)
            e = MergeFault(loc=loc, what='key-exists', data=key, message=m)
            collect_error(errs, e)
        return

    subsource = doc_spec_normalize_val(subsource)
    if subsource:
        if not subtarget:
            subtarget = {}

        subloc = loc + (key,)

        # recurse into subdocuments
        subtarget = doc_spec_merge(
            subtarget, subsource,
            predicates=predicates,
            extend=extend, merge=merge,
            autoregister=autoregister,
            loc=subloc, errs=errs,
            top_target=top_target)

        target_spec[key] = subtarget

    elif subsource is None:
        # None as a source asks to disable the key
        if not subtarget or not subtarget.get('=k'):
            # disable an empty subdocument
            # even if it is a prefix wildcard
            target_spec[key] = None

        elif key[-1:] == '*':
            # disable a non-empty prefix wildcard
            prefix = key[:-1]

            try:
                # remove from prefix index so that
                # it does not match new extensions
                target_spec['=x'].remove(prefix)
            except ValueError:
                # already removed
                pass

            try:
                # remove from merge key order so that
                # it does not get merged in compilation
                target_spec['=k'].remove(key)
            except ValueError:
                # already removed
                pass

        else:
            m = "not allowed to disable non-empty, non-prefix key {key!r}"
            m = m.format(key=key)
            e = MergeFault(loc=loc, what='cannot-disable',
                           data=key, message=m)
            collect_error(errs, e)


def doc_spec_merge_key(target_spec, source, key,
                       extend, merge, predicates,
                       loc, errs, top_target, register_keys):

    subsource = source[key]

    target_spec, err = doc_spec_ensure_target_key(
        target_spec, key,
        extend, merge, predicates,
        loc, errs, top_target, register_keys)

    if err:
        return target_spec

    doc_spec_merge_subsource(target_spec, source, key,
                             extend, merge, predicates,
                             loc, errs, top_target, register_keys)

    return target_spec


def doc_spec_merge_value(target_spec, source, merge, errs, loc):

    source_data = source.get('=', Null)
    target_data = target_spec.get('=', Null)

    if isinstance(source_data, MutableMapping) and not source_data:
        # empty source data does not attempt to update
        source_data = Null

    if source_data is not Null:
        if target_data is Null:
            # it is always allowed to set a value if it does not exist
            target_spec['='] = source_data

        elif target_data != source_data:
            # if values differ they must be merged
            if not merge:
                m = ("value mismatch while no merge function given: "
                     "target {target_data!r} vs source {source_data!r}")
                m = m.format(target_data=target_data,
                             source_data=source_data)
                e = MergeFault(loc=loc,
                               what='value-mismatch',
                               data=(source_data, target_data),
                               message=m)
                collect_error(errs, e)
            else:
                target_spec['='] = merge(target_data, source_data)

        else:
            # equal data match and nothing is written to the target
            pass


def construct_after(context, *predicates):
    constructed = context['constructed']
    if len(constructed.intersection(predicates)) != len(predicates):
        raise DeferConstructor()


def construct_last(context):
    constructed = context['constructed']
    local_predicates = context['local_predicates']
    if len(constructed) < len(local_predicates) - 1:
        raise DeferConstructor()


def instance_get_val_or_skip(instance):
    if '=' not in instance:
        raise SkipConstructor()
    return instance['=']
