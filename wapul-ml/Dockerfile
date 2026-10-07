# syntax=docker/dockerfile:1

# Torch and CUDA come from the base image; the GPU driver here supports CUDA up to 13.0.
# Windows application control blocks torch's DLLs on the host, so experiments run here.
FROM pytorch/pytorch:2.14.1-cuda13.0-cudnn9-runtime

# torch sits in the system Python (PEP 668 managed), so add packages the same way the image did
ENV PIP_BREAK_SYSTEM_PACKAGES=1
# tree-sitter pins match the data repo's scripts, so units split identically
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "sentence-transformers[train]==6.1.0" scikit-learn==1.9.1 lightgbm==4.7.0 \
    tree-sitter==0.26.0 tree-sitter-cpp==0.23.4 tree-sitter-java==0.23.5 tree-sitter-python==0.25.0
# Grammars added after segmenter-v2, in their own layer so the layers above stay as trained
RUN --mount=type=cache,target=/root/.cache/pip     pip install tree-sitter-rust==0.24.2
# Notebook tools in a layer of their own, so the packages the models were trained with stay as built
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install jupyterlab==4.6.4 jupytext==1.19.6

ENV PYTHONUNBUFFERED=1
# Code and data are mounted at run time, not copied; notebooks/ imports wapul_ml from the mount
ENV PYTHONPATH=/work
WORKDIR /work
