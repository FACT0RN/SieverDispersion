## Prerequisite
- A Linux machine (WSL2 should work as well, although it's not covered in this guide. Feel free to open a PR and add it to this guide)
- The API key to your Sister Margaret's account (register at https://sismargaret.fact0rn.io/, then get the API key from https://sismargaret.fact0rn.io/profile)
- Install docker ([guide](https://docs.docker.com/engine/install/ubuntu/))
- If you're using GPU: Install NVIDIA driver ([guide](https://ubuntu.com/server/docs/nvidia-drivers-installation)) and CUDA ([guide](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html#network-repo-installation-for-ubuntu))
- If you're using GPU: Install and configure nvidia-container-toolkit ([guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#installing-with-apt), make sure to do the "Configuring Docker" step as well)

## Miner setup and update
### CPU miner setup
```
git clone https://github.com/FACT0RN/SieverDispersion
cd SieverDispersion
nano api_token.txt
# Paste your Sister Margaret's API key into api_token.txt
```
Afterwards, run `./CPUStartMiner_AVX512.sh` if your CPU supports AVX512IFMA, or run `./CPUMinerStart.sh` if it doesn't.  
If you're not 100% sure, run `./checkAVX512Support.sh` and follow its suggestion.

### GPU miner setup
```
git clone https://github.com/FACT0RN/SieverDispersion
cd SieverDispersion
nano api_token.txt
# Paste your Sister Margaret's API key into api_token.txt
./GPUMinerStart.sh
```
If you want to utilize both CPU and GPU, run `./CPUMinerStart.sh` in another terminal tab

### Updating the miner
Run `git pull`, and then run CPUMinerStart.sh (or CPUMinerStart_AVX512.sh, or GPUMinerStart.sh)
