conda create -y -n evalscope python=3.10
conda activate evalscope
pip install tiktoken omegaconf
pip install torch==2.6.0
pip install accelerate
pip install bitsandbytes
pip install evalscope
conda deactivate
