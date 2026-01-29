import serial
import time

ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1) # match arduino baud
time.sleep(2) #Settle

ser.write(b'Hellow Arduino\n"')
print(ser.readline().decode().strip()) # echo back
ser.close()
