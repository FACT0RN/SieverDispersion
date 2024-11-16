class ECMTask:
    def __str__(self):
        return f"ECMTask(taskId={self.taskId}, candidateId={self.candidateId}, B1={self.B1}, B2Mult={self.B2Mult}, curves={self.curves})"


    def __init__(self, obj):
        for key in ["taskId", "N", "candidateId", "B1", "B2Mult", "curves"]:
            setattr(self, key, obj[key])

        self.B2 = self.B2Mult * self.B1
        self.active = True

        self.curvesRan = 0

        self.startedAt = None
        self.ongoing = False
        self.taskRuntime = 0

