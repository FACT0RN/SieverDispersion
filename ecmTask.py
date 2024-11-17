class ECMTask:
    def __str__(self):
        return f"ECMTask(taskId={self.taskId}, candidateId={self.candidateId}, B1={self.B1}, B2Mult={self.B2Mult}, curves={self.curves})"


    def __init__(self, obj):
        self.taskId = int(obj["id"])
        self.N = int(obj["n"])
        self.candidateId = int(obj["candidateId"])
        self.B1 = int(obj["b1"])
        self.B2Mult = int(obj["b2mult"])
        self.curves = int(obj["curves"])

        self.B2 = self.B2Mult * self.B1
        self.active = True

        self.curvesRan = 0

        self.startedAt = None
        self.ongoing = False
        self.taskRuntime = 0

