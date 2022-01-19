from collections import deque
import time
import hkdf
import os, binascii
import hmac, hashlib

global epoch_time, window_size

def decodePrint(list):
    decoded_list = []
    for l in list:
        decoded_list.append(binascii.hexlify(l).decode())
    print(f"Decoded List: \n{decoded_list}")

def getTracingKey():
    tk = os.urandom(32)  # 256-bit random key
    return tk

#create 16bytes key per day
def getDailyTK(tk):
    global epoch_time
    epoch_time = time.time()
    dayNumber = str(int(epoch_time / (60 * 60 * 24)))
    info = "CT-DTK" + dayNumber
    dailyTk = hkdf.HKDF(tk,None,info,16)
    return dailyTk

#check contacted people every 10mins. Each window means 10mins
# it will be used for getRollingProximityID and later again for compare corona confirmed one's diagnosis key with myDB
def createWindows(window_size = 10):
    windows = []
    numofWindows = 24*60//window_size
    for i in range(numofWindows):
        windows.append('w'+str(i))
    return windows

# it will automatically give you RPID with current time's window
def getRollingProximityID(dailyTk):
    window_size = 5
    now = time.time()
    TIN = str(now - epoch_time / 60 * window_size)
    info = "CT-RPI" + TIN
    # convert str to bytes for input of HMAC
    dailyTk = bytes(dailyTk, 'utf-8')
    info = bytes(info, 'utf-8')

    RPI = hmac.new(dailyTk,info,hashlib.sha256).digest()[:16]
    return RPI

def checkIn2WeeksandAdd(deq,val):

    # if condition :
        # deq need to remove old data more than 14days
        # avoid saving the same val twice
    if len(deq)>=14 and val not in deq:
        print(f'Current deq size is {len(deq)}. it alreay contain 14days data. I will delete the oldest one')
        deq.popleft()
        print(f'I removed the oldest data,so current deq size is {len(deq)}. I successfully update the latest data')

    deq.append(val)


# idx : idx of Contacted Person
def contactWithSbd(idx , contactSbdToday):
    '''
       Situation : My point of view
       I receive person3's tk who is near me and took more then 5min together.
       (Let's premise that my info is automatically sent to p3 in the same way I received)
    '''

    # contacted person's RPID
    RPID = getRollingProximityID(DB[idx]['dailyTk'])
    print("Meet person" + str(idx) + "! \n Now created RPID :", binascii.hexlify(RPID).decode())
    '''
    save to each db
        1. save contacted person's RPID to dailyContact
        2. change contactSbdToday to True
        3. add dailyTK to diagnosisKey(14days)
        4. saved today's dailyContact to my exposure(14days)
        5. reset dailyTk,dailyContact,contactSbdToday everyday
    '''
    # 1. save contacted person's RPID to myDB
    # 2. if I contacted sbd today then it changed to True
    if contactSbdToday == False:
        # 3. add dailyTK to diagnosisKey(14days)
        contactSbdToday = True
        checkIn2WeeksandAdd(diagnosisKey,DB[0]['dailyTk'])

    if RPID not in dailyContact:
        dailyContact.append(RPID)
        # print(f'add RPID to dailyContact : {dailyContact}')

    return contactSbdToday


def resetDailyDB(dailyContact,contactSbdToday):
    # 4.saved today's dailyContact to my exposure(14days)
    if contactSbdToday:
        checkIn2WeeksandAdd(exposure, dailyContact)
    # if I don't meet anybody today then add 0 to exposure and diagnosisKey for avoiding error
    else:
        checkIn2WeeksandAdd(exposure, 0)
        checkIn2WeeksandAdd(diagnosisKey, 0)


    # 5.reset dailyTk, dailyContact, contactSbdToday everyday
    for i in range(11):
        DB[i]['dailyTk'] = getDailyTK(DB[i]['tk'])

    contactSbdToday = False
    dailyContact = []

    print(f'reset all daily info and renew them!')
    return dailyContact, contactSbdToday

def compareToExposure(confirmed,exposure):
    totalDiagnosisKeys = []
    windows = createWindows()

    # combine windows with dailykey so I can compare to exposure
    for dailykey in confirmed:
        for window in windows :
            totalDiagnosisKeys.append(dailykey+"-"+window)

    # For convenince, add all exposure elements to temp and make exposure simple one-dimensional flat list.
    exposure_flat_list = []
    for sublist in exposure:
        if type(sublist)!= int:
            for item in sublist:
                exposure_flat_list.append(item)
    decodePrint(exposure_flat_list)

    # now compare totalDiagnosisKeys to my exposure data
    for dk in totalDiagnosisKeys:
        if dk in exposure_flat_list:
            print("\n WARN : You contacted with confirmed person!!!!! You should go to get a corona test!!!")
            break



if __name__ == '__main__':
    global DB, dailyContact, contactSbdToday, exposure, diagnosisKey
    # DB for all (for convenience)
    DB = [{'tk': '', 'dailyTk': '' } for i in range(11)]
    # save contacted people today
    dailyContact = []
    # whether I met someone today -> if yes, add my dailyTk to diagnosisKey
    contactSbdToday = False
    # this exposure is the everyday list of contacted people. Each idx contains one-day contacted people list
    exposure = deque()
    # this diagnosisKey is my data for sending to server when I got corona
    diagnosisKey = deque()

    # create tk and dailytk and save to pks and DB
    for i in range(11):
        tk = getTracingKey()
        DB[i]['tk'] = tk
        DB[i]['dailyTk'] = getDailyTK(tk)

    #print(DB)


    '''
    Situation : My point of view
    I receive RollingProximityID of person who was near me and took more then 5min together.
    P4 got confirmed corona and P4 met somebody on day2,5,9,13,15 so diagnosisKey will contain these days' P4's dailyTK
    
    Day1. meet p1,p3
    Day2. meet no one
    Day3. meet p6
    Day4. meet no one
    Day5. meet no one
    Day6. meet p7,p9,p2
    Day7. meet no one
    Day8. meet no one
    Day9. meet p5
    Day10. meet p8
    Day11. meet no one 
    Day12. meet no one
    Day13. meet no one
    Day14. meet p1,p10
    Day15. meet p3,p4, 
        -> show that after 14days, it will delete the first day's data and add new 15th day's data
        -> got notified that p4 is confirmed -> with dianosisKey of p4, I will compare with my exposure
    
    When we contact sdb, save/change to each db
        1. save contacted person's RPID to dailyContact
        2. change contactSbdToday to True
        3. add dailyTK to diagnosisKey(14days)
        4. saved today's dailyContact to my exposure(14days)
        5. reset dailyTk,dailyContact,contactSbdToday everyday
    '''
    p4DiagnosisKey = []

    #Day1. meet p1,p3
    print('----------------------------Day1----------------------------------')
    contactSbdToday = contactWithSbd(1,contactSbdToday)
    contactSbdToday = contactWithSbd(3,contactSbdToday)
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    '''
    when we premise that one day passed(we can use Timer)
    Then, we need to 
        -renew dailyTk
        -reset dailyContact = [], contactSbdToday = False
    '''
    #Day2. meet no one
    print('----------------------------Day2----------------------------------')
    checkIn2WeeksandAdd(p4DiagnosisKey, DB[4]['dailyTk'])
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day3. meet p6
    print('----------------------------Day3----------------------------------')
    contactSbdToday = contactWithSbd(6,contactSbdToday)
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day4. meet no one
    print('----------------------------Day4----------------------------------')
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day5. meet no one
    print('----------------------------Day5----------------------------------')
    checkIn2WeeksandAdd(p4DiagnosisKey, DB[4]['dailyTk'])
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day6. meet p7,p9,p2
    print('----------------------------Day6----------------------------------')
    contactSbdToday = contactWithSbd(7,contactSbdToday)
    contactSbdToday = contactWithSbd(9,contactSbdToday)
    contactSbdToday = contactWithSbd(2,contactSbdToday)
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day7. meet no one
    print('----------------------------Day7----------------------------------')
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day8. meet no one
    print('----------------------------Day8----------------------------------')
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day9. meet p5
    print('----------------------------Day9----------------------------------')
    contactSbdToday = contactWithSbd(5,contactSbdToday)
    checkIn2WeeksandAdd(p4DiagnosisKey, DB[4]['dailyTk'])
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day10. meet p8
    print('----------------------------Day10---------------------------------')
    contactSbdToday = contactWithSbd(8,contactSbdToday)
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day11. meet no one
    print('----------------------------Day11---------------------------------')
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day12. meet no one
    print('----------------------------Day12---------------------------------')
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day13. meet no one
    print('----------------------------Day13---------------------------------')
    checkIn2WeeksandAdd(p4DiagnosisKey, DB[4]['dailyTk'])
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day14. meet p1,p10
    print('----------------------------Day14---------------------------------')
    contactSbdToday = contactWithSbd(1,contactSbdToday)
    contactSbdToday = contactWithSbd(10,contactSbdToday)
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    print('------------------------------------------------------------------')
    #Day15. meet p3,p4,
    print('----------------------------Day15---------------------------------')
    # -> show that after 14days, it will delete the first day's data and add new 15th day's data
    contactSbdToday = contactWithSbd(3,contactSbdToday)
    contactSbdToday = contactWithSbd(4,contactSbdToday)
    checkIn2WeeksandAdd(p4DiagnosisKey, DB[4]['dailyTk'])
    print(f"Did I add diagnosisKey successfully to the latest position after remove the oldest data? {DB[0]['dailyTk']==diagnosisKey[13]}")
    dailyContact, contactSbdToday = resetDailyDB(dailyContact,contactSbdToday)
    # -> got notified that p4 is confirmed -> with dianosisKey of p4, I will compare with my exposure
    confirmed = p4DiagnosisKey
    compareToExposure(confirmed, exposure)
    print('------------------------------------------------------------------')



