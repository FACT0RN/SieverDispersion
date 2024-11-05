import psutil
import os
import subprocess

IS_DOCKER = os.environ.get("IS_DOCKER", "False") == "True"
GIT_VERSION = subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WORKDIR = "/dev/shm/sieverdispersion-workdir/"
DEFAULT_YAFU_WORKDIR = DEFAULT_WORKDIR + "yafu/"
DEFAULT_CUDAECM_WORKDIR = DEFAULT_WORKDIR + "cuda-ecm/"
YAFU_PATH = "/tmp/yafu/yafu"
ECM_PATH = "/tmp/gmp-ecm/ecm"
CUDAECM_PATH = "/tmp/cuda-ecm"
YAFU_THREADS = int(os.environ.get("YAFU_THREADS", psutil.cpu_count()))
SIEVER_MODE = int(os.environ.get("SIEVER_MODE", "0"))

API_DEF_RETRIES = 10000
API_MAX_TIMEOUT = 300
API_CANDIDATE_GEN_WAIT_TIME = (5, 7)

CUDA_ECM_PARAMS = { "b1":     [11000, 50000, 250000, 1000000, 3000000, 11000000, 43000000],
                    "curves": [   86,   214,    430,     910,    2351,     4482,     7557]}
