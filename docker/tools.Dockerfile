FROM centos:7

RUN yum update -y
RUN yum install -y sudo curl

# Setup docker
ARG DOCKER_GID=994
RUN sudo groupadd -g $DOCKER_GID docker
RUN curl -fsSL https://get.docker.com/ | sh

# Create User in container which should be same as in host
ARG USER=jenkins
ARG USER_UID=1001
ENV C_USER ${USER}
ENV C_USER_UID ${USER_UID}
ENV HOME "/home/${C_USER}"

RUN mkdir -p ${HOME}
RUN chmod -R 755 /home
RUN chown -R ${C_USER_UID}:${C_USER_UID} ${HOME}
RUN adduser \
    --home "${HOME}" \
    --shell /bin/bash \
    --uid "${C_USER_UID}" \
    "${C_USER}"
#RUN adduser "${C_USER}" sudo
RUN echo "${C_USER} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    echo "Defaults    timestamp_timeout=-1" >> /etc/sudoers

ENV USER ${USER}
WORKDIR ${HOME}

# Add user to docker group(s)
RUN sudo usermod -aG docker $USER
#RUN sudo usermod -aG libvirt $USER


RUN yum update -y
RUN yum install -y \
    epel-release \
    https://www.rdoproject.org/repos/rdo-release.rpm
RUN yum update -y
RUN yum install -y \
    python36-pip \
    net-tools \
    git \
    tcpdump \
    vim \
    make \
    gcc \
    python36-devel \
    libffi-devel \
    openssl-devel \
    python36-sphinx \
    python36-wheel \
    python36-virtualenv \
    python36-virtualenvwrapper \
    libguestfs-tools \
    python-heat-agent \
    libselinux-python \
    wget \
    bash-completion \
    openssh-clients \
    nmap \
    net-snmp-utils \
    libnl3-devel \
    python-devel \
    lksctp-tools \
    unzip \
    perl \
    pcre-devel \
    zlib-devel \
    skopeo

RUN yum clean all && \
    rm -rf /var/cache/yum && \
    wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64 && chmod +x ./jq && cp jq /usr/bin && \
    wget https://bootstrap.pypa.io/get-pip.py && \
    python get-pip.py

RUN python -m pip install \
    ansible==2.7.6 \
    robotframework==3.1.1 \
    robotframework-requests==0.5.0 \
    robotframework-sshlibrary==3.3.0 \
    decorator==3.4.0 \
    ethtool==0.14 \
    py-dmidecode==0.0.2 \
    sshuttle \
    j2cli \
    j2cli[yaml] \
    hiyapyco

RUN pip3 install --upgrade setuptools
RUN pip3 install git+git://github.com/ansible/ansible.git@stable-2.7
RUN pip3 install yamlordereddictloader netaddr
RUN pip3 install selinux # There are no libraries for Python 3 in yum, shim from pip must be installed
RUN pip3 install yq

# Downgrade pyvcloud to version 21.0.1.dev3
RUN pip3 install --upgrade pyvcloud==21.0.1.dev3

RUN pip3 install --ignore-installed python-openstackclient python-heatclient python-keystoneclient

# vSphere cli prerequisite
RUN yum install -y \
    e2fsprogs-devel \
    libuuid-devel \
    openssl-devel \
    perl-devel
RUN yum install -y \
    glibc.i686 \
    zlib.i686
RUN yum install -y \
    perl-XML-LibXML \
    libncurses.so.5 \
    perl-Crypt-SSLeay \
    perl-CPAN
RUN yum install -y \
    perl-Test-Base \
    perl-IPC-Run \
    perl-Test-LongString \
    cpanminus \
    expect

# VCD
RUN pip3 install vcd-cli
ENV LC_ALL=en_US.utf8

# openssl
WORKDIR ${HOME}
RUN wget https://ftp.openssl.org/source/old/1.1.1/openssl-1.1.1.tar.gz
RUN tar xf openssl-1.1.1.tar.gz
WORKDIR ${HOME}/openssl-1.1.1
RUN ./config --prefix=/usr --openssldir=/etc/ssl --libdir=lib no-shared zlib-dynamic
RUN make install
RUN export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib64
RUN echo "export LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib64" >> ~/.bashrc
WORKDIR ${HOME}
RUN rm openssl-1.1.1.tar.gz

# cloud-utils
WORKDIR /opt
RUN wget https://launchpad.net/cloud-utils/trunk/0.31/+download/cloud-utils-0.31.tar.gz
RUN tar -xf cloud-utils-0.31.tar.gz
ENV PATH "${PATH}:/opt/cloud-utils-0.31/bin"
RUN rm cloud-utils-0.31.tar.gz
WORKDIR ${HOME}

# Terraform
ARG TF_VERSION="0.12.10"
RUN wget https://releases.hashicorp.com/terraform/${TF_VERSION}/terraform_${TF_VERSION}_linux_amd64.zip
RUN unzip terraform_${TF_VERSION}_linux_amd64.zip
RUN mv terraform /usr/local/bin/
RUN rm -f terraform_${TF_VERSION}_linux_amd64.zip

# Packer
ARG PACKER_VERSION="1.4.4"
RUN wget https://releases.hashicorp.com/packer/${PACKER_VERSION}/packer_${PACKER_VERSION}_linux_amd64.zip
RUN unzip packer_${PACKER_VERSION}_linux_amd64.zip
RUN mv packer /usr/local/bin/
RUN rm -f packer_${PACKER_VERSION}_linux_amd64.zip

#WORKDIR /root
RUN pip3 install docker-py

USER ${C_USER}

CMD [ "/bin/bash" ]
