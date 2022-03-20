class Graph:

    def __init__(self, execution):
        pe = execution.process_executions.all()
        p_executions = {p.id: p for p in pe.prefetch_related(
            "downstream_data", "upstream_data"
        )}
        data = {}
        for pe in p_executions.values():
            pe.down, pe.up = set(), set()
            for d in pe.downstream_data.all():
                data[d.id] = d
                pe.down.add(d)
            for d in pe.upstream_data.all():
                if d.id in data:
                    d = data[d.id]
                else:
                    data[d.id] = d
                pe.up.add(d)
        for d in data.values():
            d.down = set()
            d.up = set()
            for pe in p_executions.values():
                if d in pe.up: d.down.add(pe)
                if d in pe.down: d.up.add(pe)
        self.process_executions = p_executions
        self.data = data
    

    def __repr__(self):
        node_count = len(self.process_executions) + len(self.data)
        return f"<Graph ({node_count} node{'' if node_count == 1 else 's'})>"