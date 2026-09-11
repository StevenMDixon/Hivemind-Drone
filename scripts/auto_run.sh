#!/usr/bin/bash

sleep 10
sudo mount.cifs //Laptop-Base-Station/d /home/piratestation/nick -o user=user,password=1

cd ~/Desktop/ 
. env/bin/activate

python3 main.py
