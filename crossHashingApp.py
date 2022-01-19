import hkdf as hkdf
import contactTracingAlgorithm as ct

# history RPIs , Current RPIs
import time, datetime
import hkdf
import os, math
import hmac, hashlib, binascii
global epoch_time, window_size, serverDB

def getTracingKey():
    tk = os.urandom(32)  # 256-bit random key
    return tk

# create 16 bytes key per day
# NOTE : epoch_time is commented for the test. It is supposed not to be commented in real application.
def getDailyTK(tk):
    global epoch_time
    # for the manual test, this line below is commented.
    # epoch_time = math.trunc(time.time())
    dayNumber = str(int(epoch_time / (60 * 60 * 24)))
    info = "CT-DTK" + dayNumber
    dailyTk = hkdf.HKDF(tk,None,info,16)
    return dailyTk

# it will automatically give you RPID with current time's window
def getRollingProximityID(dailyTk,TIN=None,now=None):
    if now is None:
        now = math.trunc(time.time())
    if TIN is None:
        TIN = str(math.floor((now - epoch_time) / (60 * window_size)))
    else:
        TIN = str(TIN)
    # convert str to bytes for input of HMAC
    info = bytes("CT-RPI" + TIN, 'utf-8')
    dailyTk = bytes(dailyTk, 'utf-8')

    RPI = hmac.new(dailyTk,info,hashlib.sha256).digest()[:16]
    return RPI

# create dailyRPIs depending on the window_size.
# window size 10 -> 144, 5 -> 288
def getDailyRPIs(dailyTk,window_size):
    DailyRPIs = []
    for i in range(int(60*24/window_size)):
        RPI = getRollingProximityID(dailyTk=dailyTk,TIN=i)
        DailyRPIs.append(RPI)
    print("The len of DailyRPIs is :",len(DailyRPIs))
    return DailyRPIs


# create CCI
def getCCIs(historyRPIs, currentRPIs):
    def explode(string, size):
        chunks = len(string)
        return [string[i:i + size] for i in range(0, chunks, size)]

    storeCCIS = []

    for RPI in currentRPIs:
        for lastRPI in historyRPIs:
            print(RPI[0:2]==lastRPI[0:2])
            CCI = hkdf.HKDF(RPI[0:12],lastRPI[0:12])[0:9] #k-anonymity
            # storeCCIS.append(CCI)
            signitures = explode(lastRPI[12:16],2)
            if RPI[0:2] in signitures:
                print(f"matched : {RPI[0:2]} in {signitures}")
                storeCCIS.append(CCI)
    if len(storeCCIS)>0:
        print(storeCCIS)
    else:
        print("storeCCIS is empty")
    return storeCCIS

def decodePrint(list):
    decoded_list = []
    for l in list:
        decoded_list.append(binascii.hexlify(l).decode())
    print(f"Decoded List: \n{decoded_list}")

# if broadcast 4th RPIs in a row, then send msg
def vaccineSideEffectCheck(waiting_time,dailyTk):
    run_away = []
    def TIN_check(now=None):
        if now is None:
            now = math.trunc(time.time())
        TIN = str(math.floor((now - epoch_time) / (60 * window_size)))
        return TIN

    check_flag = True
    start_time = datetime.datetime.now()
    finish_time = start_time + datetime.timedelta(minutes=waiting_time)
    # Every 5 mins check the person's RPI is saved to the serverDB
    def checkRPI(TIN, dailyTk):
        global check_flag
        RPI = getRollingProximityID(dailyTk,TIN=TIN)
        if RPI not in serverDB:
            check_flag = False
            run_away.append(dailyTk)
        return check_flag
    # check every 5 minutes
    interval = waiting_time/5
    for i in range(interval,0,-1):
        TIN = TIN_check()
        check_flag = checkRPI(TIN, dailyTk)
        if check_flag:
            if i>0:
                print(f"Waiting time {5*i}minutes left")
            else:
                print("Wating time is over. Please do the simple symptom check")
                check_flag = False
                break
        else:
            print(f"Your waiting finishs at {finish_time.strftime('%H:%M:%S')}")
            break
        # wait 5 minutes -> use sleep?
        if check_flag:
            time.sleep(60*5)

# self- quarantine
def self_quarantine(dailyTk):
    print("SELF QUARANTIME STARTS")
    # save contacted records as CCIs for the self-quarantine period
    recordedCCIs = []
    # save body conditoins for the self-quarantine period
    body_conditions = []

    def get_user_input_from_device(dailyTk):
        body_condition = {'temperature':36.5,'tiredness':False, 'cough':False,'loss_of_taste':False,'loss_of_smell':False}
        return body_condition

    def get_user_storeCCIs_from_device(dailyTk):
        storeCCIs = []
        return storeCCIs

    # if there's problem, send the data to the server
    def report_to_server(body_conditions, recordedCCIs ,brief_check):
        if brief_check['body_condition'] and brief_check['CCI']:
            print("REPORT : body condition issue & contacted record issue")
        elif brief_check['body_condition']:
            print("REPORT : body condition issue")
        else:
            print("REPORT : contacted record issue")

        # print(f"Sending....\nbody_conditions :\n{body_conditions}\n and\nrecordedCCIs :\n{recordedCCIs}\nto the server... ")
        # print("Successfully sent")

    def check_symtoms_contact(start_date, end_date):
        # penalty
        penalty = 0
        start_date = start_date
        end_date = end_date

        cur_CCI_count = 0

        for day in range(start_date,end_date+1):
            print("------------------------------------------------------------------")
            print(f"Self quarantine day count : D+{day}")
            print("------------------------------------------------------------------")

            body_condition = get_user_input_from_device(dailyTk)

            # briefly check whether there's problem at body condition or CCI(met sbd)
            brief_check = {'body_condition': False, 'CCI': False}

            # test - manually add body condition issue
            if day == 3:
                body_condition['temperature'] = 38

            if day == 6:
                body_condition['tiredness'] = True

            if day == 15 :
                body_condition['loss_of_smell'] = True

            # Save data to storage for sending this data for the future when some problem happens
            body_conditions.append(body_condition)

            temperature = body_condition['temperature']
            tiredness = body_condition['tiredness']
            cough = body_condition['cough']
            loss_of_taste = body_condition['loss_of_taste']
            loss_of_smell = body_condition['loss_of_smell']

            # checking the corona symptoms and temperature
            if temperature >= 37.5 or tiredness or cough or loss_of_taste or loss_of_smell:
                # send storeCCIs to the serverDB and send warning msg to the user
                print("USER MSG : detail body condition check is needed")
                brief_check["body_condition"] = True

            # check contacted sbd every hour
            for hour in range(24):
                storeCCIs = get_user_storeCCIs_from_device(dailyTk)

                #test - manually add the CCIs
                if day == 6 and hour == 18:  # to check if the CCIs store successfully
                    storeCCIs = ['testday6_CCI']

                if day == 10:
                    if hour == 16:
                        storeCCIs = ['testday10_CCI', 'testday10_CCI2']
                    elif hour == 17 : # assume that due to the contacted more people, 2 more CCIs are added to storeCCIs
                        storeCCIs = ['testday10_CCI', 'testday10_CCI2','testday10_CCI3','testday10_CCI4']

                if day == 15 and hour==9:
                    storeCCIs = ['testday15_CCI', 'testday15_CCI2']

                # check it contact with somebody -> if I contacted more people then len(storeCCIs) will longer than before
                if len(storeCCIs) > cur_CCI_count:
                    print(f"ALERT : you contacted with someone at around {hour}~{hour+1}")
                    cur_CCI_count = len(storeCCIs)
                    if brief_check["CCI"] == False:
                        brief_check["CCI"] = True
                        recordedCCIs.append(storeCCIs)
                    else:
                        recordedCCIs[-1] = storeCCIs

            # check it there's any problem at body condition or storeCCIs
            if True in brief_check.values():
                report_to_server(body_conditions, recordedCCIs ,brief_check)

            if brief_check['CCI']:
                penalty+=1
                print("PENALTY : 1 day is added to your self-quarantine period")
            else:
                recordedCCIs.append(0)

        start_date = end_date+1
        end_date = start_date + penalty -1

        return start_date,end_date, penalty

    start_date = 1
    end_date = 14
    penalty = -999
    while penalty:
        start_date, end_date, penalty = check_symtoms_contact(start_date,end_date)

        print(f"TOTAL PENALTY COUNT : {penalty}")

    print("INFO : Your self-quarantine is over. Thank you for your patient and cooperation!")

if __name__ == '__main__':
    # assume 3 people including me
    names = ["A","B","Me"]
    window_size = 5
    # manual test - Entering the cafe : 2021_01_14_15_00
    epoch_time = 1642172400
    # each key size = 32
    tks = {}
    dailytks = {}

    for name in names:
        tks[name] = getTracingKey()
        dailytks[name] = getDailyTK(tks[name])

    # create today's RPIs
    Me_daily_RPIs = getDailyRPIs(dailytks["Me"],window_size)

    # Self-quarantine mode
    self_quarantine(dailytks['Me'])
    '''
    I entered cafe at 15:00:00
    A 
    - A was already in the cafe when I entered  
    B 
    - B entered cafe at 15:18:xx ( B and I stayed together for 18 mins )
    
    Current time is 15:31:xx
    In my historyRPIs = [ An-6,An-5,An-4,An-3,Bn-3,An-2,Bn-2,An-1,Bn-1] -> A-00,05,10,15,20,25(6개) B-15,20,25
    In my currentRPIs = [ An, Bn]
    
    '''
    k = 6 # 5*6 = 30 min range
    times = []
    for i in range(k+1):
        times.append(epoch_time+60*window_size*i) #60*window_size

    historyRPIs = []
    currentRPIs = []
    A_RPIs = [b'\xf0\x10\x9f\xce[\x97\xde\x0eF\xb1$\xde\xf1*\xeb\n', b'\xc0\xe5y\xf9)\xbc\x17\xcb1m\xedD\xa3Q\xf5e',
              b'\xd2P\x91\xc4\xf9ZA\xb5\x91=\x96X\x02\x82K\xc3', b'Kda\xfb\xfb\xc0\xd3\xb56j\xbb\x8a\xedN\xf5\x11',
              b'\xbc%\xb6y/\x90\xe4\xb9\x8a(\xb0\x08\xa5P\xd5\xd7', b'\xdc\xbd\xd2j\xa1yFl$\xe9\x8bV\xd9\xb1\xae\x98',
              b'l\xbe\xf5\xadg5\x87\xa9\xdf\xaa\\\x95\xea\xe8^\xd1']
    B_RPIs = [b'6\xdc\x11]\x93\x155\xd4sU9\xa1j,Q7', b'\xd7Q\xd0\x04\x9d\x0f^\x07\x0b@V?\xa7A\x90\xba',
              b'P\xc4\xc7\x86\x17\xbc_Q\x1f\xcf?\xb4i\xb4\x13/']
    Me_RPIs = [b"\x1b1\x04WL\xab'~\xb3\xe4\xeb\xe0\x1c\xc2\x13p", b'$\xa0u%\xc9\ts4\xe5xs\x1c\x99p\xf2\x99',
               b'x(\xfa\x0e\xa0)\xbe\x88 \xfcL\xed\x94D\x1aw', b'XV"\xcbe\xa9\xc9\x8c\xc2\xd6\xb1\x99\x88\xb6k\x1d',
               b')\xfa\xf3\x08F\xd9H\xd8i>\x13-\x9c\xf5\x0b\x8d', b'c\xb15\xcaW\xa9\xb9\x8bH\x02\xb4(\xf4\xa3\xe1p',
               b'g\xc05\xdb!\xfb\x99\x8f\xb7\xa4`\xf2|\xf3\x0f\xe3']
    historyRPIs = [b'\xf0\x10\x9f\xce[\x97\xde\x0eF\xb1$\xde\xf1*\xeb\n',
                   b'\xc0\xe5y\xf9)\xbc\x17\xcb1m\xedD\xa3Q\xf5e', b'\xd2P\x91\xc4\xf9ZA\xb5\x91=\x96X\x02\x82K\xc3',
                   b'Kda\xfb\xfb\xc0\xd3\xb56j\xbb\x8a\xedN\xf5\x11',
                   b'\xbc%\xb6y/\x90\xe4\xb9\x8a(\xb0\x08\xa5P\xd5\xd7',
                   b'\xdc\xbd\xd2j\xa1yFl$\xe9\x8bV\xd9\xb1\xae\x98', b'6\xdc\x11]\x93\x155\xd4sU9\xa1j,Q7',
                   b'\xd7Q\xd0\x04\x9d\x0f^\x07\x0b@V?\xa7A\x90\xba']
    currentRPIs = [b'l\xbe\xf5\xadg5\x87\xa9\xdf\xaa\\\x95\xea\xe8^\xd1',
                   b'P\xc4\xc7\x86\x17\xbc_Q\x1f\xcf?\xb4i\xb4\x13/']

    storeCCIs = getCCIs(historyRPIs, currentRPIs)


    '''
    This is the way to generate tracking key and daily tracking key and Rolling proximity Identifier(RPI)
    
    def saveRPIs(time_range,name):
        RPIs = []
        for t in time_range:
            RPI = getRollingProximityID(dailytks[name],now=t)
            RPIs.append(RPI)
        return RPIs

    A_RPIs = saveRPIs(times,"A")
    B_RPIs = saveRPIs(times[3:6],"B")
    Me_RPIs = saveRPIs(times,"Me")
    # historyRPIs
    historyRPIs.extend(A_RPIs[:len(A_RPIs) - 1])
    historyRPIs.extend(B_RPIs[:len(B_RPIs) - 1])

    # currentRPIs
    currentRPIs.append(A_RPIs[-1])
    currentRPIs.append(B_RPIs[-1])

    '''