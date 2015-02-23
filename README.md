# MyMediaRenamer

DESCRIPTION:
A script to consistently rename photo and video files from various sources using EXIF timestamps!

Files are renamed as:

   YYYY_MMDD_HHMMSS(_####)_$$$(_???).ext

   YYYY: year
   MM:   month
   DD:   day
   HH:   hour
   MM:   minute
   SS:   second
   ####: image number (from original file name if present)
   $$$:  camera tag (from directory name)
   ???:  other tag in original file name if present

USAGE:
   mmr.py --directory '<full path to directory>' [--recursive]
   
