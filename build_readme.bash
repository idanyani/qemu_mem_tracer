#!/bin/bash

if ps -p $1 > /dev/null
then
   exit 1
fi
exit 0
