#!/bin/bash

# concat today's logs to mp3; make sure there are no current recordings first (lock files).

date=`date +%Y%m%d`

locked=`ls -l ~/.openbroadcaster/lineinlogs/$date-*.lock | wc -l`
while [[ $locked != "0" ]]
do
        sleep 60
        locked=`ls -l ~/.openbroadcaster/lineinlogs/$date-*.lock | wc -l`
done

rm -f ~/.audiolog_concat.list
for file in ~/.openbroadcaster/lineinlogs/$date-*;
        do echo file \'$file\' >> ~/.audiolog_concat.list;
done

sort -o ~/.audiolog_concat.list ~/.audiolog_concat.list

ffmpeg -f concat -safe 0 -i ~/.audiolog_concat.list ~/.openbroadcaster/lineinlogs/$date.mp3
