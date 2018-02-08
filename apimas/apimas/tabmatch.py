from collections import namedtuple
from docular import doc_set
from apimas.documents import doc_match_levels


class Tabmatch(object):
    def __init__(self, column_names, rules=()):
        self.column_names = tuple(column_names)
        self.Row = namedtuple('TabmatchRow', self.column_names)
        self.rules_set = set(rules)
        self.rules_doc = {}
        self.name_levels = {
            name: x
            for x, name in enumerate(self.column_names)
        }
        self._construct_rules_doc(rules)

    def _construct_rules_doc(self, rules):
        for rule in rules:
            doc_set(self.rules_doc, rule, {})

    def _check_row_type(self, row):
        if not isinstance(row, self.Row):
            m = "rows must be of type Tabmatch.Row, not {row!r}"
            m = m.format(row=row)
            raise TypeError(m)

    def update(self, rows):
        for row in rows:
            self._check_row_type(row)
            self.rules_set.add(row)
            doc_set(self.rules_doc, row, {})

    def match(self, row, expand):
        self._check_row_type(row)
        results = set()
        for tab_row in self.rules_set:
            item = {}
            for name in self.column_names:
                tab_val = getattr(tab_row, name)
                row_val = getattr(row, name)

                if (row_val.endswith('*') and tab_val.startswith(
                        row_val[:-1])):
                    item[name] = tab_val if name in expand else row_val
                elif (tab_val.endswith('*') and row_val.startswith(
                        tab_val[:-1])):
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
                                   expand_levels, crop_levels=depth)
        return (self.Row(*path) for path, _ in matches if len(path) == depth)
