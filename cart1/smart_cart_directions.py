
import RPi.GPIO as GPIO
from time import sleep,time
import requests,json

#constants used to estimate the distance covered by the cart.
RPM = 150
PI = 3.14
TYRE_DIAMETER = 6.5 #in cm
NINETY_DEG_TURN_TIME = 0.65 #in seconds
# The cart would cover PI * TYRE_DIAMETER * RPM/60 * t in time t
# So in 1 sec, it would cover PI * TYRE_DIAMETER * RPM/60 
#(substituting we get 34cm ~ is not the ideal value - only theoretical!)
DISTANCE_CM_COVERED_1SEC = 35 #cm

UPDATE_INTERVAL = 0 #in sec.

#OBSTACLE_THRESHOLD = 5
OBSTACLE_THRESHOLD = 10

bayGpsLat = 0;
bayGpsLong = 0;
gpsLat = 0;
gpsLong = 0;
weight = 0;
moving = False;
reverseDirections = []
rDis=[]
rDir=[]
cartId = 1

#ultrasonic pins
GPIO_TRIGGER = 23
GPIO_ECHO    = 24

def setup():
    print("setup happens")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(18,GPIO.OUT)
    GPIO.setup(5,GPIO.OUT)
    GPIO.setup(6,GPIO.OUT)
    GPIO.setup(13,GPIO.OUT)
    GPIO.setup(19,GPIO.OUT)
    # Set pins as output and input
    GPIO.setup(GPIO_TRIGGER,GPIO.OUT)  # Trigger
    GPIO.setup(GPIO_ECHO,GPIO.IN)      # Echo
    # Set trigger to False (Low)
    GPIO.output(GPIO_TRIGGER, False)
    sleep(0.5)
    #GPIO.output(5,GPIO.LOW)
    #GPIO.output(6,GPIO.HIGH)
    print("setup complete")

def loop():
    print("lets loop this one")
    #GPIO.output(18,GPIO.HIGH)
    print("LED is on")
    sleep(1)
    #GPIO.output(18,GPIO.LOW)
    print("LED is Off")
    #forward()

def backward():
    moving = True
    GPIO.output([5,13], GPIO.LOW)
    GPIO.output([6,19], GPIO.HIGH)

def forward():
    moving = True
    GPIO.output([5,13], GPIO.HIGH)
    GPIO.output([6,19], GPIO.LOW)

def moveCartToBayArea():
    while(bayGpsLat>gpsLat and bayGpsLong>gpsLong):
        while(bayGpsLat>gpsLat):
            forward()
        while(bayGpsLong>gpsLong):
            leftMovement()

def leftMovement():
    moving = True
    GPIO.output([5,6,19], GPIO.LOW)
    GPIO.output(13,GPIO.HIGH)

def rightMovement():
    moving = True
    GPIO.output(5,GPIO.HIGH)
    GPIO.output([6,13,19], GPIO.LOW)
    
def stopMovement():
    moving = False
    GPIO.output([5,6,13,19], GPIO.LOW)

def getObstacleDistance():
    try:
        # Send 10us pulse to trigger
        GPIO.output(GPIO_TRIGGER, True)
        sleep(0.00001)
        GPIO.output(GPIO_TRIGGER, False)
        start = time()

        while GPIO.input(GPIO_ECHO)==0:
          start = time()

        while GPIO.input(GPIO_ECHO)==1:
          stop = time()

        # Calculate pulse length
        elapsed = stop-start

        # Distance pulse travelled in that time is time
        # multiplied by the speed of sound (cm/s)
        distance = elapsed * 34300
        print("distance infront is ", distance)
        return(distance)
    except :
        return 0

def getGpsLocation():
    #logic for getting gps from sensor
    gpsLat = 0
    gpsLong = 0

def getCartMovementDirection():
    print("getting data")
    url = "http://139.59.15.209:5000/getDirection/1"
    r =requests.get(url)
    data = json.loads(r.text)
    print("getting data",r.status_code,r.text)
    direction = json.loads(data["data"])
    if(direction == None):
        sleep(4)
        stopMovement()
        return 0
    if(cartId != int(direction["cartID"])):
        return 0
    distance_cm = int(direction["distance"])
    directionTo = direction["direction"]
    rDis.append(distance_cm)
    rDir.append(directionTo)
    reverseDirections.append((directionTo,distance_cm))
    print(reverseDirections)
    return [directionTo, distance_cm]



#Function to move the cart based on the Queued data from the server.

def moveCart(directionTo, distance):    
    while(distance >0):
        if directionTo == "Straight" :
            print("moving",directionTo)
            if(distance == 1):
				distance = 0;
                continue
            obstacleD = getObstacleDistance()
            if obstacleD<OBSTACLE_THRESHOLD:
                #move cart left if any obstacle
                backward()
                sleep(NINETY_DEG_TURN_TIME)
                leftMovement()
                sleep(NINETY_DEG_TURN_TIME)
                forward()
                sleep(2*NINETY_DEG_TURN_TIME)
                rightMovement()
                sleep(NINETY_DEG_TURN_TIME)
                forward()
                sleep(4*NINETY_DEG_TURN_TIME)
                rightMovement()
                sleep(NINETY_DEG_TURN_TIME)
                forward()
                sleep(2*NINETY_DEG_TURN_TIME)
                leftMovement()
                sleep(NINETY_DEG_TURN_TIME)
                distance = distance - 4*NINETY_DEG_TURN_TIME*DISTANCE_CM_COVERED_1SEC
                print("obstacle found at ",obstacleD)
                continue
            forward()
            distance = distance - DISTANCE_CM_COVERED_1SEC;
            sleep(1)
        elif directionTo == "Left":
            print("moving",directionTo)
            leftMovement()
            sleep(NINETY_DEG_TURN_TIME)
            directionTo = "Straight"
        elif directionTo == "Right":
            print("moving",directionTo)
            rightMovement()
            sleep(NINETY_DEG_TURN_TIME)
            directionTo = "Straight"
        elif directionTo == "Stop":
            print("stoping cart movement",directionTo)
            stopMovement()
        elif directionTo == "newCart":
            print("cart is going back now")
            stopMovement()
            reverseCart()
        #sleep(1)

    stopMovement()
    return 0

def getCartBayLocation():
    url = "https://139.59.15.209/getLocation"
    r =requests.get(url)
    bayGpsLat = r.json().gspLat
    bayGpsLong = r.json().gpsLong
    getGpsLocation()
    moveCartToBayArea()


def sendDataToServer():
    getGspLocation()
    data = {
        'id':'12345',
        'gpsLat':gpsLat,
       'gpsLong':gpsLong,
        'weight':weight,
        'moving':moving
        }
    headers = {'content-type':'application/json'}
    r = requests.post(url="https://139.59.15.209/sendReadings",data = data,headers = headers)
    print("data sent to server:",r.text)

def destroy():
    GPIO.cleanup()
    print("destroy everything")

def reverseInstruction(s):
    if(s=="Left"):
        return "Right"
    elif(s=="Right"):
        return "Left"
    return s

def main():
    try:
        moveForward = True
        moveReverse = False
        begin =0
        old_direction = ""
        new_direction = ""
        del rDis[:]
        del rDir[:]
        while moveForward:
            #rightMovement()
            move_info = getCartMovementDirection()
            #move_info = input().split(' ')
            #move_info[1] = int(move_info[1])
            # test data
            #move_info = ["Straight",20]
            print(move_info)
            if(move_info and len(move_info) > 1 and move_info[0] == "Reverse"):
                print("reversing cart")
                leftMovement()
                sleep(NINETY_DEG_TURN_TIME)
                sleep(NINETY_DEG_TURN_TIME)
                sleep(UPDATE_INTERVAL)
                stopMovement()
                reverseDirections.pop()
                rDis.pop()
                rDir.pop()
                moveReverse = True
                break;
            if(move_info and len(move_info) > 1 and move_info[0] and move_info[1] >= 0):
                d=0
                #direction, distance
                if(move_info[0]=="Left" or move_info[0]=="Right"):
                    moveCart(move_info[0], move_info[1]+1)
                else:
                    moveCart(move_info[0], move_info[1])
            sleep(UPDATE_INTERVAL)
        for i in range(len(rDis)):
            if(i==0):
                print("Straight",rDis[len(rDis)-i-1])
                moveCart("Straight", rDis[len(rDis)-i-1])
            else:
               print(reverseInstruction(rDir[len(rDis)-i]),rDis[len(rDis)-i-1]) 
               moveCart(reverseInstruction(rDir[len(rDis)-i]),rDis[len(rDis)-i-1])
            sleep(UPDATE_INTERVAL)
        main()
    except KeyboardInterrupt:
        stopMovement()
        destroy()
    
if __name__ == '__main__':
    setup()
    main()
