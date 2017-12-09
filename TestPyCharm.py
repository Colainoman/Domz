import sys
import serial
import time
import pymysql
import re
from threading import Thread

print("Initializing...")
Globalz = {
    'DefaultRepeat': '15',
}
AllThreads = []
DataReceived=''
expression = r"""^b'{"action":"received","value":(\d*?),"PulseLength":(\d*?),"Protocol":(\d*?)}\\r\\n'$"""
DefaultRepeat = 15

def getError(theError):
    erreur = sys.exc_info()
    typerr = u"%s" % (theError[0])
    typerr = typerr[typerr.find("'")+1:typerr.rfind("'")]
    msgerr = u"%s" % (theError[1])
    return typerr[typerr.find(".")+1:] + ": " + msgerr

def writeInDomz(Val, Pul, Rep):
    fail = True
    while fail==True:
        fail = False
        try:
            conn = pymysql.connect(host='192.168.0.200',
                                   user='Spike',
                                   password='spatczek',
                                   db='Domz',
                                   charset='utf8mb4',
                                   cursorclass=pymysql.cursors.DictCursor)
            with conn.cursor() as curs:
                req = "SELECT id FROM Radio WHERE value = %s"
                curs.execute(req, (Val,))
                res = curs.fetchone()
                if res == None:
                    req = "INSERT INTO Radio (value, pulselength, protocol, repeat_transmit) " \
                          "VALUES(%s,%s,%s,%s)"
                    curs.execute(req, (Val, Pul, Rep, DefaultRepeat))
                    conn.commit()
                    print("nouveau signal ajouté")
                else:
                    print("ce signal est déjà connu")
        except:
            print("erreur d'insert nouveau signal")
            print(getError(sys.exc_info()))
            fail = True
        finally:
            conn.close

class WaitTime(Thread):

    """Thread chargé de lire les données de l'arduino et créer le nouveau signal dans la base SQL si l'arduino en recoit un nouveau."""

    def __init__(self, wait_time, id):
        Thread.__init__(self)
        self.wait_time = wait_time
        self.myId = id
        self.running = False


    def run(self):
        """Code à exécuter pendant l'exécution du thread."""
        self.running = True
        time.sleep(self.wait_time)
        if self.running:
            fail = True
            while fail==True:
                fail = False
                try:
                    conn = pymysql.connect(host='192.168.0.200',
                                           user='Spike',
                                           password='spatczek',
                                           db='Domz',
                                           charset='utf8mb4',
                                           cursorclass=pymysql.cursors.DictCursor)
                    with conn.cursor() as curs:
                        req = "SELECT * FROM Radio WHERE id = %s"
                        curs.execute(req, (self.myId,))
                        res = curs.fetchone()
                        if res is not None:
                            if res['cancel_time'] != 1:
                                req = "UPDATE Radio SET todo = 1 WHERE id = %s"
                                curs.execute(req, (self.myId,))
                                conn.commit()
                                print("time_wait finished")
                            # else:
                            #     req = "UPDATE Radio SET cancel_wait = 0 WHERE id = %s"
                            #     curs.execute(req, (self.myId,))
                            #     conn.commit()
                            #     print("time_wait cancelled")
                        else:
                            print("impossible de retrouver l'id")
                except:
                    print("erreur dans thread")
                    print(getError(sys.exc_info()))
                    fail = True
                finally:
                    conn.close

    def stop(self):
        self.running = False

class ReadArduino(Thread):

    """Thread chargé de lire les données de l'arduino et créer le nouveau signal dans la base SQL si l'arduino en recoit un nouveau."""

    def __init__(self, SERIAL, Glob):
        Thread.__init__(self)
        self.Serial = SERIAL
        self.Glob = Glob


    def run(self):
        """Code à exécuter pendant l'exécution du thread."""
        while 1:
            try:
                SR = str(self.Serial.readline())
                print(SR)
            except:
                print('erreur de lecture')

            try:
                if re.match(expression, SR):
                    print("commande trouvée")
                    tmpValue = int(re.sub(expression, r"\1", SR))
                    tmpPulse = int(re.sub(expression, r"\2", SR))
                    tmpRepeat = int(re.sub(expression, r"\3", SR))
                    writeInDomz(tmpValue,tmpPulse,tmpRepeat)
                #else:
                    #print(expression)
            except:
                print("erreur Regex")

            # try:
            #
            #     #if '{"' in SR and '"}' in SR:

            #     if re.match(expression, SR):
            #         print("commande trouvée")
            #         #self.Glob['DataReceived'] = SR
            #         Globalz['DataReceived'] = SR
            #
            # except:
            #     print("erreur sur Glob")

def DecToBin24(n):
    tmp = bin(n)[2:]
    while len(tmp) <24:
        tmp = '0' + tmp
    return tmp

ser = serial.Serial('COM9', 9600)

time.sleep(4)

MyThread = ReadArduino(ser, Globalz)
MyThread.start()

print("I'm Ready!")

# connection = pymysql.connect(host='192.168.0.200',
#                              user='Spike',
#                              password='spatczek',
#                              db='Domz',
#                              charset='utf8mb4',
#                              cursorclass=pymysql.cursors.DictCursor)
while 1:
    # fail = True
    # while fail==True:
    #     fail = False
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
                #
                # if row['wait_time'] == 0:
                #     try:
                #         toWriteCode = DecToBin24(row['value'])  # 4527420  4527411
                #         toWritePulse = str(row['pulselength'])
                #         # "function_name": "SendRadioCode",
                #         toWrite = '{"Value":"' + toWriteCode + '","PulseLength":"' + toWritePulse + '"}'
                #         # while toWrite not in Globalz['DataReceived']:
                #         #     ser.write(toWrite.encode('utf-8'))
                #         #     time.sleep(0.5)
                #         ser.write(toWrite.encode('utf-8'))
                #         # Globalz['DataReceived'] = ''
                #     except TypeError as errorrecup:
                #         print('erreur d\'ecriture :', errorrecup)
                #     except:
                #         print('erreur d\'ecriture')
                # else:
                #     print("timer on id = {0}".format(row['id']))
                #     tmpT = WaitTime(row['wait_time'], row['id'])
                #     AllThreads.append(tmpT)
                #     tmpT.start()
                # try:
                #     sql = "UPDATE Radio SET todo = 0, wait_time = 0 WHERE id = %s"
                #     cursor.execute(sql, (row['id'],))
                #     connection.commit()
                # except:
                #     print("erreur d'update")
                #     # time.sleep(2)
    except:
        print("erreur d'update de cancel")
        print(getError(sys.exc_info()))
        fail = True
    finally:
        connection.close

print("fin du while... reste a comprendre pourquoi")
# try:
#     #ser.write(b'4527411') 185
#     #ser.write(b'F0FF0FFF0110') #off 185
#     #ser.write(b'F0FF0FFF0101') #on 185
#     #ser.write(b'010001010001010100110011') # equivalent a 4527411 (on) 185
#                #'010001001110111000100011'
#     #ser.write(b'010001010001010100111100') #equivalent a 4527420 (off) 185
#     #ser.write(b'1119509') #celui la marche bordel!!!! 310
#
#     toWriteCode = DecToBin24(4527411) #4527420  4527411
#     toWritePulse = '185'
#
#
#
#     toWrite = '{"function_name":"SendRadioCode","Value":"' + toWriteCode + '","PulseLength":"' + toWritePulse + '"}'
#     BinaryWrite = toWrite.encode('utf-8')
#     #ser.write(BinaryWrite)
# except TypeError as errorrecup:
#     print('erreur d\'ecriture :', errorrecup)
# except:
#     print('erreur d\'ecriture')
#
# #print("Ready")
# while 1:
#
#
#
#     try:
#         SR = ser.readline()
#         print(SR)
#     except:
#         print('erreur de lecture')
#
# # time.sleep(2)





