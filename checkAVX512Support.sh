#!/bin/bash

if grep -q "avx512ifma" /proc/cpuinfo; then
    echo "Please use CPUMinerStart_AVX512.sh"
else
    echo "Please use CPUMinerStart.sh"
fi
