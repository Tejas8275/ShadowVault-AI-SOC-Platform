"""Deterministic test-only provider. Never installed by the production application."""
import json


class FixtureProvider:
    def __init__(self):
        self.inputs = []

    def count_input_tokens(self, *, instructions, data):
        return len(instructions) + len(data)  # Conservative fixture-only count.

    async def select_sources(self, *, instructions, data, max_output_bytes, max_output_tokens):
        self.inputs.append((instructions, data))
        rows = json.loads(data)['untrusted_records']
        return json.dumps({'sources':[row['alias'] for row in rows[:20]]})
