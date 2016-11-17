from collections import namedtuple
from apimas.modeling.core.documents import (
    doc_set, doc_match_levels, doc_iter, ANY, Prefix, Regex)


class Tabmatch(object):
    def __init__(self, column_names, rules=()):
        self.column_names = tuple(column_names)
        self.Row = namedtuple('TabmatchRow', self.column_names)
        self.rules_set = set(rules)
        self.rules_doc = {}
        for rule in rules:
            doc_set(self.rules_doc, rule[:-1], rule[-1])

        self.name_levels = {
            name: x
            for x, name in enumerate(self.column_names)
        }

    def _check_row_type(self, row):
        if not isinstance(row, self.Row):
            m = "rows must be of type Tabmatch.Row, not {row!r}"
            m = m.format(row=row)
            raise TypeError(m)

    def update(self, rows):
        for row in rows:
            self._check_row_type(row)
            self.rules_set.add(row)
            doc_set(self.rules_doc, row[:-1], row[-1])

    def match(self, row, expand):
        self._check_row_type(row)
        results = set()
        for tab_row in self.rules_set:
            item = {}
            for name in self.column_names:
                tab_val = getattr(tab_row, name)
                row_val = getattr(row, name)

                if (row_val.endswith('*') and tab_val.startswith(row_val[:-1])):
                    item[name] = tab_val if name in expand else row_val
                elif (tab_val.endswith('*') and row_val.startswith(tab_val[:-1])):
                    item[name] = tab_val
                elif tab_val == row_val:
                    item[name] = tab_val
                else:
                    item = None
                    break

            if item is not None:
                val = self.Row(**item)
                results.add(val)

        return results

    def multimatch(self, pattern_sets, expand):
        expand_levels = {self.name_levels[name] for name in expand}
        depth = len(self.column_names)
        matches = doc_match_levels(self.rules_doc, pattern_sets,
                                   expand_levels)
        return (self.Row(*path) for path in matches if len(path) == depth)


def test():
    tb = Tabmatch(['one', 'two', 'three'])
    tb.update([tb.Row(one='hella', two='two', three='hooves')])
    tb.update([tb.Row(one='hellish', two='taint', three='saw')])
    tb.update([tb.Row(one='hello', two='there', three='friend')])
    tb.update([tb.Row(one=Prefix('foo'), two=ANY, three='blam')])
    pattern_sets = [
        ['alpha', Prefix('hel'), 'one'],
        [Regex('th.r[ae]'), 'bom', Prefix('t')],
    ]
    print "RULES"
    print tb.rules_doc
    print "PATTERNS"
    print pattern_sets
    expand = []
    print "EXPAND", expand
    print list(tb.multimatch(pattern_sets, expand=[]))
    expand = ['one', 'two', 'three']
    print "EXPAND", expand
    expand_levels = {tb.name_levels[name] for name in expand}
    print list(tb.multimatch(pattern_sets, expand=expand))


if __name__ == '__main__':
    test()

