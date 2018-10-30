obj-m += simple_kernel_memory_intensive_workload_lkm.o

all:
	make -C /lib/modules/4.15.0-36-generic/build M=$(PWD) modules

clean:
	make -C /lib/modules/4.15.0-36-generic/build M=$(PWD) clean
	