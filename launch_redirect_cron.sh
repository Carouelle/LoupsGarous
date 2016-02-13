#!/bin/bash

weekNb=`date +"%W"`

echo "Week $weekNb"

if [[ `expr $weekNb % 2` -eq 0 ]]
then
	echo "Wrong week"
        exit
fi

cd /etc/unrealircd/loup/
killall loup.py

echo $$ > pid.pid

while [ 1 ]
do
	date
	./loup.py -r
	sleep 5
done
