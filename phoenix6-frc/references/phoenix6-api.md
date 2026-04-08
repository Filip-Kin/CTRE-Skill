# Phoenix 6 API Reference

Dense lookup tables. No prose. Verified against Phoenix 6 v26.1.x Javadoc.
Javadoc: https://api.ctr-electronics.com/phoenix6/stable/java/

---

## 1. TalonFXConfiguration Fields

`TalonFXConfiguration` contains these sub-configs as public fields (access with dot notation):

| Field | Type | Notes |
|-------|------|-------|
| `MotorOutput` | `MotorOutputConfigs` | Invert, neutral mode, deadband |
| `CurrentLimits` | `CurrentLimitsConfigs` | Stator/supply current limiting |
| `Voltage` | `VoltageConfigs` | Peak output, supply voltage filtering |
| `Torque` | `TorqueCurrentConfigs` | Peak torque current, deadband |
| `Feedback` | `FeedbackConfigs` | Sensor source, gear ratios |
| `OpenLoopRamps` | `OpenLoopRampsConfigs` | Ramp rates for open-loop modes |
| `ClosedLoopRamps` | `ClosedLoopRampsConfigs` | Ramp rates for closed-loop modes |
| `HardwareLimitSwitch` | `HardwareLimitSwitchConfigs` | Fwd/rev limit switch behavior |
| `SoftwareLimitSwitch` | `SoftwareLimitSwitchConfigs` | Software position limits |
| `MotionMagic` | `MotionMagicConfigs` | Cruise vel, accel, jerk, expo params |
| `CustomParams` | `CustomParamsConfigs` | Team-defined integer params |
| `ClosedLoopGeneral` | `ClosedLoopGeneralConfigs` | ContinuousWrap, etc. |
| `Slot0` | `Slot0Configs` | PID + FF gains for slot 0 |
| `Slot1` | `Slot1Configs` | PID + FF gains for slot 1 |
| `Slot2` | `Slot2Configs` | PID + FF gains for slot 2 |

---

## 2. MotorOutputConfigs

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `Inverted` | `InvertedValue` | `CounterClockwise_Positive` | Motor direction |
| `NeutralMode` | `NeutralModeValue` | `Coast` | Brake or Coast when neutral |
| `DutyCycleNeutralDeadband` | double | 0.0 | Minimum duty cycle to move (0–0.25) |
| `PeakForwardDutyCycle` | double | 1.0 | Max forward duty cycle (0–1) |
| `PeakReverseDutyCycle` | double | -1.0 | Max reverse duty cycle (-1–0) |

---

## 3. CurrentLimitsConfigs

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `StatorCurrentLimit` | double | 0 | Max stator current (A) |
| `StatorCurrentLimitEnable` | boolean | false | Enable stator limiting |
| `SupplyCurrentLimit` | double | 0 | Max supply current (A) |
| `SupplyCurrentLimitEnable` | boolean | false | Enable supply limiting |
| `SupplyCurrentLowerLimit` | double | 0 | Lower supply limit after timeout (A) |
| `SupplyCurrentLowerTime` | double | 0 | Seconds at SupplyCurrentLimit before stepping down |

**Typical FRC values:**
```java
cfg.CurrentLimits.StatorCurrentLimit = 60;
cfg.CurrentLimits.StatorCurrentLimitEnable = true;
cfg.CurrentLimits.SupplyCurrentLimit = 40;
cfg.CurrentLimits.SupplyCurrentLimitEnable = true;
```

---

## 4. Slot0Configs / Slot1Configs / Slot2Configs

All three classes have identical fields:

| Field | Type | Range | Unit (Voltage ctrl) | Description |
|-------|------|-------|---------------------|-------------|
| `kP` | double | 0–3.4e38 | V / rot | Proportional gain |
| `kI` | double | 0–3.4e38 | V / (rot·s) | Integral gain |
| `kD` | double | 0–3.4e38 | V / (rot/s) | Derivative gain |
| `kV` | double | 0–3.4e38 | V / (rot/s) | Velocity feedforward |
| `kS` | double | -128–127 | V | Static friction feedforward |
| `kA` | double | 0–3.4e38 | V / (rot/s²) | Acceleration feedforward |
| `kG` | double | -128–127 | V | Gravity feedforward |
| `GravityType` | `GravityTypeValue` | — | — | `Elevator_Static` or `Arm_Cosine` |
| `StaticFeedforwardSign` | `StaticFeedforwardSignValue` | — | — | `UseVelocitySign` (default) or `UseClosedLoopSign` |

---

## 5. MotionMagicConfigs

| Field | Type | Default | Unit | Description |
|-------|------|---------|------|-------------|
| `MotionMagicCruiseVelocity` | double | 0 | rot/s | 0 = use kV to determine |
| `MotionMagicAcceleration` | double | 0 | rot/s² | 0 = unlimited (not recommended) |
| `MotionMagicJerk` | double | 0 | rot/s³ | 0 = trapezoidal; >0 = S-curve |
| `MotionMagicExpo_kV` | double | 0 | V/(rot/s) | Expo profile velocity gain |
| `MotionMagicExpo_kA` | double | 0 | V/(rot/s²) | Expo profile accel gain |

Expo variants (`MotionMagicExpoVoltage` etc.) ignore CruiseVelocity and use kV/kA instead.

---

## 6. FeedbackConfigs

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `FeedbackSensorSource` | `FeedbackSensorSourceValue` | `RotorSensor` | Which sensor to use |
| `FeedbackRemoteSensorID` | int | 0 | CAN ID of remote CANcoder |
| `SensorToMechanismRatio` | double | 1.0 | Mechanism rotations per sensor rotation |
| `RotorToSensorRatio` | double | 1.0 | Sensor rotations per rotor rotation |
| `FeedbackRotorOffset` | double | 0 | Offset added to rotor position (rotations) |

**Usage:**
- Internal encoder only: `cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;`
- CANcoder sensor fusion: set `FeedbackSensorSource`, `FeedbackRemoteSensorID`, `RotorToSensorRatio`

---

## 7. SoftwareLimitSwitchConfigs

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ForwardSoftLimitEnable` | boolean | false | Enable forward limit |
| `ForwardSoftLimitThreshold` | double | 0 | Forward limit in mechanism rotations |
| `ReverseSoftLimitEnable` | boolean | false | Enable reverse limit |
| `ReverseSoftLimitThreshold` | double | 0 | Reverse limit in mechanism rotations |

---

## 8. OpenLoopRampsConfigs / ClosedLoopRampsConfigs

| Field | Type | Description |
|-------|------|-------------|
| `DutyCycleOpenLoopRampPeriod` | double | Seconds to ramp duty cycle 0→1 |
| `VoltageOpenLoopRampPeriod` | double | Seconds to ramp voltage output 0→max |
| `TorqueOpenLoopRampPeriod` | double | Seconds to ramp torque current 0→max |
| `DutyCycleClosedLoopRampPeriod` | double | (ClosedLoop) duty cycle ramp |
| `VoltageClosedLoopRampPeriod` | double | (ClosedLoop) voltage ramp |
| `TorqueClosedLoopRampPeriod` | double | (ClosedLoop) torque ramp |

---

## 9. CANcoderConfiguration Fields

`CANcoderConfiguration` has one sub-config:

**MagnetSensorConfigs** (`cfg.MagnetSensor`):

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `SensorDirection` | `SensorDirectionValue` | `CounterClockwise_Positive` | Positive direction |
| `AbsoluteSensorDiscontinuityPoint` | double | 0.5 | Wrap point in rotations (0.5 = ±0.5 range) |
| `MagnetOffset` | double | 0 | Offset in rotations (set via Tuner X) |

---

## 10. Control Request Classes

| Class | Type | Key `.with*()` Builder Methods |
|-------|------|-------------------------------|
| `DutyCycleOut` | Open loop | `.withOutput(double)`, `.withEnableFOC(bool)`, `.withOverrideBrakeDurNeutral(bool)` |
| `VoltageOut` | Open loop | `.withOutput(double)`, `.withEnableFOC(bool)` |
| `TorqueCurrentFOC` | Open loop | `.withOutput(double amps)`, `.withMaxAbsDutyCycle(double)` |
| `PositionDutyCycle` | Closed loop | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double)` |
| `PositionVoltage` | Closed loop | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double)`, `.withEnableFOC(bool)` |
| `PositionTorqueCurrentFOC` | Closed loop | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double amps)` |
| `VelocityDutyCycle` | Closed loop | `.withVelocity(double)`, `.withSlot(int)`, `.withFeedForward(double)`, `.withAcceleration(double)` |
| `VelocityVoltage` | Closed loop | `.withVelocity(double)`, `.withSlot(int)`, `.withFeedForward(double)`, `.withAcceleration(double)`, `.withEnableFOC(bool)` |
| `VelocityTorqueCurrentFOC` | Closed loop | `.withVelocity(double)`, `.withSlot(int)`, `.withFeedForward(double amps)` |
| `MotionMagicDutyCycle` | Profile | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double)` |
| `MotionMagicVoltage` | Profile | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double)`, `.withEnableFOC(bool)` |
| `MotionMagicTorqueCurrentFOC` | Profile | `.withPosition(double)`, `.withSlot(int)`, `.withFeedForward(double amps)` |
| `MotionMagicVelocityDutyCycle` | Profile | `.withVelocity(double)`, `.withSlot(int)` |
| `MotionMagicVelocityVoltage` | Profile | `.withVelocity(double)`, `.withSlot(int)`, `.withEnableFOC(bool)` |
| `MotionMagicVelocityTorqueCurrentFOC` | Profile | `.withVelocity(double)`, `.withSlot(int)` |
| `MotionMagicExpoDutyCycle` | Profile (expo) | `.withPosition(double)`, `.withSlot(int)` |
| `MotionMagicExpoVoltage` | Profile (expo) | `.withPosition(double)`, `.withSlot(int)`, `.withEnableFOC(bool)` |
| `MotionMagicExpoTorqueCurrentFOC` | Profile (expo) | `.withPosition(double)`, `.withSlot(int)` |
| `Follower` | Special | `new Follower(int LeaderID, MotorAlignmentValue alignment)` — `Aligned` or `Opposed`; import from `com.ctre.phoenix6.signals` |
| `StrictFollower` | Special | `new StrictFollower(int LeaderID)` — ignores leader's `InvertedValue`, always mirrors output |
| `NeutralOut` | Special | no params |
| `CoastOut` | Special | no params |
| `StaticBrake` | Special | no params — shorts leads for max braking |
| `EmptyControl` | Special | no params — leaves motor in last state |

All closed-loop and profile requests also support:
- `.withLimitForwardMotion(bool)` — respect hardware forward limit
- `.withLimitReverseMotion(bool)` — respect hardware reverse limit
- `.withIgnoreHardwareLimits(bool)` — override limits (use with caution)
- `.withUpdateFreqHz(double)` — control request CAN send rate (default: 100 Hz)

---

## 11. TalonFX StatusSignal Accessors

| Signal | Method | Unit |
|--------|--------|------|
| Position | `motor.getPosition()` | rotations |
| Velocity | `motor.getVelocity()` | rot/s |
| Acceleration | `motor.getAcceleration()` | rot/s² |
| Motor voltage | `motor.getMotorVoltage()` | V |
| Supply voltage | `motor.getSupplyVoltage()` | V |
| Stator current | `motor.getStatorCurrent()` | A |
| Supply current | `motor.getSupplyCurrent()` | A |
| Torque current | `motor.getTorqueCurrent()` | A |
| Device temp | `motor.getDeviceTemp()` | °C |
| Processor temp | `motor.getProcessorTemp()` | °C |
| Closed-loop error | `motor.getClosedLoopError()` | rot or rot/s |
| Closed-loop output | `motor.getClosedLoopOutput()` | V or A |
| Closed-loop reference | `motor.getClosedLoopReference()` | rot or rot/s |
| Closed-loop ref slope | `motor.getClosedLoopReferenceSlope()` | rot/s |
| Duty cycle | `motor.getDutyCycle()` | unitless (-1 to 1) |
| Bridge output | `motor.getBridgeOutput()` | percent |
| Rotor polarity | `motor.getAppliedRotorPolarity()` | `AppliedRotorPolarityValue` |
| Control mode | `motor.getControlMode()` | `ControlModeValue` |
| Fault: undervoltage | `motor.getFault_Undervoltage()` | boolean signal |
| Fault: boot during enable | `motor.getFault_BootDuringEnable()` | boolean signal |
| Sticky fault: hardware | `motor.getStickyFault_Hardware()` | boolean signal |

**CANcoder signals:**
| Signal | Method | Unit |
|--------|--------|------|
| Absolute position | `cancoder.getAbsolutePosition()` | rotations |
| Position | `cancoder.getPosition()` | rotations |
| Velocity | `cancoder.getVelocity()` | rot/s |
| Supply voltage | `cancoder.getSupplyVoltage()` | V |

**Pigeon2 signals:**
| Signal | Method | Unit |
|--------|--------|------|
| Yaw | `pigeon.getYaw()` | degrees |
| Pitch | `pigeon.getPitch()` | degrees |
| Roll | `pigeon.getRoll()` | degrees |
| Yaw rate | `pigeon.getAngularVelocityZWorld()` | deg/s |
| Quaternion W/X/Y/Z | `pigeon.getQuatW()` etc. | unitless |
| Gravity vector | `pigeon.getGravityVectorX()` etc. | g |

---

## 12. BaseStatusSignal Methods

```java
// Batch refresh (non-blocking, uses cached CAN data)
BaseStatusSignal.refreshAll(sig1, sig2, sig3, ...);

// Blocking batch wait (waits up to timeoutSec for fresh data on all signals)
StatusCode status = BaseStatusSignal.waitForAll(double timeoutSec, sig1, sig2, ...);

// Set CAN update frequency for multiple signals at once
BaseStatusSignal.setUpdateFrequencyForAll(double hz, sig1, sig2, ...);

// Latency-compensated value (adds vel × latency to position)
// Returns value in the signal's native unit type
var compensated = BaseStatusSignal.getLatencyCompensatedValue(posSignal, velSignal);

// Reduce bus utilization — disables all unneeded signals on devices
// import com.ctre.phoenix6.hardware.ParentDevice
ParentDevice.optimizeBusUtilizationForAll(device1, device2, ...);
ParentDevice.optimizeBusUtilizationForAll(double optimizedFreqHz, device1, device2, ...);
```

Individual signal methods:
```java
StatusSignal<Angle> sig = motor.getPosition();
sig.refresh();                        // non-blocking single refresh
sig.waitForUpdate(0.1);               // blocking single wait (100 ms timeout)
double val = sig.getValueAsDouble();  // raw double in native unit
Angle typed = sig.getValue();         // typed Measure<Angle>
```

---

## 13. FeedbackSensorSourceValue Enum

| Value | License | Description |
|-------|---------|-------------|
| `RotorSensor` | Free | Internal rotor encoder (default) |
| `RemoteCANcoder` | Free | CANcoder provides position; rotor used for velocity |
| `FusedCANcoder` | **Pro** | CANcoder fused with rotor for high-accuracy absolute position |
| `SyncCANcoder` | **Pro** | CANcoder syncs absolute position to rotor at startup |
| `RemotePigeon2_Yaw` | Free | Pigeon2 yaw as feedback source |
| `RemotePigeon2_Pitch` | Free | Pigeon2 pitch as feedback source |
| `RemotePigeon2_Roll` | Free | Pigeon2 roll as feedback source |

`FusedCANcoder` is the recommended choice when a CANcoder is available (requires Phoenix Pro license). `RemoteCANcoder` works without Pro but only uses CANcoder for absolute position initialization.

---

## 14. Key Signal Enums

### InvertedValue
```java
InvertedValue.CounterClockwise_Positive  // default: CCW = positive output
InvertedValue.Clockwise_Positive         // CW = positive output
```

### NeutralModeValue
```java
NeutralModeValue.Coast  // free-spin when no output (default)
NeutralModeValue.Brake  // short motor leads → resist motion
```

### GravityTypeValue
```java
GravityTypeValue.Elevator_Static  // constant kG regardless of position
GravityTypeValue.Arm_Cosine       // kG × cos(mechanismPosition × 2π)
```

### SensorDirectionValue (CANcoder)
```java
SensorDirectionValue.CounterClockwise_Positive  // default
SensorDirectionValue.Clockwise_Positive
```

### ForwardLimitValue / ReverseLimitValue
```java
ForwardLimitValue.Open    // limit switch not triggered
ForwardLimitValue.Closed  // limit switch triggered
```

### GravityTypeValue
```java
GravityTypeValue.Elevator_Static  // use for linear elevators
GravityTypeValue.Arm_Cosine       // use for rotating arms
```
