import sys
sys.path.append("../util/*")
sys.path.append("../db/*")
from util.Util import Util
from util.ScheduleManager import ScheduleManager
from db.ConnectionManager import ConnectionManager
import pymssql

class Patient:
    def __init__(self, username, password=None, salt=None, hash=None):
        self.username = username
        self.password = password
        self.salt = salt
        self.hash = hash
    
    # getters
    def get(self):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)

        get_patient_details = "SELECT Salt, Hash FROM Patients WHERE Username = %s"
        try:
            cursor.execute(get_patient_details, self.username)
            if cursor.rowcount == 0:
                print("Username does not exist!")
            for row in cursor:
                curr_salt = row['Salt']
                curr_hash = row['Hash']
                calculated_hash = Util.generate_hash(self.password, curr_salt)
                if not curr_hash == calculated_hash:
                    print("Incorrect password!")
                    cm.close_connection()
                    return None
                else:
                    self.salt = curr_salt
                    self.hash = calculated_hash
                    cm.close_connection()
                    return self
        except pymssql.Error as e:
            raise e
        finally:
            cm.close_connection()
        return None

    def get_username(self):
        return self.username

    def get_salt(self):
        return self.salt

    def get_hash(self):
        return self.hash

    def save_to_db(self):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()

        add_patients = "INSERT INTO Patients VALUES (%s, %s, %s)"
        try:
            cursor.execute(add_patients, (self.username, self.salt, self.hash))
            # you must call commit() to persist your data if you don't set autocommit to True
            conn.commit()
        except pymssql.Error:
            raise
        finally:
            cm.close_connection()

    def reserve(self, vaccine_name, availability, id=""):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor()
        reserve_appointment = "INSERT INTO Appointments (PatientName, VaccineName, Time, CaregiverName) VALUES (%s , %s , %s , %s)"
        try:
            cursor.execute(reserve_appointment, (self.username, vaccine_name, availability['Time'], availability['Username']))
            conn.commit()
            cursor.execute("SELECT @@IDENTITY AS GeneratedID")
            id = cursor.fetchone()[0]
        except pymssql.Error:
            raise
        finally:
            cm.close_connection()
        return id
    
    def show_appointments(self):
        cm = ConnectionManager()
        conn = cm.create_connection()
        cursor = conn.cursor(as_dict=True)
        reserved_appointment = "SELECT * FROM Appointments WHERE PatientName = %s ORDER BY ID"
        try:
            cursor.execute(reserved_appointment, self.username)
            patient_appointments = cursor.fetchall()
            ScheduleManager.list_appointment(patient_appointments, 'PatientName')
        except pymssql.Error:
            raise
        finally:
            cm.close_connection()