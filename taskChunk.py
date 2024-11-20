from ecmTask import ECMTask


class TaskChunk:
    def __str__(self):
        return f"""TaskChunk(type={self.type}, id={self.taskChunkId}, height={self.height}, tasks=[
    {', \n    '.join(map(str, self.tasks))}
])"""


    def __init__(self, obj, type):
        assert type == "cpu" or type == "gpu"
        self.type = type

        self.taskChunkId = int(obj["id"])
        self.height = int(obj["height"])
        self.tasks = [ECMTask(t, type) for t in obj[f"{self.type}Tasks"]]

        self.startedAt = None
        self.taskChunkRuntime = None


    def abort(self):
        for t in self.tasks:
            t.active = False
