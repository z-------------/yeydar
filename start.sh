python3 adsb.py &
cd web; python3 -m http.server

trap "killall python3" EXIT