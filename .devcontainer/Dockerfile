FROM python:3.8-bullseye

ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

RUN apt-get update &&                        \
  apt-get install -y --no-install-recommends \
  curl                                       \
  doxygen                                    \
  graphviz                                   \
  ssh                                        \
  sudo                                       \
  zsh                                        \
  && rm -rf /var/lib/apt/lists/*

# Install just
RUN curl --proto '=https' -sSf https://just.systems/install.sh \
    | sudo bash -s -- --tag 1.13.0 --to /usr/local/bin

# Add the render group and a user with sudo permissions for the container
RUN useradd -Um developer \
    && echo developer ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/developer \
    && chmod 0440 /etc/sudoers.d/developer

CMD mkdir -p /workspace && chown developer:developer /workspace

WORKDIR /workspace
VOLUME /workspace

USER developer
