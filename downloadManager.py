import os
import sys
import time
import signal
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.error import HTTPError

SELF_DIR = os.path.dirname(os.path.realpath(__file__))
CURRENT_SIZE = 0
TOTAL_REMAINING_SIZE = 0
TOTAL_SIZE = 0
EXIT = False
maxSendRateBytesPerSecond = (500*1024)
CHUNK_SIZE = 2 ** 10
line_length = 0


rx_prev = 0
rx_speed = 0
last_speed_time = 0


def ConvertSecondsToBytes(numSeconds):
    return numSeconds*maxSendRateBytesPerSecond


def ConvertBytesToSeconds(numBytes):
    if numBytes <= 0:
        return 0
    else:
        return float(numBytes)/maxSendRateBytesPerSecond


def signal_handler(sig, frame):
    global EXIT
    EXIT = True


def progress(count, total, directory, filename, suffix=''):
    global tx_prev, rx_prev, tx_speed, rx_speed, last_speed_time, line_length
    # tx = get_bytes('tx')
    # tx_speed = tx - tx_prev
    # print('TX: ', tx_speed, 'bps')
    # tx_prev = tx

    if time.time() - last_speed_time > 1:
        rx = os.path.getsize(os.path.join(directory, filename))
        if rx - rx_prev > 0:
            rx_speed = rx - rx_prev
        rx_prev = rx
        last_speed_time = time.time()

    if suffix == '':
        suffix = str(round(count / (2 ** 20))) + " MB"
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write(' '*line_length + '\r')
    line = '[%s] %s%s ... %s ... %0.0f KB/S\r' % (
        bar, percents, '%', suffix, rx_speed / (2 ** 10))
    line_length = len(line)
    sys.stdout.write(line)
    sys.stdout.flush()


def download(url, directory=SELF_DIR):
    purl = urlparse(url)
    headers = {
        'Host': purl.hostname,
    }

    filename = os.path.basename(purl.path)
    if filename.find('/') >= 0 or filename == '':
        raise RuntimeError('Invalid save path ' + filename)

    global CURRENT_SIZE, TOTAL_REMAINING_SIZE, TOTAL_SIZE, rx_prev
    try:
        CURRENT_SIZE = os.path.getsize(os.path.join(directory, filename))
    except FileNotFoundError:
        CURRENT_SIZE = 0
    rx_prev = CURRENT_SIZE
    headers['Range'] = 'bytes=' + str(CURRENT_SIZE) + '-'
    #
    response = None
    req = Request(url=url, headers=headers)
    try:
        response = urlopen(req)
    except HTTPError as e:
        print('ERROR: "{}" when connecting to {}'.format(e, url))
        sys.exit(1)
    #
    TOTAL_REMAINING_SIZE = int(response.info()['Content-Length'])
    TOTAL_SIZE = CURRENT_SIZE + TOTAL_REMAINING_SIZE
    print("Current Size = " + str(round(CURRENT_SIZE / (2 ** 20))) + " MB")
    print("Remaining Size = " + str(round(TOTAL_REMAINING_SIZE / (2 ** 20))) + " MB")
    print("Total Size = " + str(round(TOTAL_SIZE / (2 ** 20))) + " MB")

    bytesAheadOfSchedule = 0

    prevTime = None

    with open(os.path.join(directory, filename), 'ab') as fh:
        while True:
            now = time.time()
            if (prevTime != None):
                bytesAheadOfSchedule = bytesAheadOfSchedule - \
                    ConvertSecondsToBytes(now-prevTime) + CHUNK_SIZE
            prevTime = now
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            fh.write(chunk)
            CURRENT_SIZE += len(chunk)
            progress(CURRENT_SIZE, TOTAL_SIZE,
                     directory=directory, filename=filename)
            time.sleep(ConvertBytesToSeconds(bytesAheadOfSchedule))
            if EXIT:
                fh.close()
                print('\nFile Closed!')
                break
        if TOTAL_SIZE == CURRENT_SIZE:
            print('\nDownload complete!')


signal.signal(signal.SIGINT, signal_handler)
download("https://ia801602.us.archive.org/11/items/Rick_Astley_Never_Gonna_Give_You_Up/Rick_Astley_Never_Gonna_Give_You_Up.mp4")
