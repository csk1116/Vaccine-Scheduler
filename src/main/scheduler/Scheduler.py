from model.Vaccine import Vaccine
from model.Caregiver import Caregiver
from model.Patient import Patient
from util.ScheduleManager import ScheduleManager
from util.Util import Util
from db.ConnectionManager import ConnectionManager
import pymssql
import datetime


'''
objects to keep track of the currently logged-in user
Note: it is always true that at most one of currentCaregiver and currentPatient is not null
        since only one user can be logged-in at a time
'''
current_patient = None

current_caregiver = None


def create_patient(tokens):
    # create_patient <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        print("Please check your command as -> create_patient <username> <password>")
        return

    username = tokens[1].lower()
    password = tokens[2]
    # check 2: check if the username has been taken already
    if username_exists_patient(username):
        print("Username taken, try again!")
        return

    # check 3: strong password check
    while not ScheduleManager.check_password(password):
        password = input("Please enter a strong password: ")

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the patient
    patient = Patient(username, salt=salt, hash=hash)

    # save to patient information to our database
    try:
        patient.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def create_caregiver(tokens):
    # create_caregiver <username> <password>
    # check 1: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Failed to create user.")
        print("Please check your command as -> create_caregiver <username> <password>")
        return

    username = tokens[1].lower()
    password = tokens[2]

    # check 2: check if the username has been taken already
    if username_exists_caregiver(username):
        print("Username taken, try again!")
        return

    # check 3: strong password check
    while not ScheduleManager.check_password(password):
        password = input("Please enter a strong password: ")

    salt = Util.generate_salt()
    hash = Util.generate_hash(password, salt)

    # create the caregiver
    caregiver = Caregiver(username, salt=salt, hash=hash)

    # save to caregiver information to our database
    try:
        caregiver.save_to_db()
    except pymssql.Error as e:
        print("Failed to create user.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Failed to create user.")
        print(e)
        return
    print("Created user ", username)


def username_exists_caregiver(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Caregivers WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def username_exists_patient(username):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_username = "SELECT * FROM Patients WHERE Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_username, username)
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Username'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking username")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking username")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def login_patient(tokens):
    # login_patient <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_patient
    if current_caregiver is not None or current_patient is not None:
        current_username = current_caregiver.get_username() if current_caregiver else current_patient.get_username()
        print("User: {} already logged in.".format(current_username))
        print("Please logout first.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        print("Please check your command as -> login_patient <username> <password>")
        return

    username = tokens[1].lower()
    password = tokens[2]

    patient = None
    try:
        patient = Patient(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if patient is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_patient = patient


def login_caregiver(tokens):
    # login_caregiver <username> <password>
    # check 1: if someone's already logged-in, they need to log out first
    global current_caregiver
    if current_caregiver is not None or current_patient is not None:
        current_username = current_caregiver.get_username() if current_caregiver else current_patient.get_username()
        print("User: {} already logged in.".format(current_username))
        print("Please logout first.")
        return

    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Login failed.")
        print("Please check your command as -> login_caregiver <username> <password>")
        return

    username = tokens[1].lower()
    password = tokens[2]

    caregiver = None
    try:
        caregiver = Caregiver(username, password=password).get()
    except pymssql.Error as e:
        print("Login failed.")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Login failed.")
        print("Error:", e)
        return

    # check if the login was successful
    if caregiver is None:
        print("Login failed.")
    else:
        print("Logged in as: " + username)
        current_caregiver = caregiver


def search_caregiver_schedule(tokens):
    # Both patients and caregivers can perform this operation.
    # Output the username for the caregivers that are available for the date, 
    # along with the number of available doses left for each vaccine. Order by the username of the caregiver. 
    # Separate each attribute with a space.
    # If no user is logged in, print “Please login first!”.
    # For all other errors, print "Please try again!".
    
    # check1: if any user login.
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return
    
    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        print("Please check your command as -> search_caregiver_schedule <date>")
        return
    
    # check 3: check if input date format is valid.
    date = tokens[1].lower()
    try:
        date_tokens = date.split("-")
        month = int(date_tokens[0])
        day = int(date_tokens[1])
        year = int(date_tokens[2])
        d = datetime.datetime(year, month, day)
    except ValueError:
        print("Please enter a valid date!")
        return
    
    cm = ConnectionManager()
    conn = cm.create_connection()
    
    try:
        cursor = conn.cursor(as_dict=True)
        select_availability = "SELECT * FROM Availabilities WHERE Time = %s AND Status = 0 ORDER BY Username"
        select_vaccine = "SELECT * FROM Vaccines"
        cursor.execute(select_availability, d)
        available_user = cursor.fetchall()
        cursor.execute(select_vaccine)
        vaccine_status = cursor.fetchall()
        ScheduleManager.show_caregiver_schedule(available_user, vaccine_status)
    except pymssql.Error as e:
        print("Search caregiver schedule Failed")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when searching caregiver schedule")
        print("Error:", e)
    finally:
        cm.close_connection()


def reserve(tokens):
    # Patients perform this operation to reserve an appointment.
    # Caregivers can only see a maximum of one patient per day, meaning that if the reservation went through, the caregiver is no longer available for that date.
    # If there are available caregivers, choose the caregiver by alphabetical order and print “Appointment ID: {appointment_id}, Caregiver username: {username}” for the reservation.
    # If there’s no available caregiver, print “No Caregiver is available!”. If not enough vaccine doses are available, print "Not enough available doses!".
    # If no user is logged in, print “Please login first!”. If the current user logged in is not a patient, print “Please login as a patient!”.
    # For all other errors, print "Please try again!".

    # check1: if any patient login.
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return
    if current_patient is None:
        print("Please login as a patient.")
        return
    
    # check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        print("Please check your command as -> reserve <date> <vaccine>")
        return
    
    # check 3: check if input date format is valid.
    date = tokens[1].lower()
    try:
        date_tokens = date.split("-")
        month = int(date_tokens[0])
        day = int(date_tokens[1])
        year = int(date_tokens[2])
        d = datetime.datetime(year, month, day)
    except ValueError:
        print("Please enter a valid date!")
        return
    
    
    # check 4 check if any caregiver availabile on this date and if vaccine has enough doses.
    vaccine_name = tokens[2].lower()
    availability = search_availability(d)
    vaccine = vaccine_available(vaccine_name)

    if vaccine and vaccine['Doses'] == 0:
        print("Not enough available doses!")
        print("Please try another vaccine.")
        return
    if not availability or not vaccine:
        print("Please try another date or another vaccine.")
        return
    
    
    # update availability and doses
    if not update_availability(availability, 1):
        print("Please try again!")
        return
    if not update_doses(vaccine, -1):
        update_availability(availability, 0)
        print("Please try again!")
        return

    # reserve
    try:
        reserve_result = current_patient.reserve(vaccine_name, availability)
    except pymssql.Error as e:
        print("Reserve Failed")
        print("Please try again!")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when reserving")
        print("Please try again!")
        print("Error:", e)
        return
    if reserve_result != "":
        print("Appointment confirmed!")
        print("Appointment ID: {appointment_id}, Caregiver username: {username}".format(appointment_id=reserve_result, username=availability['Username']))


def search_availability(date):
    cm = ConnectionManager()
    conn = cm.create_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        select_availability = "SELECT TOP 1 * FROM Availabilities WHERE Time = %s AND Status = 0 ORDER BY Username"  
        cursor.execute(select_availability, date)
        availablility = cursor.fetchone()
        if not availablility:
            print("No Caregiver is available!")
    except pymssql.Error as e:
        print("Search Failed")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when searching schedule")
        print("Error:", e)
        return {}
    finally:
        cm.close_connection()
    return availablility


def vaccine_available(vaccine_name):
    cm = ConnectionManager()
    conn = cm.create_connection()
    try:
        cursor = conn.cursor(as_dict=True)
        select_vaccine = "SELECT * FROM Vaccines WHERE Name = %s"
        cursor.execute(select_vaccine, vaccine_name)
        vaccine_status = cursor.fetchone()
        if not vaccine_status:
            print("This vaccine is not available!")
    except pymssql.Error as e:
        print("Search Failed")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when searching schedule")
        print("Error:", e)
    finally:
        cm.close_connection()
    return vaccine_status


def update_availability(availability, method):
    if method == 1:
        set_availability = "UPDATE Availabilities SET Status = 1 WHERE Time = %s AND Username = %s"
    elif method == 0:
        set_availability = "UPDATE Availabilities SET Status = 0 WHERE Time = %s AND Username = %s"
    else:
        print("Invalid method")
        return False

    cm = ConnectionManager()
    conn = cm.create_connection()

    try:
        cursor = conn.cursor()
        cursor.execute(set_availability, (availability['Time'], availability['Username']))
        conn.commit()
        return True
    except pymssql.Error as e:
        print("Error occurred when updating availability")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when updating availability")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def update_doses(vaccine, method):

    current_vaccine = None
    try:
        current_vaccine = Vaccine(vaccine['Name'], vaccine['Doses']).get()
    except pymssql.Error as e:
        print("Error occurred when getting vaccine")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when getting vaccine")
        print("Error:", e)
        return False
    
    if method == 1:
        try:
            current_vaccine.increase_available_doses(1)
            return True
        except pymssql.Error as e:
            print("Error occurred when updating doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when updating doses")
            print("Error:", e)
    elif method == -1:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            current_vaccine.decrease_available_doses(1)
            return True
        except pymssql.Error as e:
            print("Error occurred when updating doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when updating doses")
            print("Error:", e)
    else:
        print("Invalid method!")
    return False


def upload_availability(tokens):
    #  upload_availability <date>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        print("Please check your command as -> upload_availability <date>")
        return

    # check 3: check if input date format is valid.
    date = tokens[1].lower()
    try:
        date_tokens = date.split("-")
        month = int(date_tokens[0])
        day = int(date_tokens[1])
        year = int(date_tokens[2])
        d = datetime.datetime(year, month, day)
    except ValueError:
        print("Please enter a valid date!")
        return
    
    # check 4: check if date is already availbale for the caregiver.
    if availability_exist_caregiver(d, current_caregiver.get_username()):
        print("This date is already update. Try another date!")
        return
    
    try:
        current_caregiver.upload_availability(d)
    except pymssql.Error as e:
        print("Upload Availability Failed")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when uploading availability")
        print("Error:", e)
        return
    print("Availability uploaded!")


def availability_exist_caregiver(date, username):
    cm = ConnectionManager()
    conn = cm.create_connection()
    select_availability = "SELECT * FROM Availabilities WHERE Time = %s AND Username = %s"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_availability, (date, username))
        #  returns false if the cursor is not before the first record or if there are no rows in the ResultSet.
        for row in cursor:
            return row['Time'] is not None
    except pymssql.Error as e:
        print("Error occurred when checking availability")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking availability")
        print("Error:", e)
    finally:
        cm.close_connection()
    return False


def cancel(tokens):
    # Both caregivers and patients should be able to cancel an existing appointment. 
    # Implement the cancel operation for both caregivers and patients. 
    # Hint: both the patient’s schedule and the caregiver’s schedule should reflect the change when an appointment is canceled.
    
    # check1: if any patient login.
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return

    # check 2: the length for tokens need to be exactly 2 to include all information (with the operation name)
    if len(tokens) != 2:
        print("Please try again!")
        print("Please check your command as -> cancel <appointment_id>")
        return
    
    # check 3: check if this id exist or is canceled
    try:
        id = int(tokens[1])
    except ValueError:
        print("Please enter a valid ID!")
        return
    
    user = current_caregiver.get_username() if current_caregiver else current_patient.get_username()
    appointment = appointment_exist(id, user)
    if not appointment:
        print("This appointment has already canceled or you don't have this appointment.")
        print("Please make sure you your appointment ID is correct.")
        return
    
    # update availability and doses
    availability = {"Time": appointment['Time'], "Username": appointment['CaregiverName'], "Status": 1}
    vaccine = vaccine_available(appointment['VaccineName'])
    if not vaccine:
        print("Please try again!")
        return
    if not update_availability(availability, 0):
        print("Please try again!")
        return
    if not update_doses(vaccine, 1):
        update_availability(availability, 1)
        print("Please try again!")
        return

    # cancel
    cm = ConnectionManager()
    conn = cm.create_connection()
    try:
        cursor = conn.cursor()
        cancel_appointment = "UPDATE Appointments SET Status = 0 WHERE ID = %d"
        cursor.execute(cancel_appointment, id)
        conn.commit()
        print("Cancel confirmed: Appointment ID:{}".format(id))
    except pymssql.Error as e:
        print("Cancel Appointment Failed")
        print("Please try again!")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when canceling appointment")
        print("Please try again!")
        print("Error:", e)
    finally:
        cm.close_connection()


def appointment_exist(id, user):
    cm = ConnectionManager()
    conn = cm.create_connection()

    select_appointment = "SELECT * FROM Appointments WHERE ID = %d AND Status = 1 AND (CaregiverName = %s OR PatientName = %s)"
    try:
        cursor = conn.cursor(as_dict=True)
        cursor.execute(select_appointment, (id, user, user))
        appointment = cursor.fetchone()
    except pymssql.Error as e:
        print("Error occurred when checking appointment")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when checking appointment")
        print("Error:", e)
    finally:
        cm.close_connection()
    return appointment


def add_doses(tokens):
    #  add_doses <vaccine> <number>
    #  check 1: check if the current logged-in user is a caregiver
    global current_caregiver
    if current_caregiver is None:
        print("Please login as a caregiver first!")
        return

    #  check 2: the length for tokens need to be exactly 3 to include all information (with the operation name)
    if len(tokens) != 3:
        print("Please try again!")
        print("Please check your command as -> add_doses <vaccine> <number>")
        return

    vaccine_name = tokens[1].lower()

    try:
        doses = int(tokens[2])
    except ValueError:
        print("Please enter a valid doses!")
        return
    
    vaccine = None
    try:
        vaccine = Vaccine(vaccine_name, doses).get()
    except pymssql.Error as e:
        print("Error occurred when adding doses")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when adding doses")
        print("Error:", e)
        return

    # if the vaccine is not found in the database, add a new (vaccine, doses) entry.
    # else, update the existing entry by adding the new doses
    if vaccine is None:
        vaccine = Vaccine(vaccine_name, doses)
        try:
            vaccine.save_to_db()
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    else:
        # if the vaccine is not null, meaning that the vaccine already exists in our table
        try:
            vaccine.increase_available_doses(doses)
        except pymssql.Error as e:
            print("Error occurred when adding doses")
            print("Db-Error:", e)
            quit()
        except Exception as e:
            print("Error occurred when adding doses")
            print("Error:", e)
            return
    print("Doses updated!")


def show_appointments(tokens):
    # Output the scheduled appointments for the current user (both patients and caregivers). 
    # For caregivers, you should print the appointment ID, vaccine name, date, and patient name. Order by the appointment ID. Separate each attribute with a space.
    # For patients, you should print the appointment ID, vaccine name, date, and caregiver name. Order by the appointment ID. Separate each attribute with a space.
    # If no user is logged in, print “Please login first!”.
    # For all other errors, print "Please try again!".
    
    # check1: if any patient login.
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return
    
    try:
        if current_caregiver:
            current_caregiver.show_appointments()
            return
        if current_patient:
            current_patient.show_appointments()
            return
    except pymssql.Error as e:
        print("show Appointments Failed")
        print("Please try again!")
        print("Db-Error:", e)
        quit()
    except Exception as e:
        print("Error occurred when showing appointments")
        print("Please try again!")
        print("Error:", e)


def logout(tokens):
    # if not logged in
    global current_caregiver, current_patient
    if current_caregiver is None and current_patient is None:
        print("Please login first.")
        return

    # logout
    try:
        current_caregiver = None
        current_patient = None
    except Exception as e:
        print("Please try again!")
        print("Error:", e)
        return
    print("Successfully logged out!")


def show_command():
    print()
    print(" *** Please enter one of the following commands *** ")
    print("> create_patient <username> <password>")
    print("> create_caregiver <username> <password>")
    print("> login_patient <username> <password>")
    print("> login_caregiver <username> <password>")
    print("> search_caregiver_schedule <date>")
    print("> reserve <date> <vaccine>")
    print("> upload_availability <date>")
    print("> cancel <appointment_id>")
    print("> add_doses <vaccine> <number>")
    print("> show_appointments")
    print("> logout")
    print("> Quit")
    print("> Help")
    print()


def start():
    stop = False
    show_command()
    while not stop:
        response = ""
        print("> ", end='')

        try:
            response = str(input())
        except ValueError:
            print("Please try again!")
            break

        # I found this will make strong password fail.
        # I disable this and handle lowercase in each methods.
        # -> response = response.lower()
        tokens = response.split(" ")
        if len(tokens) == 0:
            ValueError("Please try again!")
            continue
        operation = tokens[0].lower()
        if operation == "create_patient":
            create_patient(tokens)
        elif operation == "create_caregiver":
            create_caregiver(tokens)
        elif operation == "login_patient":
            login_patient(tokens)
        elif operation == "login_caregiver":
            login_caregiver(tokens)
        elif operation == "search_caregiver_schedule":
            search_caregiver_schedule(tokens)
        elif operation == "reserve":
            reserve(tokens)
        elif operation == "upload_availability":
            upload_availability(tokens)
        elif operation == "cancel":
            cancel(tokens)
        elif operation == "add_doses":
            add_doses(tokens)
        elif operation == "show_appointments":
            show_appointments(tokens)
        elif operation == "logout":
            logout(tokens)
        elif operation == "quit":
            print("Bye!")
            stop = True
        elif operation == "help":
            show_command()
        else:
            print("Invalid operation name!")

        if operation != "quit":
            print()
            print("use Help to browse commands.")
            print()

if __name__ == "__main__":
    '''
    // pre-define the three types of authorized vaccines
    // note: it's a poor practice to hard-code these values, but we will do this ]
    // for the simplicity of this assignment
    // and then construct a map of vaccineName -> vaccineObject
    '''

    # start command line
    print()
    print("Welcome to the COVID-19 Vaccine Reservation Scheduling Application!")

    start()
