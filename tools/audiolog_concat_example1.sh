#!/bin/bash

# concat yesterday's logs to a single ogg file

date=`date -d "yesterday 13:00" +%Y%m%d`
rm -f ~/.audiolog_concat.list
for file in ~/.openbroadcaster/lineinlogs/$date-*;
	do echo file \'$file\' >> ~/.audiolog_concat.list;
done
sort -o ~/.audiolog_concat.list ~/.audiolog_concat.list
ffmpeg -f concat -safe 0 -i ~/.audiolog_concat.list -c copy ~/.openbroadcaster/lineinlogs/$date.ogg
