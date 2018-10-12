ip link add name qemu_bridge type bridge &&
ip link set qemu_bridge up &&
ip link set ens33 up &&
ip link set ens33 master qemu_bridge

