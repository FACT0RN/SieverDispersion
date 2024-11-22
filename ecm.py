import os
import shutil
import subprocess
import traceback
import time
from threading import Thread

from config import SIEVER_MODE, YAFU_PATH, YAFU_THREADS, DEFAULT_WORKDIR, DEFAULT_YAFU_WORKDIR, DEFAULT_CUDAECM_WORKDIR
from config import ECM_PATH, CUDA_ECM_PARAMS, CUDAECM_PATH, HAS_AVX512, YAFU_INI_PATH
from candidate import Candidate
from api import submitSolutionToSisMargaret
from ecmTask import ECMTask

if SIEVER_MODE == 1:
    import nvidia_smi
    nvidia_smi.nvmlInit()


def popenPiped(args, cwd=DEFAULT_WORKDIR):
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)


def resetWorkdir(workdir, yafu=True):
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)

    if yafu:
        # Copy yafu.ini to workdir
        shutil.copy(YAFU_INI_PATH, workdir)


def stopYAFU():
    print("stopYAFU: Stopping YAFU and ecm")
    os.system("pkill -f " + YAFU_PATH)
    os.system("pkill -f " + ECM_PATH)


def stopCUDAECM():
    print("stopCUDAECM: Stopping CUDA ECM")
    os.system("pkill -f " + CUDAECM_PATH)


def factorCandidateViaYAFU(candidate: Candidate, workdir=DEFAULT_YAFU_WORKDIR, threads=YAFU_THREADS, one=True):
    resetWorkdir(workdir)
    yafuArgs = [YAFU_PATH, "-threads", str(threads)]
    if one:
        yafuArgs.append("-one")
    yafuArgs.append(f"factor({candidate.N})")

    proc = popenPiped(yafuArgs, cwd=workdir)
    startYAFUFactors = False
    factors = []
    for line in proc.stdout:
        if not candidate.active:
            stopYAFU()
            return []

        line = line.decode("utf8")
        print(line, end="")
        if "***factors found***" in line:
            startYAFUFactors = True

        try:
            if startYAFUFactors and line[0] in ["C", "P"] and " = " in line:
                factor = int(line.split()[-1])
                if factor > 1 and candidate.N % factor == 0:
                    factors.append(factor)
        except Exception:
            traceback.print_exc()

    factors.sort()
    return factors


def performECMViaYAFU(task: ECMTask, workdir=DEFAULT_YAFU_WORKDIR, threads=YAFU_THREADS, one=True):
    # Only one candidate per task is supported right now
    assert len(task.Ns) == 1
    N = task.Ns[0]

    resetWorkdir(workdir)
    yafuArgs = [YAFU_PATH, "-threads", str(threads),
                "-B1ecm", str(task.B1), "-B2ecm", str(task.B2),
                "-ecm_path", ECM_PATH, "-ext_ecm", "1000000000" if HAS_AVX512 else "0"]
    if one:
        yafuArgs.append("-one")
    yafuArgs.append(f"ecm({N}, {task.curvesPerCandidate})")

    task.startedAt = time.time()
    task.ongoing = True
    proc = popenPiped(yafuArgs, cwd=workdir)
    startYAFUFactors = False
    factors = []
    for line in proc.stdout:
        if not task.active:
            stopYAFU()
            task.taskRuntime = time.time() - task.startedAt
            task.ongoing = False
            return []

        line = line.decode("utf8")
        print(line, end="")
        if "***factors found***" in line:
            startYAFUFactors = True

        if line.startswith("ecm: ") and "curves on" in line:
            task.curvesRan = max(task.curvesRan, int(line.split("/")[0].split()[-1]))

        try:
            if startYAFUFactors and line[0] in ["C", "P"] and " = " in line:
                factor = int(line.split()[-1])
                if factor > 1 and N % factor == 0:
                    factors.append(factor)
        except Exception:
            traceback.print_exc()

    factors.sort()
    task.taskRuntime = time.time() - task.startedAt
    task.ongoing = False
    return [factors]


# Based on https://github.com/FACT0RN/GPUDispersion/blob/9cb46b4bb0104575fea695a369b4d256206470c4/blockchain.py#L32
def createConfigFile(b1, curvesPerCandidate, gpuID, filename, workdir=DEFAULT_CUDAECM_WORKDIR):
    config = f"""[general]

; server or file
mode = file

; Logfile location
logfile = /dev/null

; Output file of abandoned, i.e. unsolved tasks.
; Format is the same as the output format, without listing factors
;
; Example line:
; 44800523911798220433379600867; # effort 112
output_abandoned = /dev/null

; Log level
;
;   1: "VERBOSE",
;   2: "DEBUG",
;   3: "INFO",
;   4: "WARNING",
;   5: "ERROR",
;   6: "FATAL",
;   7: "NONE"
; Default is set at compile time.
loglevel = 3

; Use a random seed for the random number generator used to generate points and
; curves. If set to 'false', each run of the program will behave the same
; provided the same input data.
; Default: true
random = true

[server]
port = 11111

[file]
; Input file.
; The input file should contain a single number to be factored per line. Lines
; starting with anything but a digit are skipped.
;
; Example line:
; 44800523911798220433379600867
input = {workdir}/input{gpuID}.txt


; Output file.
; Each fully factored input number is appended to the output on its own line in
; the format
; (input number);(factor),(factor),(factor), # effort: (number of curves)
;
; Example line:
; 44800523911798220433379600867;224536506062699,199524454608233, # effort: 12
output = {workdir}/output{gpuID}.txt


[cuda]

; Number of concurrent cuda streams to issue to GPU
; Default: 2
streams = 1

; Number of threads per block for cuda kernel launches.
; Set to auto to determine setting for maximum parallel resident blocks per SM at runtime.
; Note: The settings determined by 'auto' are not always automatically the optimal setting for maximum throughput.
; Default: auto
threads_per_block = auto

; Constant memory is used for (smaller) scalars during point multiplication.
; When the scalar is too large to fit into constant memory or this option is set
; to 'false', global device memory is used.
; Default: true
use_const_memory = true

[ecm]
; Redo ECM until numbers are fully factored.
; If set to false, only the first factor is returned.
; Default: false
find_all_factors = false

; Set the computation of the scalar s for point multiplication. With
; 'powersmooth' set to 'true', then s = lcm(2, ..., b1). If set to false,
; s = primorial(2, ..., b1), i.e. the product of all primes less than or equal
; to b1.
; Default: true
powersmooth = true

b1 = {b1}
b2 = 100000


; Maximum effort per input number.
; With each curve, the already spent effort is incremented. Thus, with effort
; set to 100, ecm stage1 (and stage2) will be executed on 100 curves per input
; number.
; Default: 10
effort = {curvesPerCandidate}

; Set the curve generator function.
; Use 2 under normal circumstances.
;   0: "Naive"
;   1: "GKL2016_j1"
;   2: "GKL2016_j4"
; Default: 2
curve_gen = 2

; Use only points for finding factors that are off curve.
; After point multiplication, use all resulting points to find factors. If set
; to 'false' coordinates of points will be checked that do not fulfill the curve
; equation.
; Settings for stage1 and stage2 respectively.
; Default: true
stage1.check_all = false
stage2.check_all = true

; Enable/Disable stage 2.
; If set to 'false', only stage 1 of ECM is performed.
; Default: true
stage2.enabled = false

; Set the window size for stage 2
; Default: 2310
;stage2.window_size = 2310
"""

    with open(filename, "w") as f:
        f.write(config)
        f.close()


def factorCandidatesViaCUDAECM(manager, candidates: list[Candidate], baseWorkdir=DEFAULT_CUDAECM_WORKDIR):
    if len(candidates) == 0:
        return
    print(f"factorCandidatesViaCUDAECM: Working on {len(candidates)} candidates")

    height = manager.height
    deviceCount = nvidia_smi.nvmlDeviceGetCount()

    resetWorkdir(baseWorkdir)
    levels = len(CUDA_ECM_PARAMS["b1"])
    for level in range(levels):
        for i in range(deviceCount):
            configName = f"gpu_config_{level}_{i}.txt"
            createConfigFile(CUDA_ECM_PARAMS["b1"][level], CUDA_ECM_PARAMS["curves"][level],
                             i, DEFAULT_CUDAECM_WORKDIR + configName)

    for level in range(levels):
        totalCands = len(candidates)
        if totalCands == 0:
            print(f"factorCandidatesViaCUDAECM: Out of candidates to run on GPU {level}. Stopping")
            return

        startCandId = 0
        procs = []
        for i in range(deviceCount):
            candsToFetch = totalCands // deviceCount + (1 if i < totalCands % deviceCount else 0)
            configName = f"gpu_config_{level}_{i}.txt"

            with open(baseWorkdir + f"input{i}.txt", "w") as f:
                for j in range(startCandId, startCandId + candsToFetch):
                    f.write(f"{j} {candidates[j].N}\n")
                f.close()

            startCandId += candsToFetch
            procs.append(popenPiped(["env", f"CUDA_VISIBLE_DEVICES={i}", "unbuffer", CUDAECM_PATH, "-c", baseWorkdir + configName]))
            print(f"factorCandidatesViaCUDAECM: GPU {i} started")

            if manager.height > height:
                for proc in procs:
                    proc.kill()
                return

        for i, proc in enumerate(procs):
            print(f"factorCandidatesViaCUDAECM: Waiting for GPU {i} to finish")
            for line in proc.stdout:
                line = line.decode("utf8")
                print(line, end="")

            procs[i].wait()
            print(f"factorCandidatesViaCUDAECM: GPU {i} done")

        if manager.height > height:
            return

        for i in range(deviceCount):
            for line in open(baseWorkdir + f"output{i}.txt").read().split("\n"):
                try:
                    line = line.strip()
                    if line == "" or line == "DONE":
                        continue

                    index, factor = map(int, line.split())
                    if factor == 1 or not candidates[index].active:
                        continue

                    N = candidates[index].N
                    if N % factor != 0:
                        continue

                    candidates[index].active = False
                    factor2 = N // factor
                    print(f"factorCandidatesViaCUDAECM: Submitting {N} = {factor} * {factor2}")
                    Thread(target=submitSolutionToSisMargaret, args=(manager.mqttClient, candidates[index].id, candidates[index].N,
                                                                     factor, factor2), daemon=True).start()
                except Exception:
                    traceback.print_exc()
                    continue

            try:
                os.remove(baseWorkdir + f"output{i}.txt")
            except Exception:
                pass

            if manager.height > height:
                return

        origCands = len(candidates)
        candidates = [c for c in candidates if c.active]
        print(f"factorCandidatesViaCUDAECM: Level {level} done. Reduced {origCands} -> {len(candidates)} candidates")


def performECMViaCUDAECM(task: ECMTask, baseWorkdir=DEFAULT_CUDAECM_WORKDIR):
    totalCands = len(task.Ns)

    if totalCands == 0:
        return
    assert task.B2 == 0
    print(f"performECMViaCUDAECM: Working on {totalCands} candidates")

    task.startedAt = time.time()
    task.ongoing = True
    deviceCount = nvidia_smi.nvmlDeviceGetCount()

    resetWorkdir(baseWorkdir)
    startCandId = 0
    procs = []
    for i in range(deviceCount):
        configName = f"performECMViaCUDAECM_{i}.txt"
        createConfigFile(task.B1, task.curvesPerCandidate, i, baseWorkdir + configName)

        candsToFetch = totalCands // deviceCount + (1 if i < totalCands % deviceCount else 0)
        with open(baseWorkdir + f"input{i}.txt", "w") as f:
            for j in range(startCandId, startCandId + candsToFetch):
                f.write(f"{j} {task.Ns[j]}\n")
            f.close()

        startCandId += candsToFetch
        procs.append(popenPiped(["env", f"CUDA_VISIBLE_DEVICES={i}", "unbuffer", CUDAECM_PATH, "-c", baseWorkdir + configName]))
        print(f"performECMViaCUDAECM: GPU {i} started")

        if not task.active:
            for proc in procs:
                proc.kill()
            return

    for i, proc in enumerate(procs):
        print(f"performECMViaCUDAECM: Waiting for GPU {i} to finish")
        for line in proc.stdout:
            line = line.decode("utf8")
            print(line, end="")

        procs[i].wait()
        print(f"performECMViaCUDAECM: GPU {i} done")

    if not task.active:
        return

    factorsList = [[] for _ in range(totalCands)]
    for i in range(deviceCount):
        for line in open(baseWorkdir + f"output{i}.txt").read().split("\n"):
            try:
                line = line.strip()
                if line == "" or line == "DONE":
                    continue

                index, factor = map(int, line.split())
                if factor == 1:
                    continue

                N = task.Ns[index]
                if N % factor != 0:
                    continue

                factor2 = N // factor
                print(f"performECMViaCUDAECM: Found {N} = {factor} * {factor2}")
                factorsList[index] = [factor, factor2]
            except Exception:
                traceback.print_exc()
                continue

        try:
            os.remove(baseWorkdir + f"output{i}.txt")
        except Exception:
            pass

        if not task.active:
            return

    print(f"performECMViaCUDAECM: ECM finished. Reduced {totalCands} -> {sum(len(factors) < 2 for factors in factorsList)} candidates")

    task.taskRuntime = time.time() - task.startedAt
    task.ongoing = False
    return factorsList
