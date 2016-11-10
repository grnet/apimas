from collections import namedtuple


class Tabmatch(object):
    def __init__(self, column_names):
        self.column_names = tuple(column_names)
        self.Row = namedtuple('TabmatchRow', self.column_names)
        self.rows = set()

    def _check_row_type(self, row):
        if not isinstance(row, self.Row):
            m = "rows must be of type Tabmatch.Row, not {row!r}"
            m = m.format(row)
            raise TypeError(m)

    def update(self, rows):
        for row in rows:
            self._check_row_type(row)
            self.rows.add(row)

    def match(self, row, expand):
        self._check_row_type(row)
        results = set()
        for tab_row in self.rows:
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
