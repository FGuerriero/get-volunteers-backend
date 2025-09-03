# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# SPDX-License-Identifier: MIT
#

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []

    def add_task(self, func, *args, **kwargs):
        # Don't even store tasks to prevent any execution
        pass

    async def run_tasks(self):
        # No-op to prevent any task execution
        pass