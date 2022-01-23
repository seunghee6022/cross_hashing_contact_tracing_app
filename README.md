# cross_hashing_contact_tracing_app
Vaccination side effect check &amp; Self quarantine application - Applied cross hashing and k-anonymity method to Google-Apple contact tracing algorithm and built a basic version exchanging RPID via Bluetooth Low Energy technology.

---

### Algorithm

---

#### 1. HDKF hash function

---

**HKDF** is a simple key derivation function (KDF) based on HMAC message authentication code. 

It is used for generate Daily Tracing Key, Consistent Contact Identifier(CCI)

The main approach HKDF follows : "extract-then-expand" paradigm

* `hkdf_extract`
* `hkdf_expand`

>  Where the KDF logically consists of two modules: the first stage takes the input keying material and "extracts" from it a fixed-length pseudorandom key, and then the second stage "expands" this key into several additional pseudorandom keys (the output of the KDF).

---

#### 2. Contact Tracing Algorithm 

---

`contactTracingAlgorithm.py`  

IT contains a contact tracing algorithm. The algorithms of the main function of the contact tracing exposure notification are implemented with simulation example which is manually set. Algorithms are consisted of 3 big parts. First, Generating major encrypted keys i.e. Tracing Key, Daily Tracing Key, Rolling Proximity Identifier(RPID) , Diagnosis Key,  Secondly, broadcasting the RPID and saving shared RPID to my device.
Finally, matching received Diagnosis Key of infected person and getting notification if I contacted with infected one.

1. Generating major cryptographic keys

   > Each functions respectively generates Tracing Key, Daily Tracking Key and Rolling Proximity Identifier followed by official Cryptography Specification of Google-Apple.
   >
   > * Exposure Notification - Cryptography Specification
   >
   >   https://covid19-static.cdn-apple.com/applications/covid19/current/static/contact-tracing/pdf/ExposureNotification-CryptographySpecificationv1.2.pdf?1 
   >
   > * Contact Tracing - Cryptography Specification
   >
   >   https://blog.google/documents/56/Contact_Tracing_-_Cryptography_Specification.pdf/

   * getTracingKey()
   * getDailyTK(tk)
   * getRollingProximityID(dailyTK)

2. Broadcasting the RPID and saving shared RPID to my device

   * contactWithSbd(idx, contactSbdToday)

     > If user have close contact with somebody then it register the broadcased RPID and save the RPI to my device

   * checkIn2WeekandAdd(deq,val)

     > When we register contacted person's RPID(`val`), it delete the old RPID which is longer then 2 weeks and then save RPID to the device. For convenience, used `deq` data structure to make delete the old data and add the new data easily.

3. Matching received Diagnosis Key of infected person and getting notification if I contacted with infected one

   * compareToExporuse(confirmed,exposure)

     > When the case of infection occurs, this function receives the Diagnosis Key of the infected person (`confirmed`) and based on the Diagnosis Key, which consists of 14 days Daily Tracing Keys, and creates all the possible RPIDs and compares to my registered RPID list in device called `exposure`.

4. Simulation

   Set the simulation for 15days in user's (my) point view. 
   
   And tried to check the situation:
   
   * meet someone -> checked the RPID of contacted people are saved successfully to exposure(which contains all the contacted people's RPIDs for 2 weeks)
   * If the infection occurs so I get a Diagnosis Key, and the infected person is one of the contacted people in 2 weeks -> checked I get risk notification successfully
   
   ```
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
   ```
   
   You can see the printed result by running `contactTracingAlgorithm.py`

---

#### 3. Cross Hashing

---

 `crossHasingApp.py`

We applied cross hashing method to the previous contact tracing algorithm. And additioally, added k-anonymity method when we save the encrypted key called CCI. For implementing the cross hashing function, we reused the major key generator algorithms because we use the same Tracing Key, Daily Tracing Key, Rolling Proximity Identifier(RPID) for generating CCI. 

In this `crossHasingApp.py`, we implemented the new application which has two main functions, first one is for checking Vaccine Adverse Reactions in 15 minutes after we got vaccine. The other one is for self-quarantine.

Finally, we set fixed situation which contains all the possibilities during the vaccine adverse reactions check time(15mins) and self-quarantine. And manually simulated the situation for checking the implemented algorithms work successfully.

1. Generating the Consistent Contact Identifier(CCI) 

   * getCCIs(historyRPIs, currentRPIs)

     > CCI is generated by `current RPID` and one of the last RPID saved in `historic RPID` list. Therefore, we reused the key generator functions those are implemented for the contact tracing algorithm to generate RPID. It is implemented by the pseudo algorithm in the cross hashing paper.
     >
     > * cross hashing paper 
     >
     >   https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=9333939

2. Observation after Vaccinated Application

   * vaccineSideEffectCheck(waiting_time,dailyTk)

     > Basic Idea of vaccineSideEffectCheck function is that if we give a `waiting_time` for observing the vaccine post-vaccine symptoms, side effect or other reactions and the person's `dailyTk`. With generated the CCIs every 5 minutes, the server can check the person is waiting properly(in a series). It check the latest CCI is saved in the server and also the CCIs are saved in series. 
     >
     > If CCIs are not saved in series means that the waiting person leaves the place while waiting. Then the person will saved to the run_away list and report to the server.
     >
     > When it counts the number of registered CCI of the users depending on the wating time and when the number of counted CCIs are `waiting_time/5+1`, it approves the person's waiting time is over. Otherwise, it alert user about leaving the waiting place and informs the waiting end time to user.

3. Self-Quarantine Application

   * self_quarantine(dailyTk)

     > It records all the `body conditions` and close contact(`recordedCCIs`) during the self-quarantine period including `penalty` .
     >
     > This system has one feature that if the person(user) who in a self-quarantine contact with someone, the penalty is given to the person and the total self-quarantine period extends as followed the number of penalty. Because if the day when the person meets somebody doesn't count as self-quarantine period.

   * get_user_input_from_device(dailyTk)

     > It brings user's body condition every once per day.
     >
     > It checks temperature for fever, tiredness, cough, loss of taste and loss of smell of the user.
     >
     > ```
     > body_condition = {'temperature':36.5,'tiredness':False, 'cough':False,'loss_of_taste':False,'loss_of_smell':False}
     > ```

   * get_user_storeCCIs_from_device(dailyTk)

     > It brings user's currently stored CCIs on the day.

   * report_to_server(body_conditions, recordedCCIs, brief_check)

     > If some issue in body condition or contacted record is observed, device report this data(`body_conditions`,`recordedCCIs`,`brief_check`) to the server.
     >
     > `brief_check` takes a role like simple flag of body condition and contacted record in order to quickly check which one has a issue
     >
     > ```
     > brief_check = {'body_condition': False, 'CCI': False}
     > ```

   * check_symptoms_contact(start_date, end_date)

     > * check body condition every once per day `get_user_input_from_device(dailyTk)`
     > * check close contact every hour by checking the number of stored CCI``get_user_storeCCIs_from_device(dailyTk)`. If stored CCI exists user will get penalty.
     > * If some issue in body condition or contacted record is observed, device report this data to the server `report_to_server(body_conditions, recordedCCIs, brief_check)`
     > * This function will return start_date, end_date, penalty. If the penalty exist, this function will be automatically called with new calculted start_date and end_date which automatically designed by continuing the extended self-quarantine day count. -> you will see in simulation. 

     

4. Simulation

   We made a manual simulation by adding some situations to check each function works well.

   This simulation will shows the situation of total 17 days of self-quarantine.

   * First call(1st~14th day) : check_symptoms_contact(start_date, end_date)

     For first 14 days, user will have two days with close contact therefore get penalty =2 which extends the 2 more days of self-quarantine period.

   *  Second call because of 2 penaltys(15th~16th day) - check_symptoms_contact(start_date, end_date)

   * Third call because of 1 penalty(17th day) - since user got no penalty, self-quarantine is over. 

   

   * Body condition situations we added:

     > Body condition issue won't increase penalty however it will be reported to the server.

     ```
     # test - manually add body condition issue
     if day == 3:
         body_condition['temperature'] = 38
     
     if day == 6:
         body_condition['tiredness'] = True
     
     if day == 15 :
         body_condition['loss_of_smell'] = True
     ```

   * Close contact situations we added: 

     > If user have a close contact(which means CCI exists), user will get msg that when user have a contact and this fact will increase penalty regardless of the number of contact per day. Penalty only counts once per day. -> the day 10 will show this situation well.
     >
     > And it will be reported to the server.
     >
     > The day 15 means it is already over the 14 days because we made a situation that user had a close contact and got a penalty therefore it extended the total period of self-quarantine.

     ```
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
     ```

   

---

### Bluetooth Low Energy

---
   `Bluetooth_Low_Energy`

It's a basic version showing how to transfer Rolling Proximity Identifiers (RPID) using Bluetooth Low Energy. We get the reference from the Apple Developer (https://developer.apple.com/documentation/corebluetooth/transferring_data_between_bluetooth_low_energy_devices).

   1. Download the folder and open it with Xcode 11.1+.
   2. From Xcode, go to Sgning & Capabilities. Please sign in with your Apple Development Team account. 
   3. Please prepare two Apple devices with availablility of iOS 12.0+/iPadOS 12.0+.
   4. Get two cables with each connect a device to the laptop. 
   5. Select your device as the Build simulator from Xcode and run the project (Do this step for both devices one by one.)
   6. On your each device, go to Setting > General > VPN & Device Management > Developer App. Click on the application and make it trusted. 
   7. Open the application on both of your devices, and make one as the central and the other as the pheripheral. You should be able to see how it works now :)

   

---

### New Application

---

We built the application interface using Figma. 
Here is the link: https://www.figma.com/file/m2KAm3DHK7Ka3P7m8h5KMV/Contact-Tracing?node-id=148%3A1231. 



