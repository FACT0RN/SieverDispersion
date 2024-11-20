class ECMTask:
    def __str__(self):
        return f"""ECMTask(type={self.type}, B1={self.B1}, B2Mult={self.B2Mult}, curvesPerCandidate={self.curvesPerCandidate},
            candidateIds={self.candidateIds})"""


    def __init__(self, obj, type):
        assert type == "cpu" or type == "gpu"
        self.type = type

        self.B1 = int(obj["b1"])
        self.B2Mult = int(obj["b2mult"])
        self.curvesPerCandidate = int(obj["curves"])

        if self.type == "cpu":
            self.candidateIds = [int(obj["candidateId"])]
            self.Ns = [int(obj["n"])]
        elif self.type == "gpu":
            self.candidateIds = list(map(int, obj["candidateIds"]))
            self.Ns = list(map(int, obj["Ns"]))

        assert len(self.candidateIds) == len(self.Ns)
        if self.type == "cpu":
            assert len(self.candidateIds) == 1

        self.B2 = self.B2Mult * self.B1
        self.active = True

        self.curvesRan = 0

        self.startedAt = None
        self.ongoing = False
        self.taskRuntime = 0

