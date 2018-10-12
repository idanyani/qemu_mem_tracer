#!/snap/bin/expect -f

# I would run this script a second before executing `savevm` in the monitor,
# and so when I later do `loadvm`, the script would continue running just
# before the sleep ends.
sleep 2

spawn scp orenmn@10.0.2.2:test_elf test_elf_from_ubuntu
spawn scp -P 10022 aoe.aoeu oren@10.0.2.2:test_elf

set timeout 60
expect "assword:"

send "123456\r"
expect " 100% "

chmod 777 test_elf_from_ubuntu
./test_elf_from_ubuntu

interact
