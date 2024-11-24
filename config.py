import psutil
import os
import subprocess

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))

YAFU_THREADS = os.environ.get("YAFU_THREADS", "").strip()
if YAFU_THREADS == "":
    YAFU_THREADS = psutil.cpu_count()
else:
    YAFU_THREADS = int(YAFU_THREADS)

HAS_AVX512 = os.environ.get("HAS_AVX512", "False") == "True"

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
SIEVER_MODE = int(os.environ.get("SIEVER_MODE", "0"))

API_DEF_RETRIES = 10000
API_MAX_TIMEOUT = 300
API_CANDIDATE_GEN_WAIT_TIME = (5, 7)
API_CPU_ACCEPT_THRESHOLD = 150 * 10000

CUDA_ECM_PARAMS = { "b1":     [11000, 50000, 250000, 1000000, 3000000, 11000000, 43000000],
                    "curves": [   86,   214,    430,     910,    2351,     4482,     7557]}
