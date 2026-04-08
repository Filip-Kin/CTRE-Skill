# Phoenix 6 Code Patterns

Complete Java snippets for common FRC use cases. Import-free by design — add
your project's package/import declarations. Class names are exact Phoenix 6 API.

---

## Pattern 1: Subsystem Initialization (Full Template)

```java
// Fields
private final TalonFX m_motor = new TalonFX(1, "canivore");
private final TalonFXConfiguration m_cfg = new TalonFXConfiguration();

// Status signals — declare as fields, not local variables
private final StatusSignal<Angle>           m_pos  = m_motor.getPosition();
private final StatusSignal<AngularVelocity> m_vel  = m_motor.getVelocity();
private final StatusSignal<Current>         m_stator = m_motor.getStatorCurrent();

// Control requests — declare as fields, reuse in periodic
private final PositionVoltage m_posReq = new PositionVoltage(0).withSlot(0);

// Constructor / robotInit
private void configureMotor() {
    // Motor output
    m_cfg.MotorOutput.Inverted   = InvertedValue.CounterClockwise_Positive;
    m_cfg.MotorOutput.NeutralMode = NeutralModeValue.Brake;

    // Current limits
    m_cfg.CurrentLimits.StatorCurrentLimit       = 60;
    m_cfg.CurrentLimits.StatorCurrentLimitEnable = true;
    m_cfg.CurrentLimits.SupplyCurrentLimit        = 40;
    m_cfg.CurrentLimits.SupplyCurrentLimitEnable  = true;

    // Gear ratio (mechanism rotations per rotor rotation)
    m_cfg.Feedback.SensorToMechanismRatio = 10.71; // example: MK4i L2 drive

    // PID gains — Slot 0
    m_cfg.Slot0.kP = 1.0;
    m_cfg.Slot0.kI = 0.0;
    m_cfg.Slot0.kD = 0.05;
    m_cfg.Slot0.kV = 0.12;  // V/(rot/s)
    m_cfg.Slot0.kS = 0.25;  // V

    // Apply with retry
    StatusCode status = StatusCode.StatusCodeNotInitialized;
    for (int i = 0; i < 5; i++) {
        status = m_motor.getConfigurator().apply(m_cfg);
        if (status.isOK()) break;
    }
    if (!status.isOK()) {
        DriverStation.reportWarning("Motor config failed: " + status, false);
    }

    // Optimize CAN bus — disables unneeded signals
    BaseStatusSignal.setUpdateFrequencyForAll(50, m_pos, m_vel);
    BaseStatusSignal.setUpdateFrequencyForAll(10, m_stator);
    ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice // import com.ctre.phoenix6.hardware.ParentDevice
}

// periodic()
@Override
public void periodic() {
    BaseStatusSignal.refreshAll(m_pos, m_vel, m_stator);
}
```

---

## Pattern 2: Open-Loop Teleop Control

```java
// Field
private final DutyCycleOut m_dutyCycleReq = new DutyCycleOut(0);
private final VoltageOut    m_voltageReq   = new VoltageOut(0);

// Usage — duty cycle (-1 to +1)
m_motor.setControl(m_dutyCycleReq.withOutput(joystick.getLeftY()));

// Usage — voltage (preferred: consistent across battery levels)
m_motor.setControl(m_voltageReq.withOutput(joystick.getLeftY() * 12.0));

// Stop
m_motor.setControl(new NeutralOut());

// Note: EnableFOC = true requires Phoenix Pro (Kraken X60 only, NOT Falcon 500)
m_motor.setControl(m_dutyCycleReq.withOutput(0.5).withEnableFOC(true));
```

---

## Pattern 3: Position Closed-Loop

```java
// Fields
private final TalonFX       m_motor  = new TalonFX(1);
private final PositionVoltage m_posReq = new PositionVoltage(0).withSlot(0);
private final StatusSignal<Angle> m_pos = m_motor.getPosition();

// Config (in constructor)
TalonFXConfiguration cfg = new TalonFXConfiguration();
cfg.Slot0.kP = 2.4;   // V/rot — increase until oscillation, then back off 50%
cfg.Slot0.kI = 0.0;   // start at 0
cfg.Slot0.kD = 0.1;   // V/(rot/s) — add to dampen overshoot
cfg.Slot0.kS = 0.25;  // V — overcome static friction
cfg.Slot0.kV = 0.0;   // typically 0 for position (no continuous velocity)
cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;

// Soft limits (optional but recommended)
cfg.SoftwareLimitSwitch.ForwardSoftLimitEnable    = true;
cfg.SoftwareLimitSwitch.ForwardSoftLimitThreshold  = 50.0; // max rotations
cfg.SoftwareLimitSwitch.ReverseSoftLimitEnable    = true;
cfg.SoftwareLimitSwitch.ReverseSoftLimitThreshold  = 0.0;

// Apply (with retry — see Pattern 1)
m_motor.getConfigurator().apply(cfg);
BaseStatusSignal.setUpdateFrequencyForAll(50, m_pos);
ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice

// periodic() — read position
BaseStatusSignal.refreshAll(m_pos);
double currentRotations = m_pos.getValueAsDouble();

// Command motor to position
public void setPosition(double targetRotations) {
    m_motor.setControl(m_posReq.withPosition(targetRotations));
}

// Check if at target (within tolerance)
public boolean atTarget(double targetRotations) {
    return Math.abs(m_pos.getValueAsDouble() - targetRotations) < 0.1;
}
```

---

## Pattern 4: Velocity Closed-Loop

```java
// Fields
private final TalonFX         m_motor  = new TalonFX(1);
private final VelocityVoltage m_velReq = new VelocityVoltage(0).withSlot(0);
private final StatusSignal<AngularVelocity> m_vel = m_motor.getVelocity();

// Config (in constructor)
TalonFXConfiguration cfg = new TalonFXConfiguration();
// kV starting point: 1 / (free speed in rot/s at 12V)
// Kraken X60 free speed ≈ 100 rot/s at motor, ~13.6 rot/s at mechanism (7.36:1)
// kV ≈ 12V / 100 rot/s = 0.12 V/(rot/s) at rotor
cfg.Slot0.kS = 0.25;   // V — overcome friction
cfg.Slot0.kV = 0.12;   // V/(rot/s) — feedforward dominates velocity control
cfg.Slot0.kP = 0.11;   // V/(rot/s) — small correction on top of kV
cfg.Slot0.kI = 0.0;
cfg.Slot0.kD = 0.0;    // D is rarely useful for velocity
cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;

m_motor.getConfigurator().apply(cfg);
BaseStatusSignal.setUpdateFrequencyForAll(50, m_vel);
ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice

// periodic()
BaseStatusSignal.refreshAll(m_vel);

// Set target velocity in mechanism rot/s
public void setVelocity(double targetRPS) {
    m_motor.setControl(m_velReq.withVelocity(targetRPS));
}

// Check velocity
public double getVelocityRPS() {
    return m_vel.getValueAsDouble();
}

// Flywheel example: two motors, same speed
private final TalonFX m_follower = new TalonFX(2);
// In constructor:
m_follower.setControl(new Follower(m_motor.getDeviceID(), MotorAlignmentValue.Aligned)); // same direction
```

---

## Pattern 5: Motion Magic (Trapezoidal / S-Curve Position)

```java
// Fields
private final TalonFX           m_motor = new TalonFX(1);
private final MotionMagicVoltage m_mmReq = new MotionMagicVoltage(0).withSlot(0);
private final StatusSignal<Angle>           m_pos = m_motor.getPosition();
private final StatusSignal<AngularVelocity> m_vel = m_motor.getVelocity();

// Config
TalonFXConfiguration cfg = new TalonFXConfiguration();

// Profile parameters (in mechanism units after gear ratio is applied)
cfg.MotionMagic.MotionMagicCruiseVelocity = 50.0;  // rot/s cruise
cfg.MotionMagic.MotionMagicAcceleration   = 100.0; // rot/s² accel
cfg.MotionMagic.MotionMagicJerk           = 0.0;   // rot/s³ (0 = trapezoid, >0 = S-curve)

// Gains — Slot 0
cfg.Slot0.kS = 0.25;   // V
cfg.Slot0.kV = 0.12;   // V/(rot/s) — must match motor free speed
cfg.Slot0.kA = 0.01;   // V/(rot/s²) — usually small
cfg.Slot0.kP = 4.8;    // V/rot — increase until slight overshoot, back off
cfg.Slot0.kD = 0.1;    // V/(rot/s) — dampen oscillation

// Gravity compensation (elevator example)
cfg.Slot0.kG = 0.5;                             // V to hold against gravity
cfg.Slot0.GravityType = GravityTypeValue.Elevator_Static;

// Gear ratio
cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;

// Soft limits
cfg.SoftwareLimitSwitch.ForwardSoftLimitEnable    = true;
cfg.SoftwareLimitSwitch.ForwardSoftLimitThreshold  = MAX_ROTATIONS;
cfg.SoftwareLimitSwitch.ReverseSoftLimitEnable    = true;
cfg.SoftwareLimitSwitch.ReverseSoftLimitThreshold  = 0.0;

// Apply, optimize
StatusCode status = StatusCode.StatusCodeNotInitialized;
for (int i = 0; i < 5; i++) {
    status = m_motor.getConfigurator().apply(cfg);
    if (status.isOK()) break;
}
BaseStatusSignal.setUpdateFrequencyForAll(50, m_pos, m_vel);
ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice

// periodic()
BaseStatusSignal.refreshAll(m_pos, m_vel);

// Command
public void setTarget(double rotations) {
    m_motor.setControl(m_mmReq.withPosition(rotations));
}

// At target check
public boolean atTarget(double target) {
    return Math.abs(m_pos.getValueAsDouble() - target) < 0.05; // 0.05 rot tolerance
}

// For arm (not elevator): use Arm_Cosine
cfg.Slot0.GravityType = GravityTypeValue.Arm_Cosine;
// kG × cos(mechanismPosition × 2π) is applied automatically — position=0 means horizontal
```

---

## Pattern 6: Follower Motor

```java
// Lead motor (full config applied to this one)
private final TalonFX m_lead     = new TalonFX(1);
// Follower motor (config only needed for current limits / invert if different)
private final TalonFX m_follower  = new TalonFX(2);

// Follower control request — set ONCE in constructor, not in periodic
// MotorAlignmentValue.Aligned  = same direction as leader
// MotorAlignmentValue.Opposed  = opposite direction (physically reversed motor)
// import com.ctre.phoenix6.signals.MotorAlignmentValue
private final Follower m_followerReq = new Follower(m_lead.getDeviceID(), MotorAlignmentValue.Aligned);

// Constructor
public MySubsystem() {
    // Configure lead motor normally...
    // (apply TalonFXConfiguration to m_lead)

    // Apply follower config (only current limits needed, no gains)
    TalonFXConfiguration followerCfg = new TalonFXConfiguration();
    followerCfg.CurrentLimits.StatorCurrentLimit       = 60;
    followerCfg.CurrentLimits.StatorCurrentLimitEnable = true;
    m_follower.getConfigurator().apply(followerCfg);

    // Set follower — this persists; no need to call again in periodic
    m_follower.setControl(m_followerReq);
}

// Leader is controlled normally; follower tracks automatically
public void setVoltage(double volts) {
    m_lead.setControl(new VoltageOut(volts));
}

// StrictFollower: ignores leader's InvertedValue — always physically follows
// Use when you've manually inverted one motor and want strict mirroring:
m_follower.setControl(new StrictFollower(m_lead.getDeviceID()));
```

---

## Pattern 7: CANcoder + Sensor Fusion (FusedCANcoder)

```java
// Devices
private final TalonFX  m_motor   = new TalonFX(1,  "canivore");
private final CANcoder m_encoder = new CANcoder(10, "canivore");

// Constructor
public void configure() {
    // --- CANcoder config ---
    CANcoderConfiguration encoderCfg = new CANcoderConfiguration();
    encoderCfg.MagnetSensor.SensorDirection = SensorDirectionValue.CounterClockwise_Positive;
    encoderCfg.MagnetSensor.AbsoluteSensorDiscontinuityPoint = 0.5; // ±0.5 range
    // MagnetOffset is set by Tuner X and stored on device — don't hardcode here
    // unless re-applying after a CANcoder swap:
    // encoderCfg.MagnetSensor.MagnetOffset = -0.123; // rotations

    StatusCode encoderStatus = StatusCode.StatusCodeNotInitialized;
    for (int i = 0; i < 5; i++) {
        encoderStatus = m_encoder.getConfigurator().apply(encoderCfg);
        if (encoderStatus.isOK()) break;
    }

    // --- TalonFX config with FusedCANcoder ---
    TalonFXConfiguration motorCfg = new TalonFXConfiguration();

    // Feedback: fuse CANcoder with rotor encoder (requires Phoenix Pro)
    motorCfg.Feedback.FeedbackSensorSource  = FeedbackSensorSourceValue.FusedCANcoder;
    motorCfg.Feedback.FeedbackRemoteSensorID = m_encoder.getDeviceID();
    // RotorToSensorRatio = rotor turns per CANcoder turn (= gear ratio between them)
    motorCfg.Feedback.RotorToSensorRatio    = ROTOR_TO_SENSOR_RATIO;
    // SensorToMechanismRatio = CANcoder turns per mechanism turn (often 1:1)
    motorCfg.Feedback.SensorToMechanismRatio = 1.0;

    // After this config, motor.getPosition() reports mechanism rotations
    // using the CANcoder's absolute position, fused with rotor velocity for accuracy

    motorCfg.Slot0.kP = 4.8;
    motorCfg.Slot0.kV = 0.12;
    motorCfg.Slot0.kS = 0.25;
    // ... rest of gains

    StatusCode motorStatus = StatusCode.StatusCodeNotInitialized;
    for (int i = 0; i < 5; i++) {
        motorStatus = m_motor.getConfigurator().apply(motorCfg);
        if (motorStatus.isOK()) break;
    }

    ParentDevice.optimizeBusUtilizationForAll(m_motor, m_encoder); // import com.ctre.phoenix6.hardware.ParentDevice
}

// Without Phoenix Pro — use RemoteCANcoder (free):
motorCfg.Feedback.FeedbackSensorSource = FeedbackSensorSourceValue.RemoteCANcoder;
// RemoteCANcoder uses CANcoder for absolute position only;
// velocity comes from rotor sensor (less accurate than FusedCANcoder)
```

---

## Pattern 8: Simulation (TalonFXSimState + DCMotorSim)

```java
// Fields
private final TalonFX m_motor = new TalonFX(1);

// Get sim state handle — call once, reuse
private final TalonFXSimState m_motorSim = m_motor.getSimState();

// WPILib physics simulation
// DCMotor: getKrakenX60Foc, getKrakenX60, getFalcon500Foc, getFalcon500
private final DCMotorSim m_physicsSim = new DCMotorSim(
    LinearSystemId.createDCMotorSystem(
        DCMotor.getKrakenX60Foc(1), // motor model (numMotors)
        0.001,                       // MOI in kg·m² — characterize or estimate
        GEAR_RATIO                   // gear ratio between rotor and mechanism
    ),
    DCMotor.getKrakenX60Foc(1)
);

// simulationPeriodic() — called automatically by WPILib when sim is active
@Override
public void simulationPeriodic() {
    // 1. Give sim state the current battery voltage
    m_motorSim.setSupplyVoltage(RobotController.getBatteryVoltage());

    // 2. Get the voltage the motor controller is applying
    double motorVoltage = m_motorSim.getMotorVoltage();

    // 3. Feed voltage into physics sim
    m_physicsSim.setInputVoltage(motorVoltage);

    // 4. Step physics simulation (0.020 = 20 ms loop period)
    m_physicsSim.update(0.020);

    // 5. Write physics results back to sim state
    // IMPORTANT: DCMotorSim returns mechanism-side values.
    // Multiply by GEAR_RATIO to get rotor-side values for setRawRotorPosition/setRotorVelocity.
    // (This is the opposite of the feedback config where SensorToMechanismRatio divides)
    m_motorSim.setRawRotorPosition(
        m_physicsSim.getAngularPositionRotations() * GEAR_RATIO
    );
    m_motorSim.setRotorVelocity(
        m_physicsSim.getAngularVelocityRPM() / 60.0 * GEAR_RATIO // RPM → rps × gear ratio
    );
}

// CANcoder sim (if using external encoder)
private final CANcoder m_encoder = new CANcoder(10);
private final CANcoderSimState m_encoderSim = m_encoder.getSimState();

// In simulationPeriodic():
m_encoderSim.setRawPosition(m_physicsSim.getAngularPositionRotations());
m_encoderSim.setVelocity(m_physicsSim.getAngularVelocityRPM() / 60.0);

// Pigeon2 sim
private final Pigeon2 m_pigeon = new Pigeon2(0);
private final Pigeon2SimState m_pigeonSim = m_pigeon.getSimState();

// In simulationPeriodic() (differential drive yaw example):
m_pigeonSim.setRawYaw(m_drivetrainSim.getHeading().getDegrees());
```

---

## Pattern 9b: TalonFXS with External Motor (NEO / Minion / Brushed)

```java
// TalonFXS — for motors NOT built into a CTRE housing (NEO, Minion, CIM, 775, etc.)
// Use TalonFXSConfiguration, NOT TalonFXConfiguration
private final TalonFXS m_motor = new TalonFXS(15); // or new TalonFXS(15, "canivore")

private void configure() {
    TalonFXSConfiguration cfg = new TalonFXSConfiguration();

    // REQUIRED: set motor type — default is Disabled and motor will not run
    // import com.ctre.phoenix6.signals.MotorArrangementValue
    cfg.Commutation.MotorArrangement = MotorArrangementValue.NEO_JST;      // REV NEO
    // cfg.Commutation.MotorArrangement = MotorArrangementValue.NEO550_JST; // REV NEO 550
    // cfg.Commutation.MotorArrangement = MotorArrangementValue.VORTEX_JST; // REV Vortex
    // cfg.Commutation.MotorArrangement = MotorArrangementValue.Minion_JST; // CTRE Minion
    // cfg.Commutation.MotorArrangement = MotorArrangementValue.Brushed_DC; // CIM, 775, BAG, etc.

    // All other config fields are the same as TalonFXConfiguration
    cfg.MotorOutput.Inverted   = InvertedValue.CounterClockwise_Positive;
    cfg.MotorOutput.NeutralMode = NeutralModeValue.Brake;

    cfg.CurrentLimits.StatorCurrentLimit       = 40;
    cfg.CurrentLimits.StatorCurrentLimitEnable = true;

    cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;

    cfg.Slot0.kP = 2.0;
    cfg.Slot0.kV = 0.18; // NEO free speed ~5676 RPM = ~94.6 rot/s → kV ≈ 12/94.6 ≈ 0.127
    cfg.Slot0.kS = 0.3;

    StatusCode status = StatusCode.StatusCodeNotInitialized;
    for (int i = 0; i < 5; i++) {
        status = m_motor.getConfigurator().apply(cfg);
        if (status.isOK()) break;
    }
    ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice
}

// Control is identical to TalonFX — same setControl(), same StatusSignal accessors
private final VelocityVoltage m_velReq = new VelocityVoltage(0).withSlot(0);

public void setVelocity(double rps) {
    m_motor.setControl(m_velReq.withVelocity(rps));
}
```

**Notes:**
- For brushed DC (`Brushed_DC`), also set `cfg.Commutation.BrushedMotorWiring` to select which leads to use
- kV for NEO ≈ 0.127 V/(rot/s); for CIM ≈ 0.25 V/(rot/s) — tune with SysId
- TalonSRX (Phoenix 5) is NOT the same as TalonFXS (Phoenix 6)

---

## Pattern 9: Multi-Slot Control (Voltage + TorqueCurrentFOC)

```java
// Use Slot 0 for voltage-based control (teleop/general)
// Use Slot 1 for TorqueCurrentFOC (precise force control, requires Pro)
TalonFXConfiguration cfg = new TalonFXConfiguration();

// Slot 0 — voltage
cfg.Slot0.kS = 0.25;   // V
cfg.Slot0.kV = 0.12;   // V/(rot/s)
cfg.Slot0.kP = 4.8;    // V/rot
cfg.Slot0.kD = 0.1;

// Slot 1 — torque current (FOC)
cfg.Slot1.kS = 5.0;    // A — more current needed to overcome friction
cfg.Slot1.kV = 0.0;    // A/(rot/s) — typically 0 for torque mode
cfg.Slot1.kP = 60.0;   // A/rot
cfg.Slot1.kD = 6.0;

// Voltage control (default teleop)
private final MotionMagicVoltage m_mmVoltage = new MotionMagicVoltage(0).withSlot(0);
m_motor.setControl(m_mmVoltage.withPosition(target));

// Torque current control (precise force application, e.g., end-game hang)
private final MotionMagicTorqueCurrentFOC m_mmTorque = new MotionMagicTorqueCurrentFOC(0).withSlot(1);
m_motor.setControl(m_mmTorque.withPosition(target));
```
