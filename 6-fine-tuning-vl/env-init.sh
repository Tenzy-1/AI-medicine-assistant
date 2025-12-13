# Autodl 运行环境初始化脚本

## 查看环境

nvidia-smi
nvcc --version
pip show torch

## 解决 autodl 系统盘爆盘问题

rm -rf ~/.cache
ln -s  /root/autodl-tmp  ~/.cache

## 安装 unsloth

source activate base
conda create --name unsloth
conda activate unsloth

# 以下二选一：
# 1. pip install unsloth
#
# 2. pip install "unsloth[cu124-torch260] @ git+https://github.com/unslothai/unsloth.git"
#    pip install torchvision==0.21

# torchvision 版本对应关系可查下链接
# https://github.com/pytorch/vision

## 微调 qwen-vl

python fine-tuning-qwen25vl-32b.py
conda deactivate

## 安装 vllm

conda create --name vllm
conda activate vllm

git clone https://github.com/vllm-project/vllm.git
cd vllm
python use_existing_torch.py
pip install -r requirements/build.txt
pip install --no-build-isolation -e .

## 或者

pip install vllm==0.10.0

## 启动 vllm 服务
vllm serve ./qwen25vl-7b-offical-finetuned  --host 0.0.0.0  --port 80  --gpu_memory_utilization=0.90 --max-model-len=32k --tensor-parallel-size 1   --trust-remote-code
#vllm serve ./unsloth_finetune/ --gpu_memory_utilization=0.90 --max-model-len=32k --tensor-parallel-size 1 --host 0.0.0.0  --port 80  --trust-remote-code
#vllm serve ./unsloth_finetune/ --gpu_memory_utilization=0.90 --tensor-parallel-size 2 --host 0.0.0.0  --port 80  --trust-remote-code

## 从 ModelScope 下载模型

pip install modelscope
mkdir -p /root/autodl-tmp/qwen25vl-32b-bnb-4bit
modelscope download --model unsloth/Qwen2.5-VL-32B-Instruct-bnb-4bit --local_dir /root/autodl-tmp/qwen25vl-32b-bnb-4bit/

## Autodl 启动加速 https://autodl.com/docs/network_turbo/

source /etc/network_turbo
unset http_proxy && unset https_proxy
