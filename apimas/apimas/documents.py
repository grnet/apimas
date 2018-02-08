from collections import namedtuple
import re
from docular import doc_merge, doc_iter, doc_set

from errors import ValidationError, NotFound, InvalidInput, ConflictError


bytes = str


cons_fields = [
    'instance',
    'loc',
    'spec',
    'cons_round',
    'parent_name',
    'parent_spec',
    'top_spec',
    'sep',
    'constructor_index',
    'cons_siblings',
    'constructed',
    'context',
]

ConstructorContext = namedtuple('ConstructorContext', cons_fields)


def standard_merge(x, y):
    if x is None:
        return y
    if y is None:
        return x
    if x == y:
        return x
    else:
        raise ConflictError(
            'Cannot merge documents: distinct values (%s %s)' % (
                repr(x), repr(y)))


def doc_match_levels(rules_doc, pattern_sets, expand_pattern_levels,
                     level=0, path=(), crop_levels=None):

    reported_paths = set()
    expand_pattern = level in expand_pattern_levels
    if crop_levels is None:
        crop_levels = len(pattern_sets)

    if level >= len(pattern_sets):
        yield path, None
        return

    for pattern in pattern_sets[level]:
        if isinstance(pattern, SegmentPattern):
            rules_doc_iter = ((rule, subdoc)
                              for rule, subdoc in rules_doc.iteritems()
                              if rule == pattern or pattern == rule)

        elif pattern in rules_doc:
            rules_doc_iter = [(pattern, rules_doc[pattern])]

        else:
            rules_doc_iter = ((rule, subdoc)
                              for rule, subdoc in rules_doc.iteritems()
                              if rule == pattern)

        for rule, subdoc in rules_doc_iter:
            reportable_segment = rule if expand_pattern else pattern
            subpath = path + (reportable_segment,)
            if type(subdoc) is not dict:
                reportables = [(subpath, subdoc)]
            else:
                reportables = doc_match_levels(
                    rules_doc=subdoc, pattern_sets=pattern_sets,
                    expand_pattern_levels=expand_pattern_levels,
                    level=level + 1, path=subpath)

            for reportable_path, reportable_val in reportables:
                reported_path = reportable_path[:crop_levels]
                if reported_path not in reported_paths:
                    reported_paths.add(reported_path)
                    yield reportable_path, reportable_val


class Aggregator(object):
    def __call__(patterns, rules):
        raise NotImplementedError('__call__ must be implemented')


class AllOfAggregator(Aggregator):
    def __call__(self, patterns, rules, stop=True, expanded=False):
        matches = {}
        if expanded:
            stop = False
        for pattern in patterns:
            matching_rules = [rule for rule in rules if pattern == rule]
            if not len(matching_rules) and stop:
                return []
            if matching_rules:
                matches[pattern] = matching_rules
        if expanded and stop and len(rules) > len(
                set(sum((x for x in matches.values()), []))):
            return {}
        elif stop and len(matches) < len(patterns):
            return {}
        return matches


class AnyOfAggregator(AllOfAggregator):
    def __call__(self, patterns, rules, expanded=False):
        return super(self.__class__, self).__call__(
            patterns, rules, stop=False, expanded=expanded)


def multimerge(doc, merged_keys, merged_node=None):
    merged_doc = {}
    merged_node = merged_node or 'merged_' + '_'.join(merged_keys)
    for k in merged_keys:
        if k not in doc:
            raise NotFound('Key %s not found in document' % (repr(k)))
        doc_k = doc[k]
        merged_doc = doc_merge(doc_k, merged_doc, standard_merge)
    merged_doc = {merged_node: merged_doc}
    for k, v in doc.iteritems():
        if k not in merged_keys:
            merged_doc.update({k: v})
    return merged_doc, merged_node


def _doc_match_update_doc(doc, matched_doc, updated_keys):
    for k in updated_keys:
        if k in doc:
            doc = doc_merge(
                doc, {k: matched_doc}, standard_merge)
        else:
            doc[k] = matched_doc
    return doc


def doc_match(patterns, rules, aggregators, level=0, expand_levels=None,
              automerge=False):
    if type(rules) is dict:
        if not rules:
            return {}, True
    elif rules == patterns:
        return patterns, True
    else:
        return {}, False

    matches_doc = {}
    pattern_keys = patterns.keys()
    rule_keys = rules.keys()
    expand_levels = expand_levels or []
    expanded = bool(level in expand_levels)
    matches = aggregators[level](pattern_keys, rule_keys, expanded=expanded)
    if not matches:
        return {}, False
    missed = []
    for match, matching_rules in matches.iteritems():
        inspected_rules = matching_rules
        if automerge and len(matching_rules) > 1:
            rules, node = multimerge(rules, matching_rules)
            inspected_rules = [node]

        for rule in inspected_rules:
            subrules = rules.get(rule, {})
            subpatterns = patterns.get(match, {})
            updated_keys = matching_rules if expanded else [match]
            matched_doc, ismatched = doc_match(
                subpatterns, subrules, aggregators, level=level+1,
                expand_levels=expand_levels)
            matches_doc = _doc_match_update_doc(
                matches_doc, matched_doc, updated_keys)
            if not ismatched:
                missed.append(match)
    if any(type(x) is AllOfAggregator for x in aggregators[:level])\
            and len(missed) == len(matches):
        return {x: {} for x in missed}, False
    if missed and type(aggregators[level]) is AllOfAggregator:
        return {x: {} for x in missed}, False
    return matches_doc, True



def doc_to_level_patterns(doc):
    pattern_sets = []
    for p, v in doc_iter(doc):
        max_level = len(p)
        nr_sets = len(pattern_sets)
        level_diff = max_level - nr_sets + 1
        if max_level >= nr_sets:
            pattern_sets += [set() for _ in xrange(level_diff)]
        for level, segment in enumerate(p):
            pattern_sets[level].add(p[level])
    return pattern_sets


class SegmentPattern(object):
    def __init__(self, *args):
        self.args = args

    def match(self, segment):
        raise NotImplementedError

    def __eq__(self, other):
        return self.match(other)

    @classmethod
    def construct(cls, instance, spec, loc, context):
        key = loc[-2]
        return cls(key)


class AnyPattern(SegmentPattern):
    def match(self, segment):
        return True

    def __repr__(self):
        return "<ANY>"

    __str__ = __repr__


ANY = AnyPattern()


class Prefix(SegmentPattern):
    def __init__(self, prefix):
        self.prefix = prefix

    def __repr__(self):
        return "Prefix({prefix!r})".format(prefix=self.prefix)

    __str__ = __repr__

    def match(self, segment):
        startswith = getattr(segment, 'startswith', None)
        if startswith is not None:
            return startswith(self.prefix)
        elif isinstance(segment, AnyPattern):
            return True
        elif isinstance(segment, Regex):
            m = "Comparison between Prefix and Regex not supported"
            raise NotImplementedError(m)
        else:
            return False

    def startswith(self, prefix):
        return self.prefix.startswith(prefix)


class Regex(SegmentPattern):
    def __init__(self, pattern):
        self.pattern = pattern
        self.matcher = re.compile(pattern)

    def __repr__(self):
        return "Regex({pattern!r})".format(pattern=self.pattern)

    __str__ = __repr__

    def match(self, segment):
        segment_type = type(segment)
        if isinstance(segment_type, basestring):
            return self.matcher.match(segment) is not None
        elif isinstance(segment, AnyPattern):
            return True
        else:
            m = "Comparison between Regex and {segment!r} not supported"
            m = m.format(segment=segment)
            raise NotImplementedError(m)
            return False


class Literal(SegmentPattern):
    def __new__(cls, segment):
        return segment


class And(SegmentPattern):
    def __init__(self, pattern):
        self.patterns = parse_pattern(x for x in pattern.split('&'))

    def match(self, segment):
        return all(x == segment or segment == x for x in self.patterns)


class Or(SegmentPattern):
    def __init__(self, pattern):
        self.patterns = parse_pattern(x for x in pattern.split('|'))

    def match(self, segment):
        return any(x == segment or segment == x for x in self.patterns)


class Inverse(SegmentPattern):
    def __init__(self, pattern):
        self.pattern = parse_pattern(pattern)

    def match(self, segment):
        return not self.pattern == segment


_pattern_prefixes = {
    '*': AnyPattern,
    '?': Regex,
    '!': Inverse,
    '_': Prefix,
    '&': And,
    '|': Or,
    '=': Literal,
}


def parse_pattern(string):
    prefix = string[:1]
    if prefix in _pattern_prefixes:
        pattern = string[1:]
    else:
        # Fail back to literal for rule readability.
        pattern = string
        prefix = '='

    return _pattern_prefixes[prefix](pattern)


def construct_patterns(instance, spec, loc, context):
    spec_type = type(spec)
    if spec_type is dict:
        for pattern, val in spec.iteritems():
            pattern_instance = parse_pattern(pattern)
            instance[pattern_instance] = val
    elif spec_type in (set, tuple, list):
        for pattern in spec:
            pattern_instance = parse_pattern(pattern)
            instance[pattern_instance] = {}
    else:
        m = "Unsuported spec node type: {spec!r}"
        m = m.format(spec=spec)
        raise ValidationError(m)

    return instance


def random_doc(nr_nodes=32, max_depth=7):
    words = (
        'alpha',
        'beta',
        'gamma',
        'delta',
        'epsilon',
        'zeta',
        'eta',
        'theta',
        'iota',
        'kappa',
        'lambda',
        'mu',
        'nu',
        'omikron',
        'pi',
        'rho',
        'sigma',
        'tau',
        'ypsilon',
        'phi',
        'psi',
        'omega',
        'zero',
        'one',
        'two',
        'three',
        'four',
        'five',
        'six',
        'seven',
        'eight',
        'nine',
    )

    import random

    doc = {}

    for i in xrange(nr_nodes):
        depth = random.randint(1, max_depth)
        path = tuple(random.choice(words) for _ in xrange(depth))
        doc_set(doc, path, random.choice(words))

    return doc
