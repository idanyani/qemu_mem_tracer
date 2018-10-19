#!/bin/bash

# Took the idea from https://stackoverflow.com/questions/8410439/how-to-avoid-echo-closing-fifo-named-pipes-funny-behavior-of-unix-fifos/8410538#8410538
(while cat $1 > $2; do : Nothing; done)
