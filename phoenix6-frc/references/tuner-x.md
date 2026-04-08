# Phoenix Tuner X & Swerve Generator Reference

---

## 1. Phoenix Tuner X Overview

Phoenix Tuner X is the official CTRE companion app for configuring, updating, and diagnosing all Phoenix 6 devices.

**Platforms:**
- Desktop: Windows 10/11 (Microsoft Store), macOS 12.0+
- Mobile: iOS 15.0+, Android 8.0+

**Connection methods:**
| Method | Use case |
|--------|----------|
| USB direct | Bench setup, initial firmware flash |
| WiFi / Ethernet (robot) | On-field diagnostics, competition use |
| CANivore USB | CANivore-connected devices without robot network |

---

## 2. Key Features

| Feature | What it does |
|---------|--------------|
| **Firmware Update** | Batch-update all CTRE devices on the CAN bus to latest firmware |
| **Device Config** | Set CAN IDs, view/set device-level configs (via canbus or USB) |
| **Self-Test** | Snapshot of all faults, sensor values, firmware version — share with CTRE support |
| **Signal Logging** | Record live CAN signals to `.hoot` file for post-match analysis in Tuner X |
| **Plotter** | Real-time graph of any StatusSignal (position, velocity, current, etc.) |
| **Motor Control** | Manually command motors for bench testing (duty cycle, voltage, position, velocity) |
| **Swerve Generator** | GUI wizard → generates `TunerConstants.java` + `CommandSwerveDrivetrain.java` |
| **Elevator Generator** | GUI wizard → generates elevator mechanism constants |
| **Phoenix Diagnostic Server** | Automatically deployed to robot; enables Tuner X to connect over WiFi |

---

## 3. Swerve Generator — Configuration Workflow

Access via: **Mechanisms → Swerve** in Tuner X.

### Step 1: Assign CAN IDs
Each swerve module needs 3 devices. Standard naming:
```
Module       Drive ID   Steer ID   CANcoder ID
Front Left      1          2           3
Front Right     4          5           6
Back Left       7          8           9
Back Right     10         11          12
```
CAN IDs must be unique across the entire CAN bus.

### Step 2: Module Physical Setup
- Physically align all wheels to point **straight forward** (0°)
- Bevel gears must face **inward toward robot center** (this is required for standard MK4i/SDS modules)
- Do NOT plug in motors during calibration — use Tuner X alignment wizard

### Step 3: CANcoder Offset Calibration
- In Tuner X, use the alignment wizard per module
- It reads the current CANcoder absolute position and saves it as `MagnetOffset` in CANcoderConfiguration
- This offset is stored on the CANcoder itself AND written to TunerConstants

### Step 4: Physical Constants
| Parameter | Example | Notes |
|-----------|---------|-------|
| Wheel radius | 0.0508 m (2.0 in) | Measure actual worn wheel, not nominal |
| Drive gear ratio | 7.36 | MK4i L2; 6.12 for L1, 6.75 for SDS L3 |
| Steer gear ratio | 15.43 | MK4i (same for most SDS modules) |
| Coupling ratio | 3.82 | Steer-to-drive coupling factor (MK4i) |
| Module positions | (±X, ±Y) meters | From robot center to module center |

**Common gear ratios:**
| Module | Drive (L1/L2/L3) | Steer | Coupling |
|--------|-----------------|-------|----------|
| SDS MK4i | 8.14 / 6.75 / 6.12 | 21.43 | 0 |
| SDS MK4 | 8.14 / 6.75 / 6.12 | 12.8 | 0 |
| WCP SwerveX Micro | 7.36 / 6.12 | 15.43 | 3.82 |
| Swerve Drive Specialties Mk4 | varies | 12.8 | 0 |

**Note:** Coupling ratio = how many drive rotations occur per steer rotation due to the belt/chain inside the module. Non-zero only on some modules (WCP-style).

### Step 5: Motor Inverts
- Run the drive/steer validation in Tuner X — it commands each motor and verifies direction
- Tuner X sets inverts automatically based on validation results

### Step 6: Initial Gains
Tuner X pre-fills reasonable defaults. Teams usually tune drive kS/kV and leave steer PID alone initially:

```
Steer Slot 0 (position):  kP=100, kI=0, kD=0.5, kS=0.1, kV=1.91, kA=0
Drive Slot 0 (velocity):  kP=0.1, kI=0, kD=0,   kS=0,   kV=0.124, kA=0
```

### Step 7: Generate Code
- **Generate Project** — full project with TunerConstants + CommandSwerveDrivetrain (FRC only)
- **Generate only TunerConstants** — updates constants without overwriting subsystem code

Output file locations:
```
src/main/java/frc/robot/generated/TunerConstants.java
src/main/java/frc/robot/subsystems/CommandSwerveDrivetrain.java
```

---

## 4. TunerConstants.java — Structure

`TunerConstants.java` contains all hardware and tuning constants. Key fields:

```java
public class TunerConstants {
    // --- Physical constants ---
    public static final double kSpeedAt12Volts = 4.54; // m/s at 12V (used for scaling)

    // --- Per-module constants (example: Front Left) ---
    // CAN IDs
    public static final int kFrontLeftDriveMotorId = 1;
    public static final int kFrontLeftSteerMotorId = 2;
    public static final int kFrontLeftEncoderId = 3;

    // CANcoder offset (rotations) — set by Tuner X alignment wizard
    public static final Angle kFrontLeftEncoderOffset = Rotations.of(-0.123);

    // Motor inverts
    public static final InvertedValue kFrontLeftDriveMotorInverted = InvertedValue.CounterClockwise_Positive;
    public static final InvertedValue kFrontLeftSteerMotorInverted = InvertedValue.Clockwise_Positive;
    public static final SensorDirectionValue kFrontLeftEncoderInverted = SensorDirectionValue.CounterClockwise_Positive;

    // Module position (meters from robot center)
    public static final Translation2d kFrontLeftModuleOffset = new Translation2d(0.3, 0.3);

    // --- Drivetrain factory ---
    public static final CommandSwerveDrivetrain DriveTrain = createDrivetrain();
}
```

**Fields teams commonly modify post-generation:**
| Field | Why |
|-------|-----|
| `kSpeedAt12Volts` | After characterization (SysId); affects auto path scaling |
| Drive `kS`, `kV` | After SysId characterization run |
| Steer `kP` | Rarely needed — default 100 usually works |
| Module positions | If robot geometry changes |
| CANcoder offsets | After re-alignment |
| Current limits | Adjust to match breaker/thermal limits |

---

## 5. CommandSwerveDrivetrain.java — Key API

The generated `CommandSwerveDrivetrain` extends `SwerveDrivetrain` (CTRE swerve base) and implements `Subsystem`.

### Core Methods

```java
// Apply any SwerveRequest (use in commands/default command)
public Command applyRequest(Supplier<SwerveRequest> requestSupplier)

// Create PathPlanner AutoFactory (call once in RobotContainer)
public AutoFactory createAutoFactory()

// Follow a PathPlanner SwerveSample (called by AutoFactory internally)
public void followPath(SwerveSample sample)

// Add vision measurement to pose estimator
public void addVisionMeasurement(Pose2d visionRobotPose, double timestampSeconds)

// Sample pose at a specific timestamp (for vision latency compensation)
public Optional<Pose2d> samplePoseAt(double timestamp)

// SysId routines (steer and drive characterization)
public SysIdRoutine getSysIdRoutineTranslation()
public SysIdRoutine getSysIdRoutineSteer()
public SysIdRoutine getSysIdRoutineRotation()
```

### Built-in SwerveRequests (in `SwerveRequest` class)
```java
// Field-centric (recommended for teleop)
new SwerveRequest.FieldCentric()
    .withVelocityX(double metersPerSec)   // forward
    .withVelocityY(double metersPerSec)   // left
    .withRotationalRate(double radPerSec) // CCW positive

// Robot-centric
new SwerveRequest.RobotCentric()
    .withVelocityX(double metersPerSec)
    .withVelocityY(double metersPerSec)
    .withRotationalRate(double radPerSec)

// Field-centric with target heading
new SwerveRequest.FieldCentricFacingAngle()
    .withVelocityX(double)
    .withVelocityY(double)
    .withTargetDirection(Rotation2d heading)  // maintains heading with PID

// Point all wheels at an angle (lock wheels for pushing defense)
new SwerveRequest.PointWheelsAt()
    .withModuleDirection(Rotation2d direction)

// Brake (X-pattern lock)
new SwerveRequest.SwerveDriveBrake()

// Idle
new SwerveRequest.Idle()
```

### Simulation
```java
// Call in Robot.java or RobotContainer constructor
if (Utils.isSimulation()) {
    drivetrain.startSimThread();
}
```
The generated sim thread runs at **250 Hz** via `Notifier` (faster than robot periodic 50 Hz) for accurate closed-loop behavior.

---

## 6. RobotContainer Integration

```java
public class RobotContainer {
    // Instantiate from TunerConstants (do NOT call new CommandSwerveDrivetrain())
    private final CommandSwerveDrivetrain m_drivetrain = TunerConstants.DriveTrain;

    // Control requests as final fields
    private final SwerveRequest.FieldCentric m_drive = new SwerveRequest.FieldCentric()
        .withDeadband(TunerConstants.kSpeedAt12Volts * 0.1)
        .withRotationalDeadband(kMaxAngularRate * 0.1)
        .withDriveRequestType(DriveRequestType.OpenLoopVoltage);

    private final SwerveRequest.SwerveDriveBrake m_brake = new SwerveRequest.SwerveDriveBrake();

    public RobotContainer() {
        configureBindings();

        // PathPlanner AutoBuilder is configured automatically by CommandSwerveDrivetrain
        autoChooser = AutoBuilder.buildAutoChooser();
    }

    private void configureBindings() {
        m_drivetrain.setDefaultCommand(
            m_drivetrain.applyRequest(() ->
                m_drive
                    .withVelocityX(-m_joystick.getLeftY() * TunerConstants.kSpeedAt12Volts)
                    .withVelocityY(-m_joystick.getLeftX() * TunerConstants.kSpeedAt12Volts)
                    .withRotationalRate(-m_joystick.getRightX() * kMaxAngularRate)
            )
        );

        // X-lock on button press
        m_joystick.a().whileTrue(m_drivetrain.applyRequest(() -> m_brake));

        // Reset field-centric heading
        m_joystick.b().onTrue(m_drivetrain.runOnce(m_drivetrain::seedFieldCentric));
    }
}
```

---

## 7. Swerve Generator Gotchas

| Gotcha | Detail |
|--------|--------|
| **Bevel gear orientation** | Bevel gears must face toward robot center before running calibration wizard. Wrong orientation = 180° steer error. |
| **Coupling ratio matters** | WCP-style modules have mechanical coupling: steering motor rotates the drive axle slightly. Non-zero coupling ratio corrects odometry. SDS MK4i = 0. |
| **Don't call `new CommandSwerveDrivetrain()`** | Always use `TunerConstants.DriveTrain` — the generator configures the factory method. |
| **Steer kP=100 is intentional** | High proportional gain for steer is normal. Reducing it causes swerve modules to lag and drift. |
| **Sim runs at 250 Hz** | The Notifier-based sim loop is faster than robot periodic. Don't add your own sim calls in `simulationPeriodic()` for swerve. |
| **Re-generate only TunerConstants** | After re-calibrating encoders, use "Generate only TunerConstants" so your `CommandSwerveDrivetrain.java` edits aren't overwritten. |
| **Alliance color in periodic()** | Generated `periodic()` flips operator perspective when alliance is detected. Don't remove this — it makes red-alliance driving consistent. |
| **PathPlanner requires characterization** | For accurate autonomous, run SysId translation/rotation routines and update `kSpeedAt12Volts` and drive `kV` in TunerConstants. |
| **CANcoder offsets stored on device AND in code** | Offsets are written to the CANcoder AND stored in TunerConstants. If you swap a CANcoder, recalibrate and regenerate TunerConstants. |
