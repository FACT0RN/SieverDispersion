import psutil
import os

IS_DOCKER = os.environ.get("IS_DOCKER", "False") == "True"

SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
DEFAULT_WORKDIR = "/dev/shm/sieverdispersion-workdir"
YAFU_PATH = "/tmp/yafu/yafu"
ECM_PATH = "/tmp/gmp-ecm/ecm"
YAFU_THREADS = int(os.environ.get("YAFU_THREADS", psutil.cpu_count()))
SIEVER_MODE = int(os.environ.get("SIEVER_MODE", "0"))

API_DEF_RETRIES = 10000
API_MAX_TIMEOUT = 300
API_CANDIDATE_GEN_WAIT_TIME = (5, 7)
