from flask import Flask, render_template,request,jsonify
import datetime
from flask_cors import CORS
import threading
import pymysql
import time
from IOT_GD import mcp3208
import RPi.GPIO as GPIO
from gpiozero import DistanceSensor
from picamera import PiCamera
from time import sleep
from flask_jwt_extended import * 
import pigpio

#camera = PiCamera()

#DB_HOST = "192.168.0.15" # CLASS IP
DB_HOST = "192.168.137.1" # HACKTHON IP
DB_PW = "111111"
DB_USER = "user"
DATABASE = "hacktone"
#SERVER_HOST = "192.168.0.26" # CLASS IP
SERVER_HOST = "192.168.137.116" # HACKTHON IP
SERVER_PORT = 5001

SECRET_KEY = "SECRET_KEY"

#led_digital_pin = 4 
led_digital_pin_list = [4,17,22,5,6,16]
led_digital_pin_status_list = [False,False,False,False,False,False]
led_pin = 13



servo_pin = 18

pi = pigpio.pi()

dis_led_pin = 27

sensor = DistanceSensor(echo=21,trigger=20,max_distance=2.0)

GPIO.setmode(GPIO.BCM)

GPIO.setup(led_pin,GPIO.OUT)

led_pwm = GPIO.PWM(led_pin,100)
led_pwm.start(0)

for n in led_digital_pin_list:
    GPIO.setup(n,GPIO.OUT)
    GPIO.output(n,GPIO.LOW)

#GPIO.setup(servo_pin,GPIO.OUT)

GPIO.setup(dis_led_pin,GPIO.OUT)
def setAngle(angle):
    start = 4
    end = 12.5
    if angle > 180 or angle < 0:
        return False
    ratio = (end - start)/180

    return start + angle*ratio


#servo_pwm = GPIO.PWM(servo_pin,50)
#servo_pwm.start(setAngle(0))

#servo_pwm.ChangeDutyCycle(0)
def map(x,input_min,input_max,output_min,output_max):
    return (x-input_min)*(output_max-output_min)/(input_max-input_min)+output_min #map()함수 정의

value = 0
servo_value = 0
servoStatus = False
#ledStatus = False

class Database():
    def __init__(self):
        self.db = pymysql.connect(host=DB_HOST,
                                  user=DB_USER,
                                  password=DB_PW,
                                  db=DATABASE,
                                  charset='utf8')
        self.cursor = self.db.cursor(pymysql.cursors.DictCursor)

    def execute(self, query, args={}):
        self.cursor.execute(query, args)

    def executeOne(self, query, args={}):
        self.cursor.execute(query, args)
        row = self.cursor.fetchone()
        return row

    def executeAll(self, query, args={}):
        self.cursor.execute(query, args)
        row = self.cursor.fetchall()
        return row

    def commit(self):
        self.db.commit()

import os

def getVideoFileNameList():
    return os.listdir("./static/videos")  

app = Flask(__name__,static_folder="./static")
app.config['JWT_SECRET_KEY'] = SECRET_KEY
jwt = JWTManager(app)
CORS(app)

def sqlExecute(sql):
    db = Database()
    db.cursor.execute(sql)
    db.commit()

    row = db.cursor.fetchall()
    db.cursor.close()

    return row

@app.route("/status")
#@jwt_required()
def statusRoute():
    output = {
            "led":led_digital_pin_status_list,
            "servo":servoStatus,
            }

    print(output)
    return jsonify(output)

@app.route('/')
def hello():
   now = datetime.datetime.now()
   timeString = now.strftime("%Y-%m-%d %H:%M")
   templateData = {
      'title' : 'HELLO!',
      'time': timeString
      }
   return render_template('index.html', **templateData)

@app.route('/db')
def db():
    db_class = Database()

    sql = "SELECT * FROM users"
    row = db_class.executeAll(sql)
    #print(row)
    db_class.db.close()
    return render_template('database.html', data=row)


@app.route('/manipulate')
def manipulate():
    videos = getVideoFileNameList()
    return render_template('manipulate.html',videos=videos)

@app.route("/videos")
#@jwt_required()
def videosRoute():
    output = {
            "fileNameArr":getVideoFileNameList()
            }
    return jsonify(output)

@app.route('/speak')
def speak():
    return render_template('sp_index.html')

def ledIncrease():
    for i in range(101):
        led_pwm.ChangeDutyCycle(i)
        time.sleep(0.05)

def allLedManipulate(user,flag):
    for n in led_digital_pin_list:
        GPIO.output(n,flag)
        sqlExecute("insert into led(user_name,status,led_number) values('{}',{},7)".format(user["name"],1 if flag else 0))
        led_digital_pin_status_list = [flag] * 6


@app.route('/led/<number>/<status>')
@jwt_required()
def ledRoute(number,status):
    user = get_jwt_identity()
    
    print("LED_{} : {}".format(number,status))
    
    global led_digital_pin_status_list,servoStatus
    
    cur_index = int(number)-1
    cur_pin = led_digital_pin_list[cur_index]

    print("LED STATUS : {}".format(status))
    if status == "true":
        if number == "7":
            allLedManipulate(user,True)
        else:
            threading.Thread(target=ledIncrease).start()
            GPIO.output(cur_pin,GPIO.HIGH)
            sqlExecute("insert into led(user_name,status,led_number) values('{}',1,{})".format(user["name"],cur_index+1))
            led_digital_pin_status_list[cur_index] = True
    else:
        if number == "7":
            allLedManipulate(user,False)
        else:
            led_pwm.ChangeDutyCycle(0)
            GPIO.output(cur_pin,GPIO.LOW)
            sqlExecute("insert into led(user_name,status,led_number) values('{}',0,{})".format(user["name"],cur_index+1))
            led_digital_pin_status_list[cur_index] = False
    output = {
            "led":led_digital_pin_status_list,
            "servo":servoStatus,
            }
    return jsonify(output)

@app.route('/servo/<status>')
#@jwt_required()
def servoRoute(status):
    global led_digital_pin_status_list,servoStatus
 #   user = get_jwt_identity()
    print("SERVO STATUS : {}".format(status))
    if status == "true":
        pi.set_servo_pulsewidth(servo_pin,2300)
  #      servo_pwm.ChangeDutyCycle(setAngle(90)) 
        #time.sleep(1)
  #      sqlExecute("insert into servo(user_name,status) values('{}',1)".format(user["name"]))
        servoStatus = True
    else:
        pi.set_servo_pulsewidth(servo_pin,500)
       # servo_pwm.ChangeDutyCycle(setAngle(0))
       # time.sleep(1)
     #   sqlExecute("insert into servo(user_name,status) values('{}',0)".format(user["name"]))
        servoStatus = False
    if status == "stop":
        pi.stop()
    output = {
            "led":led_digital_pin_status_list,
            "servo":servoStatus,
            }
    return jsonify(output)

@app.route("/db/execute",methods=["POST"])
@jwt_required()
def execute():
    sql = request.json["sql"]
    db_class = Database()

    db_class.cursor.execute(sql)
    db_class.db.commit()
    
    
    #db_class.cursor.execute("select * from users")
    row = db_class.cursor.fetchall()
    db_class.db.close()

   # print(row)
    return jsonify(row)

@app.route("/signup",methods=["POST"])
def signupRoute():
    name = request.json["name"]
    password = request.json["password"]
    sql = "select * from users where name='{}' and password='{}'".format(name,password)

    sql = "insert into users(name,password) values('{}','{}')".format(name,password)
    print(sql)
    db_class = Database()

    db_class.cursor.execute(sql)
    db_class.db.commit()
    
    row = db_class.cursor.fetchall()
    db_class.db.close()

    output = {
            "result":"signup successed."
            }
    return jsonify(output)

@app.route("/login",methods=["POST"])
def loginRoute():
    name = request.json["name"]
    password = request.json["password"]
    sql = "select * from users where name='{}' and password='{}'".format(name,password)
    db_class = Database()
    print(sql)
    db_class.cursor.execute(sql)
    db_class.db.commit()
    
    row = db_class.cursor.fetchall()
    db_class.db.close()

    if len(row) == 0:
        return jsonify({
            "result":False,
            "msg":"login failed ^^"
            }),403

    delta = datetime.timedelta(days=10)
    access_token = create_access_token(identity=row[0])
    
   # access_token = create_access_token(identity=row[0],expires_delta=delta)
    output = {
            "result":{
                "user":row[0],
                "access_token":access_token,
                }
            }
   # print(row)
    return jsonify(output)

@app.route("/jwt_test")
@jwt_required()
def jwt_test():
    user = get_jwt_identity()
    print(user)
    return jsonify(user=user),200

@app.route("/history")
def history(): 

    led = sqlExecute("select * from led order by id desc")
    servo = sqlExecute("select * from servo order by id desc")

    output = {
            "result" : {
                "led":led,
                "servo":servo
                }
            }
    return jsonify(output)
            
@app.route("/admin/<id>",methods=["DELETE"])
def d_admin(id):
    sqlExecute("update users set isAdmin=0 where id = {}".format(id))

    admin = sqlExecute("select * from users")
    output = {
            "result" : admin
            }

    print(admin)
    return jsonify(output)



@app.route("/admin",methods=["POST","GET"])
def admin():
    if request.method == "POST":
        user_id = request.json["user_id"]
        print(user_id)
        sqlExecute("update users set isAdmin=1 where id = {}".format(user_id))
   
    admin = sqlExecute("select * from users")
    output = {
            "result" : admin
            }

    print(admin)
    return jsonify(output)

@app.route("/speak/led",methods=["POST"])
def speackLed():
    key = request.json["key"]
    led_arr = request.json["led_arr"].split(",")
    status = request.json["status"]

    if key != "111111":
        return jsonify({
            "result":"key value error"
            })

    for c in led_arr:
        n = int(c)
        GPIO.output(led_digital_pin_list[n-1],GPIO.HIGH if status == "on" else GPIO.LOW)
        led_digital_pin_status_list[n-1] = True if status == "on" else False
        print(n)

    output = {
            "reslut":{
                "led":led_digital_pin_status_list,
                "servo":servoStatus,
                }
            }

    return jsonify(output)

@app.route("/speak/servo",methods=["POST"])
def speackServo():
    key = request.json["key"]
    status = request.json["status"]

    if key != "111111":
        return jsonify({
            "result":"key value error"
            })
    
    if status == "off":
        #servo_pwm.ChangeDutyCycle(2.5)
        servoStatus = False
    else:
       # servo_pwm.ChangeDutyCycle(12.5) 
        servoStatus = True

    

    output = {
            "reslut":{
                "led":led_digital_pin_status_list,
                "servo":servoStatus,
                }
            }

    return jsonify(output)
import datetime

isRecordingVideo = False

def recordingVideo():
    global isRecordingVideo
    camera.start_preview()
    fileName = datetime.datetime.now()
    camera.capture("./static/images/{}.jpg".format(fileName)) # take a picture
    
    camera.start_recording("./static/videos/{}.h264".format(fileName)) # record video
    sleep(5)
    camera.stop_recording()
    camera.stop_preview()

    isRecordingVideo = False

def sensorFunction():
    global isRecordingVideo
    while True:
        
        distance = sensor.distance * 100
        channels = []

        if distance <= 6:
            GPIO.output(dis_led_pin,GPIO.HIGH)
            if(not isRecordingVideo):
                isRecordingVideo = True
                threading.Thread(target=recordingVideo).start()
        else:
            GPIO.output(dis_led_pin,GPIO.LOW)


        for n in range(0, 8):
            data = mcp3208.readadc(n)
            channels.insert(n, data)
        for n in range(0, 8):
            print("| ch " + str(n+1) + ": " + str(channels[n])+"\t",end="")
            if n==2: #3th pin
                value = map(channels[n],0,8000,0,100)
        print("DISTANCE VALUE : ",distance,end="")
        
       #servo_pwm.ChangeDutyCycle(value)
        print("")
        time.sleep(0.2)

#threading.Thread(target=sensorFunction).start()

if __name__ == '__main__':

    #servo_pwm.ChangeDutyCycle(setAngle(2))
    app.run(debug=True, port=SERVER_PORT, host=SERVER_HOST)
