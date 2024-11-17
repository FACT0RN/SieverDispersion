from ecmTask import ECMTask


class TaskChunk:
    def __str__(self):
        return f"""TaskChunk(taskChunkId={self.taskChunkId}, height={self.height}, tasks=[
    {', \n    '.join(map(str, self.tasks))}
])"""


    def __init__(self, obj):
        self.taskChunkId = int(obj["id"])
        self.height = int(obj["height"])
        self.tasks = [ECMTask(t) for t in obj["tasks"]]

        self.startedAt = None
        self.taskChunkRuntime = None


    def abort(self):
        for t in self.tasks:
            t.active = False
