import serial
import time
import pymysql
from Funcz import *

print("Initializing...")
Globalz = {
    'DefaultRepeat': '15',
}
AllThreads = []
DataReceived=''






ser = serial.Serial('COM9', 9600)

time.sleep(4)

MyThread = ReadArduino(ser)
MyThread.start()

print("I'm Ready!")

while 1:
    try:

        connection = pymysql.connect(host='192.168.0.200',
                                     user='Spike',
                                     password='spatczek',
                                     db='Domz',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM Radio WHERE todo=1"
            cursor.execute(sql)

            result = list(cursor)#cursor.fetchall()
            DoAPause = 0
            for row in result:
                if row['wait_time'] == 0:
                    try:
                        toWriteCode = DecToBin24(row['value']) # 4527420  4527411
                        toWritePulse = str(row['pulselength'])
                        #"function_name": "SendRadioCode",
                        toWrite = '{"Value":"' + toWriteCode + '","PulseLength":"' + toWritePulse + '"}'
                        # while toWrite not in Globalz['DataReceived']:
                        #     ser.write(toWrite.encode('utf-8'))
                        #     time.sleep(0.5)
                        ser.write(toWrite.encode('utf-8'))
                        #Globalz['DataReceived'] = ''
                    except TypeError as errorrecup:
                        print('erreur d\'ecriture :', errorrecup)
                        print(getError(sys.exc_info()))
                        fail = True
                    except:
                        print('erreur d\'ecriture')
                        print(getError(sys.exc_info()))
                        fail = True
                else:
                    print("timer on id = {0}".format(row['id']))
                    tmpT = WaitTime(row['wait_time'],row['id'])
                    AllThreads.append((tmpT, row['id']))
                    tmpT.start()
                try:
                    sql = "UPDATE Radio SET todo = 0, wait_time = 0 WHERE id = %s"
                    cursor.execute(sql, (row['id'],))
                    connection.commit()
                except:
                    print("erreur d'update pour remettre todo et wait time a 0")
                    print(getError(sys.exc_info()))
                    fail = True
                #time.sleep(2)
    except:
        print("erreur d'update")
        print(getError(sys.exc_info()))
        fail = True
        time.sleep(0.5)
    finally:
        connection.close

    try:

        connection = pymysql.connect(host='192.168.0.200',
                                     user='Spike',
                                     password='spatczek',
                                     db='Domz',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT * FROM Radio WHERE cancel_time=1"
            cursor.execute(sql)

            result = list(cursor)  # cursor.fetchall()
            DoAPause = 0
            for row in result:
                for thr, ID in AllThreads:
                    if ID == row['id']:
                        thr.stop()
                req = "UPDATE Radio SET cancel_time = 0 WHERE id = %s"
                cursor.execute(req, (row['id'],))
                connection.commit()
                print("time_wait cancelled")
    except:
        print("erreur d'update de cancel")
        print(getError(sys.exc_info()))
        fail = True
    finally:
        connection.close

print("fin du while... reste a comprendre pourquoi")





