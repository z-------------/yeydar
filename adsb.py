import socket, math, json, time
from tornado import websocket, web, ioloop
from bisect import bisect_left

CPR_CONST = (10.4704713, 14.82817437, 18.18626357, 21.02939493, 23.54504487,
    25.82924707, 27.9389871, 29.91135686, 31.77209708, 33.53993436,
    35.22899598, 36.85025108, 38.41241892, 39.92256684, 41.38651832,
    42.80914012, 44.19454951, 45.54626723, 46.86733252, 48.16039128,
    49.42776439, 50.67150166, 51.89342469, 53.09516153, 54.27817472,
    55.44378444, 56.59318756, 57.72747354, 58.84763776, 59.95459277,
    61.04917774, 62.13216659, 63.20427479, 64.26616523, 65.3184531,
    66.36171008, 67.39646774, 68.42322022, 69.44242631, 70.45451075,
    71.45986473, 72.45884545, 73.45177442, 74.43893416, 75.42056257,
    76.39684391, 77.36789461, 78.33374083, 79.29428225, 80.24923213,
    81.19801349, 82.13956981, 83.07199445, 83.99173563, 84.89166191,
    85.75541621, 86.53536998, 87.0)

def nround(n):
    if n % 0.5 == 0:
        return math.ceil(n)
    else:
        return round(n)

def hex2bin(hex_str):
    bin_str = bin(int(hex_str, 16))[2:]
    return(bin_str.zfill(math.ceil(len(bin_str)/2)*2))

def NL(x):
    # NL function and CPR_CONST from bma13's adsb-sender
    return 59 - bisect_left(CPR_CONST, abs(x))

def extract_latlon_b(bin_str):
    latlon = {
        "lat": None,
        "lon": None
    }
    
    latlon["lat"] = bin_str[22:39]
    latlon["lon"] = bin_str[39:56]
    
    return(latlon)

def calc_latlon(cpr1, cpr2):
    frame_1 = cpr1
    frame_2 = cpr2

    frame_1_latlon_b = extract_latlon_b(hex2bin(frame_1))
    frame_2_latlon_b = extract_latlon_b(hex2bin(frame_2))

    lat0 = int(frame_1_latlon_b["lat"], 2)
    lat1 = int(frame_2_latlon_b["lat"], 2)
    lon0 = int(frame_1_latlon_b["lon"], 2)
    lon1 = int(frame_2_latlon_b["lon"], 2)

    j = int(((59 * lat0 - 60 * lat1) / 131072) + 0.5)

    rlat0 = 6 * (j % 60 + lat0 / 131072)
    rlat1 = (360 / 59) * (j % 59 + lat1 / 131072)

    nl0 = NL(rlat0)
    nl1 = NL(rlat1)
    
    if nl0 == nl1:
        ni = max(1, nl1-1)

        dlon1 = 360 / ni

        M = nround((((lon0 * (nl1 - 1)) - (lon1 * nl1)) / 131072) + 0.5)

        lon = dlon1 * (M % ni + lon1 / 131072)

        return([rlat1, lon])
    else:
        return([None, None])

def analyse_stream(stream):
    for frame in stream:
        frame = frame[1:]
        first_byte = frame[0:2]

        if len(frame) == 28 and hex2bin(first_byte)[0:5] == "10001": # check that it has correct length and downlink format (DF) = 17
            icao = frame[2:8]

            if not icao in craft_frames:
                craft_frames[icao] = [None] * 2

            # substring the useful part
            cpr_data = frame[8:-6]

            # extract type code (TC)
            tc_hex = cpr_data[0:2]
            tc_bin = hex2bin(tc_hex)[0:5]

            if tc_bin == "01011": # check that TC is 11
                # extract flag
                flag = int(hex2bin(cpr_data)[21])
                craft_frames[icao][flag] = cpr_data

    for icao in craft_frames:
        if craft_frames[icao][0] and craft_frames[icao][1]:
            if not icao in craft_info:
                craft_info[icao] = {
                    "updated": None,
                    "pos": [None] * 2
                }
            
            craft_info[icao]["pos"] = calc_latlon(craft_frames[icao][0], craft_frames[icao][1])
            craft_info[icao]["updated"] = nround(time.time())

class EchoWebSocket(websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True
    
    def open(self):
        print("WebSocket opened")
        
    def on_message(self, message):
        self.write_message(json.dumps(craft_info))

    def on_close(self):
        print("WebSocket closed")
        
app = web.Application([
    (r"/websocket", EchoWebSocket),
])

craft_frames = {}
craft_info = {}

telnet_ip = "118.141.29.177"
telnet_port = 47806

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((telnet_ip, telnet_port))

def p_callback():
    data = client_socket.recv(512).decode("utf-8")
    analyse_stream(data.split(";\r\n"))
    
    for icao in craft_info:
        now = time.time()
        updated = craft_info[icao]["updated"]
        
        if now - updated > 20:
            craft_frames.pop(icao, 0)
            craft_info.pop(icao, 0)
    
    print(craft_info)

if __name__ == "__main__":
    app.listen(8888)
    ioloop.PeriodicCallback(p_callback, 10).start()
    ioloop.IOLoop.instance().start()