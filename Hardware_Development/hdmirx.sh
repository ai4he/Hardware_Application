#!/bin/bash

# device_id=$(v4l2-ctl --list-devices | grep -A1 hdmirx | grep -v hdmirx | awk -F ' ' '{print $NF}')

# v4l2-ctl -d $device_id --set-dv-bt-timings query

# width=$(v4l2-ctl -d $device_id --get-dv-timings | grep "Active width" |awk -F ' ' '{print $NF}')
# heigh=$(v4l2-ctl -d $device_id --get-dv-timings | grep "Active heigh" |awk -F ' ' '{print $NF}')

trap 'onCtrlC' INT
function onCtrlC () {
	echo 'Ctrl+C is captured'
	killall gst-launch-1.0
	exit 0
}

export XDG_RUNTIME_DIR=/run/user/1000
gst-launch-1.0 alsasrc device=hw:2,0 ! audioconvert ! audioresample ! queue !  alsasink device="hw:1,0" &
# gst-launch-1.0 v4l2src device=/dev/video11 ! videoconvert ! video/x-raw,width=1920,height=1080,framerate=10/1 ! fpsdisplaysink sync=false video-sink="autovideosink" &
# gst-launch-1.0 v4l2src device=$device_id ! queue ! video/x-raw,format=RGB ! capssetter replace = true caps="video/x-raw,format=BGR,width=$width,height=$heigh" ! glimagesink &
gst-launch-1.0 v4l2src device=/dev/video11 ! videoconvert ! capssetter join=false caps="video/x-raw,width=1920,height=1080,framerate=10/1" replace=true ! fpsdisplaysink sync=false autovideosink &



gst-launch-1.0 --gst-debug=capssetter:5 videotestsrc !
video/x-bayer,format=rggb,width=640,height=480,framerate=10/1 ! capssetter
join=false caps="video/x-bayer,format=gbrg,width=640,height=480,framerate=10/1"
replace=true ! bayer2rgb ! videoconvert ! xvimagesink





#capssetter replace = true caps="video/x-raw,format=BGR,width=$width,height=$heigh" !

echo "[Ctrl + C] exit"
while true 
do
	sleep 10
done


