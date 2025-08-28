# Use specific version of nvidia cuda image
FROM nvidia/cuda:12.8.1-cudnn-devel-ubuntu22.04 as runtime

# Remove any third-party apt sources to avoid issues with expiring keys.
RUN rm -f /etc/apt/sources.list.d/*.list

# Set shell and noninteractive environment variables
SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV SHELL=/bin/bash
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="/usr/local/cuda/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:${LD_LIBRARY_PATH}"
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV HF_HUB_DISABLE_PROGRESS_BARS=1
# CUDA 환경 변수 - CPU fallback 없음
ENV FORCE_CUDA=1
ENV CUDA_VISIBLE_DEVICES=0

# Set working directory
WORKDIR /

# Update and upgrade the system packages (Worker Template)
RUN apt-get update --yes && \
    apt-get upgrade --yes && \
    apt install --yes --no-install-recommends git wget curl bash libgl1 software-properties-common openssh-server nginx rsync ffmpeg && \
    apt-get install --yes --no-install-recommends build-essential libssl-dev libffi-dev libxml2-dev libxslt1-dev zlib1g-dev git-lfs && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt install python3.10-dev python3.10-venv -y --no-install-recommends && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "en_US.UTF-8 UTF-8" > /etc/locale.gen

# Download and install pip
RUN ln -s /usr/bin/python3.10 /usr/bin/python && \
    rm /usr/bin/python3 && \
    ln -s /usr/bin/python3.10 /usr/bin/python3 && \
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && \
    python get-pip.py

RUN pip install -U wheel setuptools packaging 
RUN pip install -U "huggingface_hub[hf_transfer]"
RUN pip install runpod websocket-client

RUN pip install torch==2.7.0+cu128 torchvision torchaudio xformers triton --index-url https://download.pytorch.org/whl/cu128

ENV TORCH_CUDA_ARCH_LIST="8.9;9.0"
WORKDIR /
RUN git clone https://github.com/thu-ml/SageAttention.git
WORKDIR /SageAttention
RUN sed -i "/compute_capabilities = set()/a compute_capabilities = {\"$TORCH_CUDA_ARCH_LIST\"}" setup.py
RUN python setup.py install


# Install ComfyUI
WORKDIR /
RUN git clone https://github.com/comfyanonymous/ComfyUI.git && \
    cd ComfyUI && \
    pip install --no-cache-dir -r requirements.txt

RUN cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install --no-cache-dir -r requirements.txt

# Install WAN I2V custom nodes
RUN cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git && \
    cd ComfyUI-VideoHelperSuite && \
    pip install --no-cache-dir -r requirements.txt

RUN cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/Fannovel16/ComfyUI-Frame-Interpolation.git && \
    cd ComfyUI-Frame-Interpolation && \
    pip install --no-cache-dir -r requirements-no-cupy.txt

RUN cd /ComfyUI/custom_nodes/ && \
    git clone https://github.com/city96/ComfyUI-GGUF.git && \
    cd ComfyUI-GGUF && \
    pip install --no-cache-dir -r requirements.txt

# Create model directories (models will be downloaded on-demand)
RUN mkdir -p /ComfyUI/models/unet /ComfyUI/models/vae /ComfyUI/models/clip /ComfyUI/models/loras


COPY . .
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]