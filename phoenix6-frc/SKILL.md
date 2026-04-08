---
name: phoenix6-frc
description: >
  Use when writing or reviewing Java code that uses CTRE Phoenix 6 hardware
  (TalonFX, Kraken, Falcon, CANcoder, Pigeon2). Provides API patterns,
  configuration idioms, unit conventions, and Phoenix 5 migration gotchas.
  Load when the user mentions TalonFX, Kraken, Falcon, CANcoder, Pigeon2,
  MotionMagic, Phoenix 6, CTRE, or swerve drive in an FRC Java context.
metadata:
  version: "1.0.0"
  phoenix6_version: "26.1.x"
  frc_season: "2026"
license: MIT
---

# Phoenix 6 FRC Skill

CTRE Phoenix 6 Java reference for FRC teams. Always apply the gotchas below
before generating any code. Load reference files when you need exact field
names or full code patterns.

## Reference Files

| File | Load when you need… |
|------|---------------------|
| `references/phoenix6-api.md` | Exact field names, config class fields, method signatures, enums |
| `references/phoenix6-patterns.md` | Complete Java snippets: subsystem init, MotionMagic, sim, follower, swerve |
| `references/tuner-x.md` | Phoenix Tuner X features, Swerve Generator workflow, TunerConstants integration |

---

## Import Paths

All Phoenix 6 classes live under `com.ctre.phoenix6` (NOT `com.ctre.phoenix` — that is Phoenix 5).

| Category | Package |
|----------|---------|
| Hardware devices | `com.ctre.phoenix6.hardware` — `TalonFX`, `CANcoder`, `Pigeon2`, **`ParentDevice`** |
| Control requests | `com.ctre.phoenix6.controls` — `DutyCycleOut`, `PositionVoltage`, `Follower`, … |
| Configuration | `com.ctre.phoenix6.configs` — `TalonFXConfiguration`, `Slot0Configs`, … |
| Signal enums | `com.ctre.phoenix6.signals` — `InvertedValue`, `NeutralModeValue`, **`MotorAlignmentValue`**, … |
| Status signals | `com.ctre.phoenix6` — `StatusSignal`, `BaseStatusSignal` |
| Simulation | `com.ctre.phoenix6.sim` — `TalonFXSimState`, `CANcoderSimState`, … |
| Swerve mechanisms | `com.ctre.phoenix6.swerve` |

**Commonly forgotten imports:**
- `ParentDevice` → `com.ctre.phoenix6.hardware.ParentDevice`
- `MotorAlignmentValue` → `com.ctre.phoenix6.signals.MotorAlignmentValue`
- `BaseStatusSignal` → `com.ctre.phoenix6.BaseStatusSignal`
- `StatusCode` → `com.ctre.phoenix6.StatusCode`

---

## Top 15 Gotchas

### G-1: No configFactoryDefault()
```
WRONG: motor.configFactoryDefault();
RIGHT: TalonFXConfiguration cfg = new TalonFXConfiguration(); // already clean state
```
`new TalonFXConfiguration()` starts with all defaults. There is no factory reset call in Phoenix 6.

### G-2: No ControlMode Enum
```
WRONG: motor.set(ControlMode.PercentOutput, 0.5);
RIGHT: motor.setControl(new DutyCycleOut(0.5));
```
Phoenix 6 uses control request objects. All modes are separate classes in `com.ctre.phoenix6.controls`.

### G-3: Units Are Rotations, Not Degrees or Ticks
```
WRONG: motor.setControl(posReq.withPosition(90));   // assuming degrees
WRONG: motor.setControl(posReq.withPosition(18432)); // ticks (4096 * 4.5 rotations)
RIGHT: motor.setControl(posReq.withPosition(0.25));  // 0.25 rotations = 90°
```
- Position: **rotations** (1.0 = one full revolution)
- Velocity: **rotations per second** (rps)
- Acceleration: **rotations per second²**

### G-4: No getSelectedSensorPosition
```
WRONG: double ticks = motor.getSelectedSensorPosition();
RIGHT: double rotations = motor.getPosition().getValueAsDouble();
```
There are no ticks. All sensor values are in physical units (rotations, rps, amps, volts).

### G-5: No .follow() Method
```
WRONG: follower.follow(leader);
RIGHT: follower.setControl(new Follower(leader.getDeviceID(), MotorAlignmentValue.Aligned));
```
The second parameter is `MotorAlignmentValue` (an enum, NOT a boolean):
- `MotorAlignmentValue.Aligned` — follower spins the same direction as leader
- `MotorAlignmentValue.Opposed` — follower spins opposite (physically reversed motor)

Import: `com.ctre.phoenix6.signals.MotorAlignmentValue`

### G-6: Control Requests Must Be Final Fields
```
WRONG: // Inside periodic():
       motor.setControl(new PositionVoltage(targetPos));  // allocates every 20ms!

RIGHT: // As a class field:
       private final PositionVoltage m_posReq = new PositionVoltage(0).withSlot(0);
       // In periodic():
       motor.setControl(m_posReq.withPosition(targetPos));
```
Creating objects in `periodic()` causes GC pressure on the RoboRIO. Create once, mutate with builder methods.

### G-7: apply() Not configAll(), With Retry
```
WRONG: motor.configAll(cfg);
RIGHT:
  StatusCode status = StatusCode.StatusCodeNotInitialized;
  for (int i = 0; i < 5; i++) {
    status = motor.getConfigurator().apply(cfg);
    if (status.isOK()) break;
  }
```
`getConfigurator().apply()` is the Phoenix 6 config API. Always retry on CAN bus startup races.

### G-8: Gains Are in Slot Configs, Not the Control Request
```
WRONG: posReq.withkP(1.0);   // no such method
RIGHT:
  cfg.Slot0.kP = 1.0;
  cfg.Slot0.kD = 0.1;
  motor.getConfigurator().apply(cfg);
  motor.setControl(m_posReq.withSlot(0));
```
Gains live in `Slot0Configs` / `Slot1Configs` / `Slot2Configs` inside `TalonFXConfiguration`.

### G-9: Cache StatusSignals, Don't Re-Fetch in Periodic
```
WRONG: // Every periodic():
       double pos = motor.getPosition().getValueAsDouble(); // re-fetches!

RIGHT: // As fields:
       private final StatusSignal<Angle> m_pos = motor.getPosition();
       private final StatusSignal<AngularVelocity> m_vel = motor.getVelocity();
       // In periodic():
       BaseStatusSignal.refreshAll(m_pos, m_vel);
       double posRot = m_pos.getValueAsDouble();
```
`motor.getPosition()` allocates a signal object each call. Cache it once. Use `refreshAll()` to batch-update.

### G-10: Check StatusCode on apply()
```java
StatusCode status = motor.getConfigurator().apply(cfg);
if (!status.isOK()) {
  DriverStation.reportWarning("TalonFX config failed: " + status, false);
}
```
During `periodic()`, log failures but don't throw. During `robotInit()`, use the retry loop (see G-7).

### G-11: MotionMagic Parameters Are NOT in Slot Configs
```
WRONG: cfg.Slot0.MotionMagicCruiseVelocity = 50;  // field doesn't exist
RIGHT:
  cfg.MotionMagic.MotionMagicCruiseVelocity = 50; // rot/s
  cfg.MotionMagic.MotionMagicAcceleration = 100;  // rot/s²
  cfg.MotionMagic.MotionMagicJerk = 0;            // rot/s³ (0 = trapezoidal)
  cfg.Slot0.kP = 4.8;  // gains still go in Slot
```
`MotionMagic.*` and `Slot0.*` are sibling fields of `TalonFXConfiguration`.

### G-12: Gear Ratios Go in FeedbackConfigs
```java
// After this, motor.getPosition() reports mechanism rotations (e.g., wheel rotations)
cfg.Feedback.SensorToMechanismRatio = GEAR_RATIO;  // e.g., 10.71 for MK4i L2
// For external encoder (CANcoder):
cfg.Feedback.RotorToSensorRatio = GEAR_RATIO;
cfg.Feedback.FeedbackSensorSource = FeedbackSensorSourceValue.FusedCANcoder;
cfg.Feedback.FeedbackRemoteSensorID = cancoder.getDeviceID();
```
Don't manually divide/multiply by gear ratio everywhere. Configure it once in `FeedbackConfigs`.

### G-13: Simulation Uses SimState, Not PhysicsSim
```
WRONG: PhysicsSim.getInstance().addTalonFX(motor, 0.001);  // Phoenix 5 API
RIGHT:
  private final TalonFXSimState m_motorSim = motor.getSimState();
  // In simulationPeriodic():
  m_motorSim.setSupplyVoltage(RobotController.getBatteryVoltage());
  m_physicsSim.setInputVoltage(m_motorSim.getMotorVoltage());
  m_physicsSim.update(0.020);
  m_motorSim.setRawRotorPosition(m_physicsSim.getAngularPositionRotations() * GEAR_RATIO);
  m_motorSim.setRotorVelocity(m_physicsSim.getAngularVelocityRPM() / 60.0 * GEAR_RATIO);
```
`PhysicsSim` is Phoenix 5. Phoenix 6 uses `motor.getSimState()` → `TalonFXSimState`.

### G-14: kV Units Depend on Control Mode
- **Voltage-based** (`PositionVoltage`, `VelocityVoltage`, `MotionMagicVoltage`): `kV` in **V/(rot/s)**
- **TorqueCurrentFOC** (`VelocityTorqueCurrentFOC`, etc.): set `kV = 0`; torque directly accelerates the rotor
- **kS** for voltage = volts to overcome friction; for torque = amps

### G-15: Inversion Is a Config, Not a Runtime Call
```
WRONG: motor.setInverted(true);
RIGHT:
  cfg.MotorOutput.Inverted = InvertedValue.Clockwise_Positive;
  motor.getConfigurator().apply(cfg);
```
Apply inversion in `TalonFXConfiguration.MotorOutput.Inverted` at init. `InvertedValue.CounterClockwise_Positive` is the default (positive output = CCW when looking at shaft).

---

## Quick-Reference Cheat Sheet

### Minimal Subsystem Skeleton
```java
public class MySubsystem extends SubsystemBase {
    private final TalonFX m_motor = new TalonFX(0, "canivore");
    private final TalonFXConfiguration m_cfg = new TalonFXConfiguration();

    // Cache control requests as final fields
    private final PositionVoltage m_posReq = new PositionVoltage(0).withSlot(0);

    // Cache status signals as final fields
    private final StatusSignal<Angle> m_pos = m_motor.getPosition();
    private final StatusSignal<AngularVelocity> m_vel = m_motor.getVelocity();

    public MySubsystem() {
        m_cfg.MotorOutput.Inverted = InvertedValue.CounterClockwise_Positive;
        m_cfg.MotorOutput.NeutralMode = NeutralModeValue.Brake;
        m_cfg.CurrentLimits.StatorCurrentLimit = 60;
        m_cfg.CurrentLimits.StatorCurrentLimitEnable = true;
        m_cfg.Slot0.kP = 1.0;
        m_cfg.Slot0.kD = 0.05;

        StatusCode status = StatusCode.StatusCodeNotInitialized;
        for (int i = 0; i < 5; i++) {
            status = m_motor.getConfigurator().apply(m_cfg);
            if (status.isOK()) break;
        }
        BaseStatusSignal.setUpdateFrequencyForAll(50, m_pos, m_vel);
        ParentDevice.optimizeBusUtilizationForAll(m_motor); // import com.ctre.phoenix6.hardware.ParentDevice
    }

    @Override
    public void periodic() {
        BaseStatusSignal.refreshAll(m_pos, m_vel);
    }

    public void setPosition(double rotations) {
        m_motor.setControl(m_posReq.withPosition(rotations));
    }

    public double getPositionRotations() {
        return m_pos.getValueAsDouble();
    }
}
```

### Control Request One-Liners
```java
// Open loop
motor.setControl(new DutyCycleOut(0.5));           // 50% output
motor.setControl(new VoltageOut(6.0));             // 6 V

// Closed loop — use pre-created final field + builder
motor.setControl(m_posReq.withPosition(10.0));     // 10 rotations
motor.setControl(m_velReq.withVelocity(20.0));     // 20 rot/s
motor.setControl(m_mmReq.withPosition(10.0));      // Motion Magic to 10 rot

// Follower
follower.setControl(new Follower(leader.getDeviceID(), MotorAlignmentValue.Aligned));  // or Opposed

// Stop
motor.setControl(new NeutralOut());
motor.setControl(new StaticBrake());
```

### Config Apply Retry (copy-paste)
```java
StatusCode status = StatusCode.StatusCodeNotInitialized;
for (int i = 0; i < 5; i++) {
    status = motor.getConfigurator().apply(cfg);
    if (status.isOK()) break;
}
if (!status.isOK()) {
    DriverStation.reportWarning("Motor " + motor.getDeviceID() + " config failed: " + status, false);
}
```

### StatusSignal Read Pattern
```java
// Declare as fields:
private final StatusSignal<Angle> m_pos = motor.getPosition();
private final StatusSignal<AngularVelocity> m_vel = motor.getVelocity();

// In periodic():
BaseStatusSignal.refreshAll(m_pos, m_vel);
double posRot = m_pos.getValueAsDouble();   // rotations
double velRps = m_vel.getValueAsDouble();   // rotations per second

// Latency-compensated position (useful for swerve odometry):
double compPos = BaseStatusSignal.getLatencyCompensatedValue(m_pos, m_vel).in(Rotations);
```

---

## Gain Tuning Reference

| Gain | Voltage Ctrl Unit | Torque Ctrl Unit | Purpose |
|------|-------------------|------------------|---------|
| `kP` | V / rot | A / rot | Proportional error correction |
| `kI` | V / (rot·s) | A / (rot·s) | Eliminate steady-state error |
| `kD` | V / (rot/s) | A / (rot/s) | Velocity damping, reduce overshoot |
| `kV` | V / (rot/s) | ~0 | Velocity feedforward (set = 1/maxVelocity for motors) |
| `kS` | V | A | Overcome static friction |
| `kA` | V / (rot/s²) | A / (rot/s²) | Acceleration feedforward |
| `kG` | V | A | Gravity feedforward (elevator=constant, arm=cosine) |

`kG` requires setting `GravityType` in `Slot0Configs`:
- `GravityTypeValue.Elevator_Static` — constant gravity compensation
- `GravityTypeValue.Arm_Cosine` — cosine-scaled (arm angle from horizontal)

**Typical FRC starting points (Kraken X60, voltage control):**
- kS ≈ 0.25 V, kV ≈ 0.12 V/(rot/s), kP start low and increase

---

## Device Constructors

```java
// TalonFX
new TalonFX(int deviceId)                    // CAN bus = "rio"
new TalonFX(int deviceId, String canbus)     // e.g., "canivore"
new TalonFX(int deviceId, CANBus canbus)     // preferred for CANivore objects

// CANcoder
new CANcoder(int deviceId)
new CANcoder(int deviceId, String canbus)

// Pigeon2
new Pigeon2(int deviceId)
new Pigeon2(int deviceId, String canbus)
```

**Note:** String canbus overload is deprecated (removal planned 2027). Prefer `CANBus` object for CANivore:
```java
private static final CANBus kCANivore = new CANBus("canivore");
private final TalonFX m_motor = new TalonFX(1, kCANivore);
```

---

## Common StatusSignal Accessors

| Signal | Method | Unit |
|--------|--------|------|
| Rotor/mechanism position | `motor.getPosition()` | rotations |
| Rotor/mechanism velocity | `motor.getVelocity()` | rot/s |
| Rotor acceleration | `motor.getAcceleration()` | rot/s² |
| Applied motor voltage | `motor.getMotorVoltage()` | V |
| Supply (battery) voltage | `motor.getSupplyVoltage()` | V |
| Stator current | `motor.getStatorCurrent()` | A |
| Supply current | `motor.getSupplyCurrent()` | A |
| Device temperature | `motor.getDeviceTemp()` | °C |
| Closed-loop error | `motor.getClosedLoopError()` | rot or rot/s |
| Closed-loop output | `motor.getClosedLoopOutput()` | V or A |
| Closed-loop reference | `motor.getClosedLoopReference()` | rot or rot/s |
| Fault bits | `motor.getFault_Undervoltage()` etc. | boolean signal |
| CANcoder absolute pos | `cancoder.getAbsolutePosition()` | rotations |
| Pigeon2 yaw | `pigeon.getYaw()` | degrees |
| Pigeon2 pitch | `pigeon.getPitch()` | degrees |
| Pigeon2 roll | `pigeon.getRoll()` | degrees |

Call `.getValueAsDouble()` on any signal after refreshing it.
