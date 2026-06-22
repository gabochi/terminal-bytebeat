LAYOUTS = [
    {'bits': 6, 'phase': 8, 'scope': 3, 'name': 'A'},
    {'bits': 8, 'phase': 6, 'scope': 3, 'name': 'B'},
    {'bits': 4, 'phase': 10, 'scope': 3, 'name': 'C'},
    {'bits': 8, 'phase': 4, 'scope': 5, 'name': 'D'},
    {'bits': 6, 'phase': 6, 'scope': 5, 'name': 'E'},
]


class LayoutManager:
    def __init__(self, config, top_margin=1):
        self.bits = config['bits']
        self.phase = config['phase']
        self.scope = config['scope']
        self.name = config['name']

        # fixed structure: top_margin(1) expr(1) cascade(1) sep(1) bits(N) sep(1) phase(M) sep(1) scope(P) labels(1)
        self._y = {}
        y = top_margin
        self._y['expr'] = y; y += 1
        self._y['cascade'] = y; y += 1
        y += 1  # separator
        self._y['bits'] = y; y += self.bits
        y += 1  # separator
        self._y['phase'] = y; y += self.phase
        y += 1  # separator
        self._y['scope'] = y; y += self.scope
        self._y['labels'] = y

    def y(self, section):
        return self._y[section]

    def h(self, section):
        return getattr(self, section)
