from ecmTask import ECMTask
from ecm import stopYAFU


class TaskChunk:
    def __str__(self):
        return f"""TaskChunk(taskChunkId={self.taskChunkId}, tasks=[
    {', \n'.join(map(str, self.tasks))}
])"""


    def __init__(self, obj):
        self.taskChunkId = obj["taskChunkId"]
        self.height = obj["height"]
        self.tasks = [ECMTask(t) for t in obj["tasks"]]

        self.startedAt = None
        self.taskChunkRuntime = None


    def abort(self):
        for t in self.tasks:
            t.active = False
        stopYAFU()
