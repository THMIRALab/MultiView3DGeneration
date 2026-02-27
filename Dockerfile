FROM nvidia/cuda:12.1.0-devel-ubuntu22.04

# Create working directory
WORKDIR /multiview-enigma

# Install system dependencies (no libceres-dev!)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gcc-10 g++-10 \
    cmake \
    ninja-build \
    git \
    curl \
    wget \
    libboost-all-dev \
    libfreeimage-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libabsl-dev \
    libqt5opengl5-dev \
    libglew-dev \
    qtbase5-dev \
    libsqlite3-dev \
    libopenexr-dev \
    libopencv-dev \
    libmetis-dev \
    libflann-dev \
    libcgal-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh && \
    chmod +x Miniconda3-latest-Linux-x86_64.sh && \
    ./Miniconda3-latest-Linux-x86_64.sh -b -p /workspace/miniconda3 && \
    rm Miniconda3-latest-Linux-x86_64.sh
ENV PATH="/workspace/miniconda3/bin:${PATH}"

# Create and activate Conda environment
ENV CONDA_ENV=multiview-enigma
RUN conda create -n $CONDA_ENV python=3.10 -y && \
    echo "source activate $CONDA_ENV" >> ~/.bashrc && \
    conda clean -afy
ENV PATH="/workspace/miniconda3/envs/$CONDA_ENV/bin:$PATH"

# Install Ceres 2.2.0+ from Conda-forge (NOT system package)
RUN conda run -n $CONDA_ENV conda install -c conda-forge ceres-solver=2.2.0 suitesparse eigen=3.3.7 -y
RUN conda run -n $CONDA_ENV conda install -c conda-forge libstdcxx-ng=13.2.0 -y

# Install Conda packages
RUN conda run -n $CONDA_ENV conda install -y ninja cmake pip

# Set compilers and flags
ENV CC=/usr/bin/gcc-10 \
    CXX=/usr/bin/g++-10 \
    CUDAHOSTCXX=/usr/bin/g++-10 \
    CMAKE_BUILD_PARALLEL_LEVEL=1 \
    CXXFLAGS="-fno-lto"

# Copy and build COLMAP inside Conda env
COPY colmap /multiview-enigma/colmap
WORKDIR /multiview-enigma/colmap
RUN mkdir build && cd build && \
    conda run -n $CONDA_ENV cmake .. \
        -DCMAKE_CUDA_ARCHITECTURES="86;87;89" \
        -DCMAKE_C_COMPILER=${CC} \
        -DCMAKE_CXX_COMPILER=${CXX} \
        -DCUDA_HOST_COMPILER=${CUDAHOSTCXX} \
        -DCOLMAP_GUI=OFF \
        -DCMAKE_BUILD_TYPE=Release \
        -DPYCOLMAP_BUILD=ON \
        -DPYCOLMAP_ENABLE_GPU=ON \
		-DCMAKE_INSTALL_PREFIX=/workspace/miniconda3/envs/$CONDA_ENV \
		-DCeres_DIR=/workspace/miniconda3/envs/$CONDA_ENV/lib/cmake/Ceres \
        -DSuiteSparse_INCLUDE_DIR_HINTS=/workspace/miniconda3/envs/$CONDA_ENV/include \
        -DSuiteSparse_LIBRARY_DIR_HINTS=/workspace/miniconda3/envs/$CONDA_ENV/lib && \
    conda run -n $CONDA_ENV make -j1 && \
    conda run -n $CONDA_ENV make install

RUN ln -s /workspace/miniconda3/envs/$CONDA_ENV/bin/colmap /usr/local/bin/colmap
# Install COLMAP Python bindings into Conda env
RUN conda run -n $CONDA_ENV pip install /multiview-enigma/colmap

ENV PATH="/workspace/miniconda3/envs/$CONDA_ENV/bin:/workspace/miniconda3/envs/$CONDA_ENV/lib:$PATH"
ENV LD_LIBRARY_PATH="/workspace/miniconda3/envs/$CONDA_ENV/lib:$LD_LIBRARY_PATH"


# Set working directory and copy remaining app
WORKDIR /multiview-enigma
COPY src /multiview-enigma/src
COPY app /multiview-enigma/app
COPY examples /multiview-enigma/examples
COPY requirements.txt /multiview-enigma/requirements.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install app Python dependencies inside Conda
RUN conda run -n $CONDA_ENV pip install --upgrade pip && \
    conda run -n $CONDA_ENV pip install -r requirements.txt && \
    conda clean -afy

EXPOSE 8002
ENTRYPOINT ["/entrypoint.sh"]

# Default command using Conda env
#CMD ["conda", "run", "-n", "multiview-enigma", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
