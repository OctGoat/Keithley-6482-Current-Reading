# -*- coding: utf-8 -*-
"""
for Keithley 6482
debugged and refined at 20250227
@author: Nafiy
python version:3.8.6
"""
"""
2.28 Update
1.增加了偏压自动增加循环；
2.
"""
import argparse
import os
import random
import re
import string
import sys
import time

import serial
from serial import Serial
from typing import List

os.chdir('E:/')     #将生成的.dat文件保存到E盘下
version_str: str = '20250227'

parser = argparse.ArgumentParser(
    description='Welcome to 6482 v.' + version_str + ' help menu. 6482 is a simple software data logger for Keithley 6482 pico-ammeter.')

parser.add_argument("-slp", "--sleeptime", type=float, action='store', nargs='?', const=1.0, default=1.0,
                    metavar='[seconds]',
                    help="Sleeptime during one measure and another, in seconds.")

parser.add_argument("-rg", "--manualrange", type=float, action='store', nargs='?', const=0.02, default=-1,
                    metavar='[upper range]',
                    help="Manual range will be set to on. Available upper range values: 2e-2,2e-3,...,2e-9. If '--manualrange' is called without argument will be set to 20mA.")

parser.add_argument("-p", "--plot", action="store_true",  # will store false otherwise
                    help="Plot when data acquisition end.")

parser.add_argument("--nosave", action="store_true",  # will store false otherwise
                    help=argparse.SUPPRESS)

args = parser.parse_args()


def save_to_(data_array, file, append=False):

    if not append:
        with open(file, 'w') as f:
            for index in range(0, len(data_array)):
                line = str(data_array[index][0]) + ' ' + str(data_array[index][1])
                f.write(line + '\n')
    else:
        with open(file, 'a') as f:
            for index in range(0, len(data_array)):
                line = str(data_array[index][0]) + ' ' + str(data_array[index][1])
                f.write(line + '\n')


if __name__ == '__main__':

    COMPORT = input("请输入端口号并回车 （如：COM3）")
    if result := re.findall(R"COM\d{1,2}", COMPORT):
        COMPORT = result[0]
    else:  # 默认端口号COM3
        COMPORT = "COM3"

    # configure the serial connections (the parameters differs on the device you are connecting to)
    ser: Serial = serial.Serial(    #根据所使用的设备修改
        port=COMPORT,
        baudrate=9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout = 5     #防止READLINE()卡死
    )

    print(''' Instrumental World ''' + version_str + ''' A Keithley 6482 SCPI controller and data logger. ''')

    if ser.is_open:
        print('Welcome. Connection with port ' + COMPORT + ' established.')
    else:
        print("Fail to open port")

    input("Press Enter to START. Press Ctrl + C when you are done.")

    i = 0
    arr = []
    ser.write(b'*RST\r\n')
    time_str = time.strftime("-%Y%m%d_%H%M%S")
    sleep_time = args.sleeptime
    print('Reset..OK')
    ser.write(b'FORMat:ELEMents READing, TIME\r\n')
    ser.write(b'SYSTem:TIME:RESet\r\n')
    ser.write(b'TRACe:TSTamp:FORMat:ABS\r\n')
    print('Data formatting..OK')
    ser.write(b'CONF:CURR\r\n')
    print('Arm and trig conf, zero check..OK')
    if args.manualrange != -1.0:
        range_flag = 0.0
        for dex in range(2, 10):
            if args.manualrange == 2 * 10 ** (-dex):
                ser.write(bytes('CURR:RANG ' + str(args.manualrange) + '\r\n', encoding='utf-8'))
                print('Upper range set to ' + str(args.manualrange) + 'A.. OK')
                range_flag = 1.0
        if range_flag == 0.0:
            print('''Warning!!!''')
            print("Warning!: Forbidden upper range value. Autorange will be set on.")
    else:
        print('Autorange..OK')
    print('Keithley 6482 ready.')

    i = 1  # loop iteration
    j = 0  # backup number
    BACK_UP_AFTER = 10  # 表示每10次循环就进行备份
    alphaid = random.choice(string.ascii_letters)

    voltage = 1.0
    while True:
        
        try:
            # ser.write(f'SOUR1:VOLT {voltage:1f}\r\n'.encode('utf-8'))
            # print((f'SOUR1:VOLT {voltage:.1f}\r\n')) #测试用
            if  i % 10 == 0 and i != 0: 
                voltage += 0.1
                
            if voltage > 10:  #量程是多少就改成多少
                voltage = 1.0
            # num = 1
            ser.write(f'SOUR1:VOLT {voltage:.1f}\r\n'.encode('utf-8'))

            ser.write(b'READ?\r\n')
            i += 1
            time.sleep(sleep_time)
            c: str = ser.readline().decode('utf-8')  # read line and convert byte object to utf-8 encoded string
            c: List[str] = re.findall(r".(.*).{2}", c)[0].split(',')
            c: List[float] = [float(read) for read in c]
            print(F"{c[0]} A,{c[1]} s")
            arr.append(c)
            if args.nosave == False and i % BACK_UP_AFTER == 0:
                print('Backing-up to ' + '6482' + time_str + alphaid + '_backup.dat...')
                arr_backup = arr
                if j == 0:
                    save_to_(arr_backup, '6482' + time_str + alphaid + '_backup.dat')
                else:
                    save_to_(arr_backup[BACK_UP_AFTER * j:BACK_UP_AFTER * (j + 1)],
                             '6482' + time_str + alphaid + '_backup.dat', append=True)
                j += 1
            # i += 1
            # num = 0

        except KeyboardInterrupt:
            print(args.nosave)
            if not args.nosave: #args.nosave == False
                print('All done, saving to ' + '6482' + time_str + alphaid + '.dat...')
                save_to_(arr, '6482' + time_str + alphaid + '.dat')

            ser.write(b'ABORt\r\n')
            ser.close()
            print('Goodbye!')
            # If backup file exists, delete it
            if os.path.isfile('6482' + time_str + alphaid + '_backup.dat'):
                os.remove('6482' + time_str + alphaid + '_backup.dat')
            else:
                print("Warning: Backup file not found.")
            # print(os.path.isfile('6482' + time_str + alphaid + '_backup.dat'))  #False
            sys.exit(0)
