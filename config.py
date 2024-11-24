import psutil
import os
import subprocess
import sys

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(sys.argv[0]))

YAFU_THREADS = os.environ.get("YAFU_THREADS", "").strip()
if YAFU_THREADS == "":
    YAFU_THREADS = psutil.cpu_count()
else:
    YAFU_THREADS = int(YAFU_THREADS)

HAS_AVX512 = os.environ.get("HAS_AVX512", "").strip()
if HAS_AVX512 == "":
    try:
        HAS_AVX512 = "avx512ifma" in open("/proc/cpuinfo").read()
        if HAS_AVX512:
            print("Enabling AVX512")
        else:
            print("Disabling AVX512")
    except Exception:
        print("Warning: Could not determine AVX512IFMA support. Disabling AVX512")
        print('Set HAS_AVX512 environment variable to "True" to try using AVX512IFMA anyways')
        HAS_AVX512 = False
else:
    HAS_AVX512 = HAS_AVX512 == "True"

IS_DOCKER = os.environ.get("IS_DOCKER", "False") == "True"
GIT_VERSION = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()
MACHINE_ID = open(f"{SCRIPT_FOLDER}/machineID.txt").read().strip()

DEFAULT_WORKDIR = "/dev/shm/sieverdispersion-workdir/"
DEFAULT_YAFU_WORKDIR = DEFAULT_WORKDIR + "yafu/"
DEFAULT_CUDAECM_WORKDIR = DEFAULT_WORKDIR + "cuda-ecm/"

if IS_DOCKER:
    BIN_DIR = "/tmp/bin/"
else:
    BIN_DIR = f"{SCRIPT_FOLDER}/bin/"

if HAS_AVX512:
    YAFU_PATH = f"{BIN_DIR}yafu-avx512"
else:
    YAFU_PATH = f"{BIN_DIR}yafu"
YAFU_INI_PATH = f"{BIN_DIR}yafu.ini"
ECM_PATH = f"{BIN_DIR}ecm"
CUDAECM_PATH = f"{BIN_DIR}cuda-ecm"

SIEVER_MODE = os.environ.get("SIEVER_MODE", "").strip()
if SIEVER_MODE == "":
    print("Error: Please set SIEVER_MODE=0 (Use CPU) or SIEVER_MODE=1 (Use GPU) via environment variable")
    print("If you want to utilize both CPU and GPU, run two miners in different terminal tabs, one with SIEVER_MODE=0 and the other with SIEVER_MODE=1")
    exit(1)
else:
    SIEVER_MODE = int(SIEVER_MODE)

API_DEF_RETRIES = 10000
API_MAX_TIMEOUT = 300
API_CANDIDATE_GEN_WAIT_TIME = (5, 7)
API_CPU_ACCEPT_THRESHOLD = 150 * 10000

CUDA_ECM_PARAMS = { "b1":     [11000, 50000, 250000, 1000000, 3000000, 11000000, 43000000],
                    "curves": [   86,   214,    430,     910,    2351,     4482,     7557]}
