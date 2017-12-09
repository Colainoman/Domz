import sys
from threading import Thread
import re
import time
import pymysql


expression = r"""^b'{"action":"received","value":(\d*?),"PulseLength":(\d*?),"Protocol":(\d*?)}\\r\\n'$"""
DefaultRepeat = 15

def getError(theError):
    erreur = sys.exc_info()
    typerr = u"%s" % (theError[0])
    typerr = typerr[typerr.find("'")+1:typerr.rfind("'")]
    msgerr = u"%s" % (theError[1])
    return typerr[typerr.find(".")+1:] + ": " + msgerr

class ReadArduino(Thread):

    """Thread chargé de lire les données de l'arduino et créer le nouveau signal dans la base SQL si l'arduino en recoit un nouveau."""

    def __init__(self, SERIAL):
        Thread.__init__(self)
        self.Serial = SERIAL

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

def WriteHistory(connect,):


def DecToBin24(n):
    tmp = bin(n)[2:]
    while len(tmp) <24:
        tmp = '0' + tmp
    return tmp

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