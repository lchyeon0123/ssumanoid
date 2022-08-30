import cv2
import math
import numpy as np
import pytesseract
import os
import serial
from charset_normalizer import detect
from numpy import rec
from PIL import Image
from util import *


capture = cv2.VideoCapture(0)
W_View_size = 320
H_View_size = int(W_View_size/1.333)
FPS = 30
capture.set(3, W_View_size)
capture.set(4, H_View_size)
capture.set(5, FPS)
direction = ''
BPS = 4800
yellow_range = [(15, 100, 0), (45, 455, 455)]

alpha = ''
color = ''


def TX_data_py2(ser, one_byte):  # one_byte= 0~255
    print("hjk", one_byte)
    # ser.write(chr(int(one_byte)))          #python2.7
    ser.write(serial.to_bytes([one_byte]))  # python3


def RX_data(ser):
    if ser.inWaiting() > 0:
        result = ser.read(1)
        RX = ord(result)
        return RX
    else:
        return 0


serial_port = serial.Serial('/dev/ttyS0', BPS, timeout=0.01)
TX_data_py2(serial_port, 128)


def getDegree(p1, p2):
    rad = math.atan(float(p2[1]-p1[1])/(p2[0]-p1[0]))
    return round(rad*(180/(np.pi)), 3)


def getSubDegree(deg1, deg2):
    if deg1 > deg2:
        ang1 = deg1-deg2
    else:
        ang1 = deg2-deg1
    ang2 = 180-ang1
    if abs(ang1) > abs(ang2):
        return ang2
    else:
        return ang1


def linetracing(direction):
    if float(direction) <= -10:
        return 162
    elif float(direction) >= 10:
        return 161
    else:
        if cx <= 120:
            return 163
        elif cx >= 200:
            return 164
        else:
            return 160


def detectAlpha(img):
    global alpha
    alphas = ['A', 'B', 'C', 'D', 'N', 'S', 'W', 'E']
    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    img = cv2.copyMakeBorder(
        img, 50, 50, 50, 50, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    #cv2.imshow("detect", img)
    filename = "{}.png".format(os.getpid())
    cv2.imwrite(filename, img)
    text = pytesseract.image_to_string(
        Image.open(filename), config="--psm 10", lang='eng')
    os.remove(filename)
    try:
        if alphas.count(text[0]) > 0:
            alpha = text[0]
        else:
            alpha = ''
    except:
        alpha = ''


def getMessage(alpha, color):
    message = ''
    roomAlphas = ['A', 'B', 'C', 'D']
    directionAlphas = ['N', 'S', 'W', 'E']
    direction = {'N': 'North', 'S': 'South', 'W': 'West', 'E': 'East'}
    if roomAlphas.count(alpha) > 0:
        message = 'Find {} citizen in room {}'.format(color, alpha)
    elif directionAlphas.count(alpha) > 0:
        message = 'Shout "{}"'.format(direction[alpha])
    return message


def detectDirection(alpha):
    if alpha == 'E':
        TX_data_py2(serial_port, 140)
    elif alpha == 'W':
        TX_data_py2(serial_port, 141)
    elif alpha == 'S':
        TX_data_py2(serial_port, 142)
    elif alpha == 'N':
        TX_data_py2(serial_port, 143)
    pass


while True:
    input = cv2.waitKey(1)
    _, img = capture.read()
    res = img.copy()
    tmp = RX_data(serial_port)
    print(tmp)

    if tmp == 150:
        mask = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(mask, yellow_range[0], yellow_range[1])
        img = cv2.bitwise_and(img, img, mask=mask)
        contours, _ = cv2.findContours(mask, 1, cv2.CHAIN_APPROX_NONE)
        if len(contours) > 0:
            c = max(contours, key=cv2.contourArea)
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                rows, cols = img.shape[:2]
                [vx, vy, x, y] = cv2.fitLine(c, cv2.DIST_L2, 0, 0.01, 0.01)
                try:
                    y1 = int((-x*vy/vx)+y)
                    y2 = int(((cols-x)*vy/vx)+y)
                    cv2.circle(res, (cx, cy), 5, (255, 255, 255), -1)

                    cv2.line(img, (0, y1), (cols-1, y2), (0, 0, 255), 2)

                    degMid = 90
                    deg = getDegree((0, y1), (cols-1, y2))
                    resultDeg = getSubDegree(degMid, deg)
                    resultDeg = round(resultDeg, 1)
                    if deg > 0:
                        direction = '+'+str(resultDeg)
                    else:
                        direction = '-'+str(resultDeg)
                    cv2.drawContours(res, c, -1, (0, 255, 0), 2)
                except Exception as e:
                    print(e)
        if direction != '':
            res = cv2.putText(res, direction, (0, 50), 0, 1, (0, 255, 0), 2)
            TX_data_py2(serial_port, linetracing(direction))
        else:
            TX_data_py2(serial_port, 159)

    elif tmp == 151:
        rect = getBlackObject(img)

        if rect['w'] > 0:
            img_alpha = cv2.getRectSubPix(img, (int(rect['w']), int(
                rect['h'])), (int(rect['cx']), int(rect['cy'])))
            img = drawRects(img, [rect])
            detectAlpha(img_alpha)
            color = 'Black'
            detectDirection(alpha)

        if alpha != '' and color != '':
            img = drawText(img, 1, 'Text: '+alpha)
            img = drawText(img, 2, 'Color: '+color)

    else:
        pass

    cv2.imshow("camera", res)
    cv2.rectangle(img, (focus['x'], focus['y']), (focus['x']+focus['w'], focus['y']+focus['h']),
                  (255, 255, 255), 2)
    cv2.imshow("camera", img)