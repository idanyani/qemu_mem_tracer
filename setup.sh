#!/bin/bash


#HOW TO USE:		
#  setup.sh <guest_image_path> <snapshot_name>	

set -e 
set -o pipefail

checkPackages()
{
    if (( "$#" < 1 )); then
        echo "Usage: $0 LIST_OF_PACKAGES"
        exit -1
    fi

    packages="$@"
    declare -a packages_to_install
    for package in $packages; do
        dpkg-query --show --showformat='${Status}' $package
        echo ""
        if (( $? > 0 )); then
            packages_to_install+=($package)
        fi
    done

    if (( ${#packages_to_install[@]} > 0 )); then 
        echo "To use the tracer,you need to install the following packages:"
        for package in $packages_to_install; do
            echo "$package"
        done
        echo "Do you want to install the packages? (y/n)"
        read answer
        if [ "$answer" == "${answer#[Yy]}" ] ;then
            exit -1
        fi
    fi

}

if (( "$#" < 2 )); then
    echo "Usage: $0 <guest_image_path> <snapshot_name>"
    exit -1
fi


GUEST_IMAGE_PATH=$1
SNAPSHOT_NAME=$2

checkPackages python python3.7 expect pkg-config libglib2.0-dev libpixman-1-dev zlib1g-dev libcurl4-gnutls-dev
git clone https://github.com/orenmn/qemu_with_GMBEOO
git clone https://github.com/orenmn/qemu_mem_tracer
cd qemu_with_GMBEOO && git submodule init && git submodule update --recursive && git checkout mem_tracer
sudo apt-get -y install python
echo | sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get -y update    
sudo apt-get -y install python3.7
/usr/bin/env python3.7 --version
sudo add-apt-repository universe
sudo apt-get -y install expect
sudo apt-get -y install pkg-config
sudo apt-get -y install libglib2.0-dev
sudo apt-get -y install libpixman-1-dev 
sudo apt-get -y install zlib1g-dev
sudo apt-get -y install libcurl4-gnutls-dev
../qemu_mem_tracer/build.py `pwd` 
../qemu_mem_tracer/build.py `pwd` --dont_compile_qemu --run_tests --guest_image_path $GUEST_IMAGE_PATH --snapshot_name $SNAPSHOT_NAME

echo "Setup Completed successfully."
