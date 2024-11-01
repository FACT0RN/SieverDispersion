import os
import shutil
import subprocess
import traceback
import time

from config import YAFU_PATH, YAFU_THREADS, DEFAULT_WORKDIR, ECM_PATH
from candidate import Candidate


def popenPiped(args, cwd=DEFAULT_WORKDIR):
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd)


def resetWorkdir(workdir):
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)

    # Copy /tmp/yafu/yafu.ini to workdir
    shutil.copy("/tmp/yafu/yafu.ini", workdir)


def stopYAFU():
    print("stopYAFU: Stopping YAFU and ecm")
    os.system("pkill -f " + YAFU_PATH)
    time.sleep(0.1)
    os.system("pkill -f " + ECM_PATH)


def conductECMViaYAFU(candidate: Candidate, workdir=DEFAULT_WORKDIR, threads=YAFU_THREADS, one=True):
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
