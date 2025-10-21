# utils.py
# This file contains utility functions for decoding and handling config and update messages.
import json
import struct
import numpy as np
from types import SimpleNamespace

import numpy as np
import time
import pandas as pd
import os
import socket
import math
import warnings
from typing import Optional, Tuple, Union

# Check if we're in test mode (no Candle hardware)
TEST_MODE = True  # Set to False when using real hardware

if TEST_MODE:
    from mock_motor_controller import MockMotorController as MotorController
    print("Running in test mode with mock controller")
else:
    import pyCandle
    from motor_controller import MotorController


def handle_motor_test(motor_controller , val):
    motor_controller.set_target_torque(0, val)  


def decodeSingleValueMessage(msg):
    try:
        format_string = '!f'  # Format entsprechend der Anzahl der Elemente in der Nachricht
        unpacked_data = struct.unpack(format_string, msg)
        # Entpacken und zuweisen der Werte
        print(unpacked_data)
        return SimpleNamespace(
            candle_mode=1,
            motor_no=0,
            value=unpacked_data[0]
        )
    except Exception as e:
        print(f"Decoding error: {e}")
        return None

def decodeUpdateMessage(msg):
    try:
        # format_string = '!14f'  # Format entsprechend der Anzahl der Elemente in der Nachricht
        format_string = '!IIfffffffffff'  # Format entsprechend der Anzahl der Elemente in der Nachricht

        unpacked_data = struct.unpack(format_string, msg)
        # Entpacken und zuweisen der Werte
        return SimpleNamespace(
            values = unpacked_data
        )
    except Exception as e:
        print(f"Decoding error: {e}")
        return None

def decodeConfigMessage(msg):
    try:
        format_string = '!III'  # Fügen Sie 'I' am Ende hinzu, um den Bool-Wert als Integer zu empfangen
        candle_mode, motor_no, zero_out_encoder = struct.unpack(format_string, msg)
        print("Motor No:", motor_no)
        zero_encoder_bool = bool(zero_out_encoder)  # Konvertiert den Integer zurück in einen Bool-Wert
        return SimpleNamespace(candle_mode=candle_mode, motor_no=motor_no, zero_out_encoder=zero_encoder_bool)
    except Exception as e:
        print(f"Decoding error: {e}")
        return None

def simpleDecodeiMBlocksFloatMessage_old(msg):
    try:
        if len(msg) == 4:
            # Single single-precision float
            format_string = '<f'  # Big-endian single-precision float
            unpacked_data = struct.unpack(format_string, msg)
            return SimpleNamespace(
                candle_mode=1,
                motor_no=0,
                value=unpacked_data[0]
            )
        elif len(msg) == 8:
            # Two single-precision floats
            format_string = '<ff'  # Big-endian two single-precision floats
            unpacked_data = struct.unpack(format_string, msg)
            return SimpleNamespace(
                candle_mode=1,
                motor_no=0,
                value1=unpacked_data[0],
                value2=unpacked_data[1]
            )
        elif len(msg) == 12:
            # Three single-precision floats
            format_string = '<fff'  # Big-endian two single-precision floats
            unpacked_data = struct.unpack(format_string, msg)
            return SimpleNamespace(
                candle_mode=1,
                motor_no=0,
                value1=unpacked_data[0],
                value2=unpacked_data[1],
                value3=unpacked_data[2]
            )
        else:
            raise ValueError("Input message must be exactly 4, 8 or 12 bytes.")
    
    except Exception as e:
        print(f"Decoding error: {e}")
        return None
    
def simpleDecodeiMBlocksDoubleMessage(msg):
    try:
        format_string = '<' + (int(len(msg) / 8) * 'd')
        unpacked_data = struct.unpack(format_string, msg)
        #print(unpacked_data)
        return SimpleNamespace(
            candle_mode=1,
            motor_no=0,
            values=unpacked_data
        )        
    
    except Exception as e:
        print(f"Decoding error: {e}")
        return None
    
def simpleDecodeiMBlocksFloatMessage(msg):
    try:
        format_string = '<' + (int(len(msg) / 4) * 'f')
        unpacked_data = struct.unpack(format_string, msg)
        return SimpleNamespace(
            candle_mode=1,
            motor_no=0,
            values=unpacked_data
        )        
    
    except Exception as e:
        print(f"Decoding error: {e}")
        return None


def decodeiMBlocksMessage(msg):
    try:
        format_string = '!ddddddddddd'  # Format entsprechend der Anzahl der Elemente in der Nachricht
        unpacked_data = struct.unpack(format_string, msg)
        # Entpacken und zuweisen der Werte
        return SimpleNamespace(
            #MAJS hardcoded candle mode is not ideal
            candle_mode=1,
            motor_no=0,
            #kp=unpacked_data[0],
            kp=3,
            #kd=unpacked_data[1],
            kd=0.44,
            #ki=unpacked_data[2],
            ki=unpacked_data[2],
            torque=unpacked_data[3],
            max_torque=12,
            #max_torque=unpacked_data[4],
            target_position=unpacked_data[5],
            target_velocity=unpacked_data[6],
            iWindup=unpacked_data[7],
            max_velocity=unpacked_data[8],
            upper_position_limit=unpacked_data[9],
            lower_position_limit=unpacked_data[10]
        )
    except Exception as e:
        print(f"Decoding error: {e}")
        return None

def handleConfigMessage(motor_controller, message):
    if message.candle_mode == 0:
        motor_controller.set_motor_mode(message.motor_no, pyCandle.Md80Mode_E.IDLE)
    elif message.candle_mode == 1:
        motor_controller.set_motor_mode(message.motor_no, pyCandle.Md80Mode_E.IMPEDANCE)
    elif message.candle_mode == 3:
        motor_controller.set_motor_mode(message.motor_no, pyCandle.Md80Mode_E.POSITION_PID)
    elif message.candle_mode == 2:
        motor_controller.set_motor_mode(message.motor_no, pyCandle.Md80Mode_E.VELOCITY_PID)        

def handle_soft_limits(motor_controller):
        status = motor_controller.get_motor_status(0)
        # überprüfen, ob innerhalb der Limits, wenn ja Bewegung so frei wie möglich -> kd, kp =0
        #if (status["position"] < 1 and status["position"] > -1):
        if (status["position"] < motor_controller.upper_limit and status["position"] > motor_controller.lower_limit):
            motor_controller.set_target_position(0, status["position"])
            motor_controller.set_impedance_controller_params(motor_controller.motor_no ,0,0)

            print("Position:" + str(status["position"]) + "   kd: " + str(0) + "  kp: " + str(0))
        #wenn außerhalb der Limits: kd, kp wie von user eingestellt
        #target position ist die, die zuletzt innerhalb der Limits war
        else:
            motor_controller.set_impedance_controller_params(motor_controller.motor_no ,motor_controller.kp,motor_controller.kd)
            #print("Limit_Position:" + str(status["position"]) + "  Limit_kd: " + str(motor_controller.kd) + "  Limit_kp: " +str(motor_controller.kp))

def handle_motor_params(motor_controller, previous_kP_weighted, max_increase=1.3, max_decrease=10.0, deadband_threshold=0.3):
    # Ursprüngliche Implementierung
    kD0 = 0
    kP0 = 200
    alpha = 3
    kP_weighted = previous_kP_weighted

    status = motor_controller.get_motor_status(0)
    position = status["position"]

    # Berechnung der gewichteten kD und kP
    kD_weighted = kD0 * np.exp(-alpha * abs(position))
    kP_weighted = kP0 * (position / 1.27)

    control_signal = motor_controller.control_signal
    if control_signal < 0:
        control_signal = 0
        kP_weighted = kP0 * np.exp(kP0 * control_signal * abs(position)) - 1

        if kP_weighted < 0:
            kP_weighted = 0
        if kD_weighted < 0:    
            kD_weighted = 0

    # Änderung der kP_weighted basierend auf max_increase und max_decrease
    delta_kP = kP_weighted - previous_kP_weighted
    if delta_kP > max_increase:
        kP_weighted = previous_kP_weighted + max_increase
    elif delta_kP < -max_decrease:
        kP_weighted = previous_kP_weighted - max_decrease

    # Deadband-Logik
    if abs(kP_weighted - previous_kP_weighted) < deadband_threshold:
        kP_weighted = previous_kP_weighted

    # Zuweisen der gewichteten Parameter zum Motor Controller
    motor_controller.kp = kP_weighted
    motor_controller.kd = kD_weighted
    print(f"Control Signal: {control_signal}")
    print(f"Updated kP: {motor_controller.kp}, kD: {motor_controller.kd}")

    return kP_weighted

def handle_motor_params_smooth_decrease(motor_controller, previous_kP_weighted, max_increase=1.3, max_decrease=5.0, deadband_threshold=0.3):
    # Implementierung für sanfte Verringerung
    kD0 = 0
    kP0 = 28
    alpha = 3
    kP_weighted = previous_kP_weighted

    status = motor_controller.get_motor_status(0)
    position = status["position"]

    # Berechnung der gewichteten kD und kP
    kD_weighted = kD0 * np.exp(-alpha * abs(position))
    kP_weighted = kP0 * (position / 1.57)

    control_signal = motor_controller.control_signal
    if control_signal < 0:
        control_signal = 0
        kP_weighted = kP0 * np.exp(kP0 * control_signal * abs(position)) - 1

        if kP_weighted < 0:
            kP_weighted = 0
        if kD_weighted < 0:    
            kD_weighted = 0

    # Sanftere Verringerung der kP_weighted
    delta_kP = kP_weighted - previous_kP_weighted
    if delta_kP > max_increase:
        kP_weighted = previous_kP_weighted + max_increase
    elif delta_kP < -max_decrease:
        kP_weighted = previous_kP_weighted - max_decrease

    # Deadband-Logik
    if abs(kP_weighted - previous_kP_weighted) < deadband_threshold:
        kP_weighted = previous_kP_weighted

    # Zuweisen der gewichteten Parameter zum Motor Controller
    motor_controller.kp = kP_weighted
    motor_controller.kd = kD_weighted
    print(f"Control Signal: {control_signal}")
    print(f"Updated kP: {motor_controller.kp}, kD: {motor_controller.kd}")

    return kP_weighted

def calculate_kP_modified_gaussian(
    kP0,
    position,
    range_max=1.27,
    control_signal=0.5,
    sigma=0.2
):
    """
    Berechnet den proportionalen Verstärkungsfaktor (kP) basierend auf einer modifizierten Gaußschen Verteilung.
    - kP startet bei 0 und erreicht kP0 in der Mitte der Bewegungsreichweite.
    - Die Breite der Verteilung wird durch sigma gesteuert.

    Args:
        kP0 (float): Maximale kP-Wert in der Mitte der Verteilung.
        position (float): Aktuelle Position des Motors (in Radiant).
        range_max (float): Maximale Bewegungsreichweite des Motors (in Radiant).
        control_signal (float): EMG-Steuersignal, das die Breite der Gaußschen Verteilung steuert (0 bis 1).
        sigma (float): Standardabweichung der Gaußschen Verteilung.

    Returns:
        float: Berechneter kP-Wert.
    """
    # Zentrum der Gaußschen Verteilung
    mu = range_max / 2
    
    # Berechnung des skalierenden Faktors
    scaling_factor = position / mu if mu != 0 else 0.0
    
    # Berechnung des kP-Werts anhand der modifizierten Gaußschen Funktion
    #exponent = - ((position - mu) ** 2) / (2 * sigma ** 2)
    exponent = - ((position - mu) ** 2) / (2 * control_signal ** 2)
    gaussian_component = np.exp(exponent)
    kP_weighted = kP0 * scaling_factor * gaussian_component
    
    return kP_weighted

def handle_motor_params_modified_gaussian(
    motor_controller,
    previous_kP_weighted,
    kP0=28.0,
    range_max=1.27,
    max_increase=1.3,
    max_decrease=5.0,
    deadband_threshold=0.3,
    sigma=0.2
):
    """
    Aktualisiert die Motorparameter basierend auf einer modifizierten Gaußschen Verteilung für kP.
    - Low kP an den Enden der Bewegungsreichweite.
    - High kP in der Mitte der Bewegungsreichweite.
    - Breite der Gaußschen Verteilung wird durch sigma gesteuert.
    
    Args:
        motor_controller (MotorController): Objekt zur Steuerung des Motors.
        previous_kP_weighted (float): Der vorherige kP_weighted-Wert.
        kP0 (float): Maximale kP-Wert in der Mitte der Verteilung.
        range_max (float): Maximale Bewegungsreichweite des Motors (in Radiant).
        max_increase (float): Maximale Erhöhung von kP_weighted pro Aufruf.
        max_decrease (float): Maximale Verringerung von kP_weighted pro Aufruf.
        deadband_threshold (float): Schwellenwert für den Deadband.
        sigma (float): Standardabweichung der Gaußschen Verteilung.
    
    Returns:
        float: Der aktualisierte kP_weighted-Wert.
    """
    status = motor_controller.get_motor_status(0)
    position = status["position"]
    
    control_signal = motor_controller.control_signal
    if control_signal < 0:
        control_signal = 0.0  # Negative Signale optional auf 0 setzen
    
    print(f"Position: {position}, Control Signal: {control_signal}")
    
    # Berechne den neuen kP_weighted-Wert mit der modifizierten Gaußschen Funktion
    new_kP_weighted = calculate_kP_modified_gaussian(
        kP0=kP0,
        position=position,
        range_max=range_max,
        control_signal=control_signal,
        sigma=sigma
    )
    
    # Berechne die Differenz für das Ramping
    delta_kP = new_kP_weighted - previous_kP_weighted
    
    # Asymmetrische Begrenzung: Maximale Erhöhung und Verringerung
    if delta_kP > max_increase:
        new_kP_weighted = previous_kP_weighted + max_increase
    elif delta_kP < -max_decrease:
        new_kP_weighted = previous_kP_weighted - max_decrease
    
    # Deadband-Logik: Wenn die Änderung klein ist, keine Aktualisierung
    if abs(new_kP_weighted - previous_kP_weighted) < deadband_threshold:
        new_kP_weighted = previous_kP_weighted
    
    # Sicherstellen, dass kP_weighted nicht negativ wird
    new_kP_weighted = max(new_kP_weighted, 0.0)
    
    # Aktualisiere die Motorparameter
    motor_controller.kp = new_kP_weighted
    motor_controller.kd = 0.0  # Falls gewünscht, kann auch kD angepasst werden
    
    print(f"Updated kP: {motor_controller.kp}, kD: {motor_controller.kd}")
    
    return new_kP_weighted

def calculate_kP_custom_function(
    kP0,
    position,
    range_max=1.27,
    control_signal=0.5,
    sigma=0.2,
    inflection_point_control=0.5,
    slope_control=0.5
):
    """
    Berechnet den proportionalen Verstärkungsfaktor (kP) basierend auf einer angepassten Funktion.
    Wendepunkte und Steigung können durch das EMG-Signal beeinflusst werden.

    Args:
        kP0 (float): Maximale kP-Wert in der Mitte der Verteilung.
        position (float): Aktuelle Position des Motors (in Radiant).
        range_max (float): Maximale Bewegungsreichweite des Motors (in Radiant).
        control_signal (float): EMG-Steuersignal, das die Stärke des Antriebs steuert (0 bis 1).
        sigma (float): Standardabweichung, Kontrolle der Breite der Verteilung.
        inflection_point_control (float): Steuerung der Wendepunkte durch EMG-Signal (0 bis 1).
        slope_control (float): Steuerung der Steigung durch EMG-Signal (0 bis 1).

    Returns:
        float: Berechneter kP-Wert.
    """
    # Berechne das Zentrum der Verteilung (mu) und skaliere es durch das Wendepunkt-Signal
    mu = (range_max / 2) * (1 + inflection_point_control)  # Anpassung für flexiblere Wendepunkte

    # Berechne die Steigung anhand des Steigungssteuerungssignals
    # Verwende eine sanfte Skalierung, um eine glattere Steigung zu gewährleisten
    if mu != 0:
        scaling_factor = (position / mu) ** slope_control
    else:
        scaling_factor = 0.0

    # Berechnung der kP-Funktion mit Wendepunkten und Steigungssteuerung
    exponent = - ((position - mu) ** 2) / (2 * sigma ** 2)
    gaussian_component = np.exp(exponent)

    # Berechnung des gewichteten kP-Werts unter Einbeziehung des EMG-Steuersignals
    kP_weighted = kP0 * scaling_factor * gaussian_component * control_signal

    # Optional: Begrenzung von kP_weighted auf einen minimalen Wert, um eine Mindestunterstützung zu gewährleisten
    kP_weighted = max(kP_weighted, 0.0)

    return kP_weighted

def handle_motor_params_custom_function(
    motor_controller,
    previous_kP_weighted,
    kP0=28.0,
    range_max=1.27,
    max_increase=1.3,
    max_decrease=5.0,
    deadband_threshold=0.3,
    sigma=0.2,
    inflection_point_control=0.5,
    slope_control=0.5
):
    """
    Aktualisiert die Motorparameter basierend auf einer angepassten Funktion für kP.
    Wendepunkte und Steigung werden dynamisch durch das EMG-Signal beeinflusst.

    Args:
        motor_controller (MotorController): Objekt zur Steuerung des Motors.
        previous_kP_weighted (float): Der vorherige kP_weighted-Wert.
        kP0 (float): Maximale kP-Wert in der Mitte der Verteilung.
        range_max (float): Maximale Bewegungsreichweite des Motors (in Radiant).
        max_increase (float): Maximale Erhöhung von kP_weighted pro Aufruf.
        max_decrease (float): Maximale Verringerung von kP_weighted pro Aufruf.
        deadband_threshold (float): Schwellenwert für den Deadband.
        sigma (float): Standardabweichung der Verteilung.
        inflection_point_control (float): Steuerung der Wendepunkte durch EMG-Signal (0 bis 1).
        slope_control (float): Steuerung der Steigung durch EMG-Signal (0 bis 1).

    Returns:
        float: Der aktualisierte kP_weighted-Wert.
    """
    status = motor_controller.get_motor_status(0)
    position = status["position"]
    
    # Holen der EMG-Steuersignale
    control_signal = motor_controller.control_signal
    #inflection_point_control = motor_controller.inflection_point_control  # Zusätzliche Steuerung
    #slope_control = motor_controller.slope_control  # Zusätzliche Steuerung
    
    # Optional: Negative Steuersignale auf 0 setzen
    if control_signal < 0:
        control_signal = 0.0
    
    print(f"Position: {position}, Control Signal: {control_signal}, Inflection Point Control: {inflection_point_control}, Slope Control: {slope_control}")
    
    # Berechne den neuen kP_weighted-Wert mit der benutzerdefinierten Funktion
    new_kP_weighted = calculate_kP_custom_function(
        kP0=kP0,
        position=position,
        range_max=range_max,
        control_signal=control_signal,
        sigma=sigma,
        inflection_point_control=inflection_point_control,
        slope_control=slope_control
    )
    
    # Berechne die Differenz für das Ramping
    delta_kP = new_kP_weighted - previous_kP_weighted
    
    # Asymmetrische Begrenzung: Maximale Erhöhung und Verringerung
    if delta_kP > max_increase:
        new_kP_weighted = previous_kP_weighted + max_increase
    elif delta_kP < -max_decrease:
        new_kP_weighted = previous_kP_weighted - max_decrease
    
    # Deadband-Logik: Wenn die Änderung klein ist, keine Aktualisierung
    if abs(new_kP_weighted - previous_kP_weighted) < deadband_threshold:
        new_kP_weighted = previous_kP_weighted
    
    # Sicherstellen, dass kP_weighted nicht negativ wird
    new_kP_weighted = max(new_kP_weighted, 0.0)
    
    # Aktualisiere die Motorparameter
    motor_controller.kp = new_kP_weighted
    motor_controller.kd = 0.0  # Falls gewünscht, kann auch kD angepasst werden
    
    print(f"Updated kP: {motor_controller.kp}, kD: {motor_controller.kd}")
    
    return new_kP_weighted

def handleSingleValueMessage(motor_controller, message):
    # multiple actual kP and kD values with weighing factors and message.value (e.g. EMG signal)
    motor_controller.control_signal = message.value
    #print("Control Signal: " + str(motor_controller.control_signal))
    if message.candle_mode == 1:
        # Impedance Mode
        motor_controller.set_impedance_controller_params(message.motor_no, motor_controller.kp, motor_controller.kd)
        #print("Impedance Mode")

def handleOnlyLoadCellMessage(motor_controller, message):
    # multiple actual kP and kD values with weighing factors and message.value (e.g. EMG signal)
    motor_controller.control_signal = message.value
    #print("Control Signal: " + str(motor_controller.control_signal))
    if message.candle_mode == 1:
        # Impedance Mode
        print(f"loadCellValue: {message.value}")
        motor_controller.set_target_torque(message.motor_no, message.value/100)
        # print("Impedance Mode")

def handleFlexCablesLoadCellMessage(motor_controller, message):
    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    tensionVal0 = -300
    tensionVal1 = -300
    targetTorque = 0.8
    upperLimit = 10
    lowerLimit = -10
    underTension0 = False
    underTension1 = False

#----------------------------------------------------------------------------------------------------logging functionality

    # path = 'dataAnalysis/logging.csv'
    
    # if os.path.exists(path) and os.path.getsize(path) > 0:
    #     # File exists and is non-empty; load it
    #     df = pd.read_csv(path)
    # else:
    #     # File doesn't exist or is empty; create an empty DataFrame with column names
    #     df = pd.DataFrame(columns=[
    #         'time','LoadCell0', 'LoadCell1',
    #         'motorTorque0', 'motorTorque1',
    #         'motorPosition0', 'motorPosition1'
    #     ])

    # new_row = {
    # 'time': time.time(),
    # 'LoadCell0': message.values[0],
    # 'LoadCell1': message.values[1],
    # 'motorTorque0': status0['torque'],
    # 'motorTorque1': status1['torque'],
    # 'motorPosition0': status0['position'],
    # 'motorPosition1': status1['position']
    # }

    # df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # df.to_csv(path, index=False)
#----------------------------------------------------------------------------------------------------


    if message.candle_mode == 1:
        # --------------------------------------------------------------------------------------------------------------------------handling load cell 1 value
        if message.values[0] > tensionVal0:    # --------------------------------------------------if load cell misses target tension
            if (status0["position"] < upperLimit and status0["position"] > lowerLimit):
                # motor_controller.set_target_velocity(0, )
                motor_controller.set_target_torque(0, targetTorque)
                motor_controller.set_impedance_controller_params(0, 0, 0.1)
            
            else:
                motor_controller.set_target_torque(0, 0)
                motor_controller.set_impedance_controller_params(0, 0, 0)
                print("Motor limit failure at motor0")

        else:   # ------------------------------------------------------------------------------if load cell reached target tension
            motor_controller.set_target_torque(0, 0)
            motor_controller.set_impedance_controller_params(0, 0, 0)
            underTension0 = True
            
        # print(f"loadCellValue1: {message.values[0]}")

        # --------------------------------------------------------------------------------------------------------------------------handling load cell 2 value
        if message.values[1] > tensionVal1:    # --------------------------------------------------if load cell misses target tension
            if (status1["position"] < upperLimit and status1["position"] > lowerLimit):
                motor_controller.set_target_torque(1, targetTorque)
                motor_controller.set_impedance_controller_params(1, 0, 0.1)

            else:
                motor_controller.set_target_torque(1, 0)
                motor_controller.set_impedance_controller_params(1, 0, 0)
                print("Motor limit failure at motor1")

        else:   # ------------------------------------------------------------------------------if load cell reached target tension
            motor_controller.set_target_torque(1, 0)
            motor_controller.set_impedance_controller_params(1, 0, 0)
            underTension1 = True
            
        # print(f"loadCellValue2: {message.values[1]}")
    
    else:
        raise ValueError("Candle mode is not set to 1")
    
    return underTension0 and underTension1

def handleFlexCables(motor_controller):
    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    torque0 = status0['torque']
    torque1 = status1['torque']
    print(f"Torque0: {torque0}, Torque1: {torque1}")
    targetTorque = 0.8
    torqueTolerance = 0.05
    underTension0 = False
    underTension1 = False

    motor_controller.set_impedance_controller_params(0, 0, 0)
    motor_controller.set_impedance_controller_params(1, 0, 0)

    # --------------------------------------------------------------------------------------------------------------------------handling motor 0
    if abs(torque0) < (targetTorque-(torqueTolerance*targetTorque)):    # --------------------------------------------------if motor misses target torque
        motor_controller.set_target_torque(0, -targetTorque)

    else:   # ------------------------------------------------------------------------------if motor reached target torque
        motor_controller.set_target_torque(0, 0)
        underTension0 = True
        
    # --------------------------------------------------------------------------------------------------------------------------handling motor 1
    if abs(torque1) < (targetTorque-(torqueTolerance*targetTorque)):    # --------------------------------------------------if motor misses target torque
        motor_controller.set_target_torque(1, targetTorque)

    else:   # ------------------------------------------------------------------------------if motor reached target torque
        motor_controller.set_target_torque(1, 0)
        underTension1 = True

    return underTension0 and underTension1

def handleKeepCableTension(motor_controller, base_torque, extendingMotorNo, flexingMotorNo, filtered_torque_ext, filtered_torque_flex):
    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    torque0 = status0['torque']
    torque1 = status1['torque']
    # print(f"Torque0: {torque0}, Torque1: {torque1}")
    #print(f"filtered_torque_ext: {filtered_torque_ext}  filtered_torque_flex: {filtered_torque_flex}")
    torqueTolerance = 0.05

    # --------------------------------------------------------------------------------------------------------------------------handling motor 0
    if abs(torque0) < (base_torque-(torqueTolerance*base_torque)):    # --------------------------------------------------if motor misses target torque
        motor_controller.set_target_torque(extendingMotorNo, base_torque)
        return base_torque, filtered_torque_flex # set filtered_torque_ext to base_torque
    # --------------------------------------------------------------------------------------------------------------------------handling motor 1
    if abs(torque1) < (base_torque-(torqueTolerance*base_torque)):    # --------------------------------------------------if motor misses target torque
        motor_controller.set_target_torque(flexingMotorNo, base_torque)
        return filtered_torque_ext, base_torque # set filtered_torque_flex to base_torque

    else:   # ------------------------------------------------------------------------------if motor reached target torque
        return filtered_torque_ext, filtered_torque_flex

def handleIsometric_lC(motor_controller, loadCellMessage, targetTorque, tensionVal, kp, kd, motor_no):
    status = motor_controller.get_motor_status(motor_no)
    upperLimit = 10
    lowerLimit = -10

#----------------------------------------------------------------------------------------------------logging functionality

    """path = f'dataAnalysis/paramsLogging{motor_no}.csv'
    
    if os.path.exists(path) and os.path.getsize(path) > 0:
        # File exists and is non-empty; load it
        df = pd.read_csv(path)
    else:
        # File doesn't exist or is empty; create an empty DataFrame with column names
        df = pd.DataFrame(columns=[
            'time','LoadCell0', 'LoadCell1',
            'motorTorque', 'motorPosition'
        ])

    new_row = {
    'time': time.time(),
    'LoadCell0': message.values[0],
    'LoadCell1': message.values[1],
    'motorTorque': status['torque'],
    'motorPosition': status['position']
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(path, index=False)"""
#----------------------------------------------------------------------------------------------------

    if loadCellMessage.values[motor_no] > tensionVal:    # --------------------------------------------------if load cell misses target tension
        if (status["position"] < upperLimit and status["position"] > lowerLimit):
            motor_controller.set_target_torque(motor_no, targetTorque)
            motor_controller.set_impedance_controller_params(motor_no, 0, 0.1)
        
        else:
            motor_controller.set_target_torque(motor_no, 0)
            motor_controller.set_impedance_controller_params(motor_no, 0, 0)
            print(f"Motor limit failure at motor {motor_no}")

    else:   # ------------------------------------------------------------------------------if load cell reached target tension
        motor_controller.set_target_position(motor_no, status["position"])
        motor_controller.set_target_velocity(motor_no, 0)
        motor_controller.set_target_torque(motor_no, 0)            
        motor_controller.set_impedance_controller_params(motor_no, kp, kd)
        
    # print(f"loadCellValue {motor_no}: {message.values[motor_no]}")

def handleWristExtension_lC(motor_controller, targetTorque, kp, kd):
    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    upperLimit = 10
    lowerLimit = -10

    # motor_controller.set_target_position(1, status0["position"] - 0.2)
    motor_controller.set_impedance_controller_params(0, 0, 0)
    motor_controller.set_impedance_controller_params(1, 0, 0)
    
    # motor_controller.set_target_torque(0, 0)
    # motor_controller.set_target_torque(0, targetTorque)    

    # if loadCellMessage.values[1] > tensionVal:    # --------------------------------------------------if load cell misses target tension
    #     if (status1["position"] < upperLimit and status1["position"] > lowerLimit):
    #         motor_controller.set_target_torque(1, targetTorque)
    #         motor_controller.set_impedance_controller_params(1, 0, 0.1)
        
    #     else:
    #         motor_controller.set_target_torque(1, 0)
    #         motor_controller.set_impedance_controller_params(1, 0, 0)
    #         print(f"Motor limit failure at motor 1")

    # else:   # ------------------------------------------------------------------------------if load cell reached target tension
    #     motor_controller.set_target_torque(1, 0)            
    #     motor_controller.set_impedance_controller_params(1, 0, 0)    

def handleWristFlexion_lC(motor_controller, targetTorque, kp, kd):
    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    upperLimit = 10
    lowerLimit = -10

    motor_controller.set_impedance_controller_params(0, 0, 0)
    motor_controller.set_impedance_controller_params(1, 0, 0)

    # motor_controller.set_target_position(0, status0["position"] + 0.2)
    # motor_controller.set_target_torque(1, targetTorque)
    # motor_controller.set_target_torque(1, 0)   

def run_wrist_exo_loadCell(motor_controller, loadcell_message, myo_message):
    """
    control logic of wrist exo suit using:
    - myo bracelet
    - load cell
    """

    status0 = motor_controller.get_motor_status(0)
    status1 = motor_controller.get_motor_status(1)
    tensionVal0 = -300
    tensionVal1 = -300
    targetTorque = 0.8
    upperLimit = 10
    lowerLimit = -10    

    if myo_message.candle_mode == 1:
        maximum = max(myo_message.values)
        index = myo_message.values.index(maximum)
        if maximum > 0.15:
            match index:
                case 0: # isometric hold
                    print("isometric hold")
                    # print(f"loadCell0: {loadcell_message.values[0]}")
                    # print(f"loadCell1: {loadcell_message.values[1]}")
                    handleIsometric_lC(motor_controller, loadcell_message, 0.8, -300, 10, 5, 0) # hardcoded for now
                    handleIsometric_lC(motor_controller, loadcell_message, 0.8, -300, 10, 5, 1)
                case 1: # extension
                    print("extension")
                    # handleWristExtension_lC(motor_controller, loadcell_message, 0.8, -300, 0, 0.1, 0) 
                    # handleWristExtension_lC(motor_controller, loadcell_message, 0, -300, 0, 0, 1)
                    handleWristExtension_lC(motor_controller, 0.8, 1, 0.1)
                case 2: # flexion
                    print("flexion")
                    # handleWristFlexion_lC(motor_controller, loadcell_message, 0, -300, 0, 0, 0)
                    # handleWristFlexion_lC(motor_controller, loadcell_message, 0.8, -300, 0, 0.1, 1)   
                    handleWristFlexion_lC(motor_controller, 0.8, 1, 0.1)
        else: # rest
            print("rest")
            handleFlexCablesLoadCellMessage(motor_controller, loadcell_message)

        # if myo_message.values[0] > 0.5: # isometric hold
        #     print("isometric hold")
        #     # print(f"loadCell0: {loadcell_message.values[0]}")
        #     # print(f"loadCell1: {loadcell_message.values[1]}")
        #     handleIsometric(motor_controller, loadcell_message, 0.8, -300, 10, 5, 0) # hardcoded for now
        #     handleIsometric(motor_controller, loadcell_message, 0.8, -300, 10, 5, 1)
        # elif myo_message.values[1] > 0.5: # extension
        #     print("extension")
        #     # handleWristExtension(motor_controller, loadcell_message, 0.8, -300, 0, 0.1, 0) 
        #     # handleWristExtension(motor_controller, loadcell_message, 0, -300, 0, 0, 1)
        #     handleWristExtension(motor_controller, 0.8, 1, 0.1)
        # elif myo_message.values[2] > 0.5: # flexion
        #     print("flexion")
        #     # handleWristFlexion(motor_controller, loadcell_message, 0, -300, 0, 0, 0)
        #     # handleWristFlexion(motor_controller, loadcell_message, 0.8, -300, 0, 0.1, 1)   
        #     handleWristFlexion(motor_controller, 0.8, 1, 0.1)          
        # else: # rest
        #     print("rest")
        #     handleFlexCablesLoadCellMessage(motor_controller, loadcell_message)

    else:
        raise ValueError("Candle mode is not set to 1")


def simple_run_wrist_exo(motor_controller, regression_value, config, last_mov):
    """
    simple control logic of wrist exo suit using:
    - myo bracelet
    """
    torque = 1.5

    extendingMotorNo = config["extendingMotorNo"]
    flexingMotorNo = config["flexingMotorNo"]
    extendingMotorNo = 0
    flexingMotorNo = 1

    motor_controller.set_impedance_controller_params(0, 0, 0) # temporary --> soon: emg based kp and kd values
    motor_controller.set_impedance_controller_params(1, 0, 0)    
    
    maximum = max(regression_value.values)
    index = regression_value.values.index(maximum)
    print(f"last mov: {last_mov}")
    if maximum > 0.15:
        match index:
            case 0: # isometric hold
                print("isometric hold")
                return "isometric"
            case 1: # extension
                print("extension")
                if last_mov == "flexion" or last_mov == "isometric":
                    motor_controller.set_target_torque(flexingMotorNo, 0)
                motor_controller.set_target_torque(extendingMotorNo, -torque) 
                return "extension"
            case 2: # flexion
                print("flexion")
                if last_mov == "extension" or last_mov == "isometric":
                    motor_controller.set_target_torque(extendingMotorNo, 0)
                motor_controller.set_target_torque(flexingMotorNo, torque)
                return "flexion"
    else: # rest
        print("rest")
        if last_mov == "extension" or last_mov == "flexion" or last_mov == "isometric":
                    motor_controller.set_target_torque(extendingMotorNo, 0) 
                    motor_controller.set_target_torque(flexingMotorNo, 0)
                    
        return "rest"
    
def handle_process_sensors(
        motor_controller, 
        myo_message, 
        current_avg_emg,
        ext_table, 
        flex_table, 
        iso_table,
        current_angle, 
        max_torque_extension, 
        max_torque_flexion, 
        base_torque, 
        min_torque_extension, 
        min_torque_flexion, 
        max_kp, 
        max_kd, 
        max_ext_angle, 
        max_flex_angle, 
        extendingMotorNo, 
        flexingMotorNo, 
        k, 
        filt_tau_ext, 
        filt_tau_flex, 
        alpha
        ):
    torque_ext_motor = motor_controller.get_motor_status(extendingMotorNo)["torque"]
    torque_flex_motor = motor_controller.get_motor_status(flexingMotorNo)["torque"]
    mov = classify_mov(myo_message)
    if mov == "isometric":
        if torque_ext_motor < min_torque_extension or torque_flex_motor < min_torque_flexion:
            filt_tau_ext = apply_IIR_filter(min_torque_extension, filt_tau_ext, alpha)
            filt_tau_flex = apply_IIR_filter(min_torque_flexion, filt_tau_flex, alpha)
            return "isometric", filt_tau_ext, filt_tau_flex, 0, 0
        kp, kd = isometric(current_avg_emg, iso_table, current_angle, max_flex_angle, max_ext_angle, max_kp, max_kd, k)
        return mov, filt_tau_ext, filt_tau_flex, kp, kd
    
    elif mov == "extension":
        target_tau_ext = extension(current_avg_emg, ext_table, current_angle, max_flex_angle, max_ext_angle, max_torque_extension, min_torque_extension, k)
        filt_tau_ext = apply_IIR_filter(target_tau_ext, filt_tau_ext, alpha)
        filt_tau_flex = base_torque
        return mov, filt_tau_ext, filt_tau_flex, 0, 0
    
    elif mov == "flexion":
        target_tau_flex = flexion(current_avg_emg, flex_table, current_angle, max_flex_angle, max_ext_angle, max_torque_flexion, min_torque_flexion, k)
        filt_tau_flex = apply_IIR_filter(target_tau_flex, filt_tau_flex, alpha)
        filt_tau_ext = base_torque
        return mov, filt_tau_ext, filt_tau_flex, 0, 0
    
    else:
        mov = "rest"
        return mov, base_torque, base_torque, 0, 0

def isometric(current_avg_emg, iso_table, current_angle, max_flex_angle, max_ext_angle, max_kp, max_kd, k):
    try: 
        a = current_avg_emg /iso_table[current_angle+max_flex_angle]
        kp = nonlinear_torque(a, max_kp, 0, k=k)
        kd = nonlinear_torque(a, max_kd, 0, k=k)            
    except: 
        warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
        kp = 0
        kd = 0
    return kp, kd

def extension(current_avg_emg, ext_table, current_angle, max_flex_angle, max_ext_angle, max_torque_extension, min_torque_extension, k):
    try: 
        a = current_avg_emg / ext_table[current_angle+max_flex_angle]
        target_tau_ext = nonlinear_torque(a, max_torque_extension, min_torque_extension, k=k)
    except:
        warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
        target_tau_ext = min_torque_extension
    return target_tau_ext

def flexion(current_avg_emg, flex_table, current_angle, max_flex_angle, max_ext_angle, max_torque_flexion, min_torque_flexion, k):
    try: 
        a = current_avg_emg / flex_table[current_angle+max_flex_angle]
        target_tau_flex = nonlinear_torque(a, max_torque_flexion, min_torque_flexion, k=k)
    except:
        warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
        target_tau_flex = min_torque_flexion
    return target_tau_flex


def classify_mov(myo_message):
    sorted_arr = sorted(myo_message.values, reverse=True)
    arg_max = sorted_arr[0]
    dif = arg_max - sorted_arr[1]
    index = myo_message.values.index(arg_max)
    if arg_max > 0.3 and dif > 0.1:
        match index:
            case 0:
                return "isometric"
            case 1:
                return "extension"
            case 2:
                return "flexion"    
    else:
        return "rest"

def run_wrist_exo(motor_controller, myo_message, current_avg_emg, ext_table, flex_table, iso_table, last_mov, current_angle, max_torque_extension, max_torque_flexion, min_torque, pre_torque_extension, pre_torque_flexion, max_kp, max_kd, max_ext_angle, max_flex_angle, extendingMotorNo, flexingMotorNo, k, filtered_torque_ext, filtered_torque_flex, alpha):
    """
    control logic of wrist exo suit using:
    - myo bracelet
    """
    # print(f"last mov: {last_mov}")
    # motor_controller.set_impedance_controller_params(0, 0, 0) # temporary --> soon: emg based kp and kd values
    # motor_controller.set_impedance_controller_params(1, 0, 0)
    #print(f"filtered_torque_ext: {filtered_torque_ext}  filtered_torque_flex: {filtered_torque_flex}")
    sorted_arr = sorted(myo_message.values, reverse=True)
    maximum = sorted_arr[0]
    dif = maximum - sorted_arr[1]
    index = myo_message.values.index(maximum)
    if maximum > 0.3 and dif > 0.1:
        match index:            
            case 0: # isometric hold
                try: rel_intensity = min(current_avg_emg / iso_table[current_angle+max_flex_angle], 1.0) 
                except: 
                    warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
                    rel_intensity = 0.3
                handleIsometric(motor_controller, pre_torque_extension, max_kp, max_kd, rel_intensity, last_mov, extendingMotorNo, extendingMotorNo, flexingMotorNo)
                handleIsometric(motor_controller, pre_torque_flexion, max_kp, max_kd, rel_intensity, last_mov, flexingMotorNo, extendingMotorNo, flexingMotorNo)
                return "isometric", filtered_torque_ext, filtered_torque_flex
            case 1: # extension                
                try: 
                    a = current_avg_emg / ext_table[current_angle+max_flex_angle]
                    targetTorque = nonlinear_torque(a, max_torque_extension, pre_torque_extension, k=k)
                except:
                    warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
                    targetTorque = pre_torque_extension                
                filtered_torque_ext = handleWristExtension(motor_controller, targetTorque, min_torque, extendingMotorNo, flexingMotorNo, last_mov, filtered_torque_ext, alpha)
                return "extension", filtered_torque_ext, filtered_torque_flex
            case 2: # flexion    
                try: 
                    a = current_avg_emg / flex_table[current_angle+max_flex_angle]
                    targetTorque = nonlinear_torque(a, max_torque_flexion, pre_torque_flexion, k=k)
                except:
                    warnings.warn(f"Angle {current_angle}° out of expected range [{max_flex_angle}°, {max_ext_angle}°]")
                    targetTorque = pre_torque_flexion       
                filtered_torque_flex = handleWristFlexion(motor_controller, targetTorque, min_torque, extendingMotorNo, flexingMotorNo, last_mov, filtered_torque_flex, alpha)
                return "flexion", filtered_torque_ext, filtered_torque_flex
    else:# rest
        if last_mov != "rest":
                motor_controller.set_target_torque(extendingMotorNo, min_torque) 
                motor_controller.set_target_torque(flexingMotorNo, min_torque)                        
        return "rest", min_torque, min_torque

def handleIsometric(motor_controller, pre_torque, max_kp, max_kd, rel_intensity, last_mov, motor_no, extendingMotorNo, flexingMotorNo):
    if last_mov != "isometric":
        motor_controller.set_target_torque(motor_no, 0)
    status = motor_controller.get_motor_status(motor_no)
    torque = status['torque']
    # print(f"rel_intensity: {rel_intensity}")
    
    if motor_no == extendingMotorNo:
        if abs(torque) < pre_torque:    # --------------------------------------------------if motor misses min torque --> set torque to min torque to pre tensen tendons
            motor_controller.set_impedance_controller_params(motor_no, 0, 0)
            motor_controller.set_target_torque(motor_no, pre_torque)
            
        else:   # ------------------------------------------------------------------------------if motor reaches min torque
            kp = rel_intensity * max_kp
            kd = rel_intensity * max_kd
            motor_controller.set_impedance_controller_params(motor_no, kp, kd)
            motor_controller.set_target_position(motor_no, status["position"])
            motor_controller.set_target_velocity(motor_no, 0)

    if motor_no == flexingMotorNo:
        if abs(torque) < pre_torque:    # --------------------------------------------------if motor misses min torque --> set torque to min torque to pre tensen tendons
            motor_controller.set_impedance_controller_params(motor_no, 0, 0)
            motor_controller.set_target_torque(motor_no, pre_torque)
            
        else:   # ------------------------------------------------------------------------------if motor reaches min torque
            kp = rel_intensity * max_kp
            kd = rel_intensity * max_kd
            motor_controller.set_impedance_controller_params(motor_no, kp, kd)
            motor_controller.set_target_position(motor_no, status["position"])
            motor_controller.set_target_velocity(motor_no, 0)           
        
def handleWristExtension(motor_controller, targetTorque, min_torque, extendingMotorNo, flexingMotorNo, last_mov, filtered_torque_ext, alpha):
    # print(f"rel_intensity: {rel_intensity}")
    if last_mov == "flexion" or last_mov == "isometric":
        motor_controller.set_impedance_controller_params(flexingMotorNo, 0, 0)
        motor_controller.set_impedance_controller_params(extendingMotorNo, 0, 0)
        motor_controller.set_target_torque(flexingMotorNo, min_torque)
    # motor_controller.set_target_torque(flexingMotorNo, 0)
    #  print(f"targetTorque0: {targetTorque}")
    filter_torque_ext = apply_IIR_filter(targetTorque, filtered_torque_ext, alpha)
    motor_controller.set_target_torque(extendingMotorNo, filter_torque_ext)
    return filter_torque_ext
    # motor_controller.set_target_torque(extendingMotorNo, targetTorque) 

def handleWristFlexion(motor_controller, targetTorque, min_torque, extendingMotorNo, flexingMotorNo, last_mov, filtered_torque_flex, alpha):
    # print(f"rel_intensity: {rel_intensity}")
    if last_mov == "extension" or last_mov == "isometric":
       motor_controller.set_impedance_controller_params(flexingMotorNo, 0, 0)
       motor_controller.set_impedance_controller_params(extendingMotorNo, 0, 0)
       motor_controller.set_target_torque(extendingMotorNo, min_torque)
    # motor_controller.set_target_torque(extendingMotorNo, 0)    
    # print(f"targetTorque1: {targetTorque}")
    filtered_torque_flex = apply_IIR_filter(targetTorque, filtered_torque_flex, alpha)
    motor_controller.set_target_torque(flexingMotorNo, filtered_torque_flex)
    return filtered_torque_flex
    # motor_controller.set_target_torque(flexingMotorNo, targetTorque)

def nonlinear_torque(a, tau_max, tau_kick, k=4):
    """
    k = 1 → gently convex
    k = 3 → mid-range boost
    k = 6 → rapidly rising near a=0.7, minimal output for small efforts
    (check Geogebra visualization)
    """
    # Ensure a is clipped to [0, 1]
    a = np.clip(a, 0, 1)
    # Exponential nonlinearity
    f = (np.exp(k * a) - 1) / (np.exp(k) - 1)
    return tau_kick + tau_max * f

def processIMU(IMU_message, IMU_No):
    # print(f"IMU_message{IMU_No}: {IMU_message.values}")
    return IMU_message.values[0:4]

def processIMUs(IMU_message):
    return IMU_message.values[0:4], IMU_message.values[4:8]

def normalize_quat(q):
    """Normalize a quaternion to unit length."""
    w, x, y, z = map(float, q)
    n = math.hypot(w, x, y, z)
    if n == 0:
        raise ValueError("Zero-norm quaternion")
    return (w/n, x/n, y/n, z/n)

def quat_conjugate(q):
    """Return the conjugate of a unit quaternion."""
    w, x, y, z = q
    return (w, -x, -y, -z)

def quat_multiply(q1, q2):
    """Hamilton product of two quaternions."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2
    )

# ---------- angle post-processing helpers ----------
def wrap_180(angle_deg: float) -> float:
    """Map any angle to (-180, +180]."""
    return (angle_deg + 180.0) % 360.0 - 180.0

def unwrap_angle(angle_deg: float, prev_deg: Optional[float]) -> float:
    """
    Continuously unwrap a stream of angles so that successive differences
    are never larger than 180° in magnitude.
    """
    if prev_deg is None:
        return angle_deg
    diff = angle_deg - prev_deg
    if diff > 180.0:
        angle_deg -= 360.0
    elif diff < -180.0:
        angle_deg += 360.0
    return angle_deg

# ---------- main API ----------
def signed_wrist_tilt(
    q_ref,
    q,
    tilt_axis="y",
    degrees=False,
    wrap=False,
    prev_unwrapped=None,
    log_all=False,
):
    """
    Compute signed wrist flexion (+) / extension (–) about a single local axis.
    Roll and yaw rotations do NOT affect the result.

    Parameters
    ----------
    q_ref : tuple of 4 floats (w, x, y, z)
        Reference quaternion. Will be normalized, and its scalar part forced ≥ 0.
    q : tuple of 4 floats (w, x, y, z)
        Current quaternion. Will be normalized.
    tilt_axis : 'x'/'y'/'z' or 3‐tuple of floats, default 'y'
        Local axis about which to compute signed tilt. If a string, one of
        'x', 'y', 'z' is used; otherwise a 3‐element vector is interpreted directly.
    degrees : bool, default False
        If True, return angle in degrees; otherwise, in radians.
    wrap : bool, default False
        If True, constrain output to (−180, +180] (if degrees) or (−π, +π] (if radians).
    prev_unwrapped : float or None, default None
        If provided, unwrap this angle relative to the previous value. Ignored if None.
    log_all : bool, default False
        If True, also return a DataFrame with ['w_rel', 'd'] for debugging.

    Returns
    -------
    float
        The signed tilt angle (in radians or degrees).
    (float, pandas.DataFrame)
        If log_all=True, returns (angle, DataFrame) where DataFrame has columns ['w_rel', 'd'].
    """

    # 1) Normalize reference quaternion, force scalar ≥ 0
    qr = normalize_quat(q_ref)
    if qr[0] < 0:
        qr = tuple(-comp for comp in qr)

    # 2) Inverse of reference quaternion
    q_ref_inv = quat_conjugate(qr)

    # 3) Normalize current quaternion
    qn = normalize_quat(q)

    # 4) Relative quaternion q_rel = q_ref_inv ⊗ qn (and normalize)
    q_rel = normalize_quat(quat_multiply(q_ref_inv, qn))
    w_rel, vx, vy, vz = q_rel

    # 5) Choose local axis
    if isinstance(tilt_axis, str):
        axis_map = {
            "x": (1.0, 0.0, 0.0),
            "y": (0.0, 1.0, 0.0),
            "z": (0.0, 0.0, 1.0),
        }
        unit_axis = axis_map[tilt_axis.lower()]
    else:
        unit_axis = tilt_axis  # expecting a 3‐element tuple

    # 6) Project vector part onto axis → d = sin(θ/2) * sign
    d = unit_axis[0] * vx + unit_axis[1] * vy + unit_axis[2] * vz

    # 7) Recover signed angle: θ = 2 * atan2(d, w_rel)
    theta = 2.0 * math.atan2(d, w_rel)

    # 8) Convert to degrees if requested
    if degrees:
        theta = math.degrees(theta)

    # 9) Optional wrap to (−π, +π] or (−180, +180]
    if wrap:
        theta = wrap_180(theta)

    # 10) Optional unwrap relative to prev_unwrapped
    if prev_unwrapped is not None:
        theta = unwrap_angle(theta, prev_unwrapped)

    # 11) If logging, return DataFrame as well
    if log_all:
        df = pd.DataFrame({"w_rel": [w_rel], "d": [d]})
        return theta, df

    return theta
   
def processMyo(myo_message):
    sorted_arr = sorted(myo_message.values, reverse=True)
    maximum = sorted_arr[0]
    dif = maximum - sorted_arr[1]
    index = myo_message.values.index(maximum)
    if maximum > 0.3 and dif > 0.1:
        match index:
            case 0: # isometric hold
                return "isometric"
            case 1: # extension
                return "extension"
            case 2: # flexion
                return "flexion"
    else: # rest
        return "rest"

def handlePrintMotorStatus(motor_controller, motor_no:list):
    torque_string = ""
    position_string = ""
    velocity_string = ""
    for i in motor_no:
        status = motor_controller.get_motor_status(i)
        torque_string += f"torque{i}: {status['torque']}, "
        position_string += f"position{i}: {status['position']}, "
        velocity_string += f"velocity{i}: {status['velocity']}, "
    print(torque_string+position_string+velocity_string)

def handleBroadcastMotorStatus(motor_controller, address, port, *motor_no):
    statusArray = []
    for motor in motor_no:
        status = motor_controller.get_motor_status(motor)
        statusArray.append(status['position'])
        statusArray.append(status['velocity'])
        statusArray.append(status['torque'])

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data = struct.pack(f'<{len(statusArray)}d', *statusArray)  # Little-endian Double-Werte
    try:
        udp_socket.sendto(data, (address, port))
    finally:
        udp_socket.close()

def handleBroadcastValues(address, port, *args):
    values = [val for val in args]

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data = struct.pack(f'<{len(values)}d', *values) # Little-endian Double-Werte
    try:
        udp_socket.sendto(data, (address, port))
    finally:
        udp_socket.close()

def handleBroadcastCurrentAngle(address, ui_port, imblocks_port, *args):
    values = [val for val in args]

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    data = struct.pack(f'<{len(values)}d', *values) # Little-endian Double-Werte
    try:
        udp_socket.sendto(data, (address, ui_port))
        udp_socket.sendto(data, (address, imblocks_port))
    finally:
        udp_socket.close()

def handleCheckMotorLimits(motor_controller, motor_no, lowerLimit, upperLimit):
    status = motor_controller.get_motor_status(motor_no)

    if status["position"] <= upperLimit:
        motor_controller.set_impedance_controller_params(motor_no, 0, 0)
        pass
    else:
        motor_controller.set_target_position(motor_no, upperLimit)
        motor_controller.set_impedance_controller_params(motor_no, 10, 0)
        print(f"upper limit failure at motor {motor_no}", status["position"], upperLimit, lowerLimit)    

    if status["position"] >= lowerLimit:
        motor_controller.set_impedance_controller_params(motor_no, 0, 0)
        pass
    else:
        motor_controller.set_target_position(motor_no, lowerLimit)
        motor_controller.set_impedance_controller_params(motor_no, 10, 0)
        print(f"lower limit failure at motor {motor_no}", status["position"], upperLimit, lowerLimit)

def handleUpdateMessage(message):
    return message.values[8], message.values[2], message.values[3]

def apply_IIR_filter(target_value, filtered_value, alpha=0.1):
    filtered_value = alpha * target_value + (1-alpha) * filtered_value
    # print(filtered_value)
    return filtered_value




