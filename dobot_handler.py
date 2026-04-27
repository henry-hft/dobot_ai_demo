from dobot_api import DobotApiDashboard, DobotApi, DobotApiMove, MyType, alarmAlarmJsonFile
from time import sleep
import subprocess
import re
import sys

class dobot_handler:
    def __init__(self, ip):
        self.restartEthernet()
        self.ip = ip
        self.dashboardPort = 29999
        self.movePort = 30003
        self.feedPort = 30004
        self.dashboard = DobotApiDashboard(ip, self.dashboardPort)
        self.move = DobotApiMove(ip, self.movePort)
        self.feed = DobotApi(ip, self.feedPort)

    def start(self):
        enableState = self.parseResultId(self.dashboard.EnableRobot())
        if enableState[0] != 0:
            raise Exception("Verbindung fehlgeschlagen")
        
        print("Verbindung erfolgreich")

        start_point = [300, 0, -50.3, 48] # x, y, z, r
        
        self.dashboard.EnableRobot()
        self.dashboard.ClearError()

        self.setDO(8, 1)
        sleep(0.5)
        self.setDO(8, 0)

        # move to start point
        move = self.moveToPoint(start_point)

    def setDO(self, port, value):
        self.dashboard.DOExecute(8, value)
        print(f"Port {port} set to {value}\n")
        
    def getPosition(self):
        position = self.dashboard.GetPose() 
        match = re.search(r'\{([^}]*)\}', position)

        if match:
            values_str = match.group(1)
            values_array = [float(val) for val in values_str.split(',')]
            return(values_array)
        return [0,0,0,0]
    
    def moveToZ(self, z_value):
        current_position = self.getPosition()
        if len(current_position) != 4:
            raise ValueError("Current position must contain 4 elements.")

        new_position = current_position.copy()
        new_position[2] = z_value
        self.moveToPoint(new_position)

    def moveToPoint(self, point_list: list):
        if len(point_list) == 3:
            current_position = self.getPosition()
            point_list.append(current_position[3])
        elif len(point_list) != 4:
            raise ValueError("point_list must have either 3 or 4 elements.")

        # Winkel anpassen
        if point_list[3] < -45:
            point_list[3] += 180
        elif point_list[3] > 135:
            point_list[3] -= 180

        move = self.move.MovL(
            point_list[0], point_list[1], point_list[2], point_list[3], 0, 0, 0)
        print("MovL ", move)
        commandArrID = self.parseResultId(move)
        return commandArrID
    
    def getErrorMessage(self):
        dataController, dataServo = alarmAlarmJsonFile()
        geterrorID = self.parseResultId(self.dashboard.GetErrorID())
        if geterrorID[0] == 0:
            for i in range(1, len(geterrorID)):
                for item in dataController:
                    if geterrorID[i] == item["id"]:
                        return item["en"]["description"]

                for item in dataServo:
                    if geterrorID[i] == item["id"]:
                        return item["en"]["description"]

        
    def parseResultId(self, valueRecv):
        if valueRecv.find("Not Tcp") != -1: 
            print("Control mode is not TCP")
            return [1]
        recvData = re.findall(r'-?\d+', valueRecv)
        recvData = [int(num) for num in recvData]
        if len(recvData) == 0:
            return [2]
        return recvData
    
    def restartEthernet(self):
        print("Restarting Ethernet Interface...")
        subprocess.run(["sudo", "ifconfig", "eth0", "down"])
        sleep(1.0)
        subprocess.run(["sudo", "ifconfig", "eth0", "up"])
        sleep(1.0)
