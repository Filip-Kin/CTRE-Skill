# WPILib Integration Reference

WPILib patterns that intersect directly with Phoenix 6 code: command structure,
SysId characterization, pose estimation, and units interop.

---

## 1. Command Factory Pattern (Subsystem API Design)

Expose subsystem actions as `Command` factory methods, not raw motor calls.
`RobotContainer` binds commands; subsystems never touch joysticks.

```java
public class ElevatorSubsystem extends SubsystemBase {
    private final TalonFX m_motor = new TalonFX(Constants.ElevatorConstants.kMotorID);
    private final MotionMagicVoltage m_mmReq = new MotionMagicVoltage(0).withSlot(0);
    private final VoltageOut m_voltageReq = new VoltageOut(0);

    // ---- Command factories ----

    /** Move to a fixed setpoint and hold there. */
    public Command moveToPosition(double rotations) {
        return run(() -> m_motor.setControl(m_mmReq.withPosition(rotations)))
               .withName("ElevatorToPos(" + rotations + ")");
    }

    /** Hold current position (use as default command). */
    public Command holdPosition() {
        return run(() -> m_motor.setControl(m_mmReq.withPosition(getPositionRotations())))
               .withName("ElevatorHold");
    }

    /** Idle — coast or brake per NeutralMode. */
    public Command stop() {
        return runOnce(() -> m_motor.setControl(new NeutralOut()))
               .withName("ElevatorStop");
    }

    // ---- Getters (used by commands and triggers) ----
    public double getPositionRotations() { return m_pos.getValueAsDouble(); }
    public boolean atGoal(double targetRot, double toleranceRot) {
        return Math.abs(getPositionRotations() - targetRot) < toleranceRot;
    }
}
```

**In RobotContainer:**
```java
m_elevator.setDefaultCommand(m_elevator.holdPosition());

m_operatorController.a()
    .onTrue(m_elevator.moveToPosition(ElevatorConstants.kScoringHeight));
m_operatorController.b()
    .onTrue(m_elevator.moveToPosition(ElevatorConstants.kStowHeight));
```

---

## 2. Trigger Bindings Quick Reference

```java
// Button held → command runs while held, cancels on release
controller.a().whileTrue(m_intake.run());

// Button pressed → command runs once (ignores release)
controller.b().onTrue(m_elevator.moveToPosition(target));

// Button released → command runs on release
controller.x().onFalse(m_claw.retract());

// Axis threshold trigger
new Trigger(() -> controller.getLeftTriggerAxis() > 0.1)
    .whileTrue(m_intake.runAtSpeed());

// Sensor-based trigger (e.g., beam break)
new Trigger(m_intake::hasPiece)
    .onTrue(m_intake.stop().andThen(m_elevator.moveToPosition(kScoringHeight)));

// Chaining commands
controller.y().onTrue(
    m_elevator.moveToPosition(kScoringHeight)
              .andThen(m_claw.open())
              .withTimeout(2.0)
);
```

---

## 3. SysId with TalonFX (Voltage Characterization)

WPILib SysId generates kS, kV, kA by driving the motor with known voltages and
recording position/velocity. Phoenix 6's `SignalLogger` writes directly to a
`.hoot` file — no WPILib log consumer needed.

### Subsystem additions

```java
// Extra field for SysId
private final VoltageOut m_voltageReq = new VoltageOut(0);

// Declare as a field (not local variable)
private final SysIdRoutine m_sysId = new SysIdRoutine(
    new SysIdRoutine.Config(
        null,          // ramp rate: default 1 V/s quasistatic
        Volts.of(7),   // step voltage for dynamic test (reduce if brownout risk)
        null,          // timeout: default 10s
        state -> SignalLogger.writeString("SysId_State", state.toString())
    ),
    new SysIdRoutine.Mechanism(
        volts -> m_motor.setControl(m_voltageReq.withOutput(volts.in(Volts))),
        null,          // no WPILib log — Phoenix SignalLogger handles it
        this
    )
);

// Expose as commands (bind in RobotContainer to controller buttons)
public Command sysIdQuasistatic(SysIdRoutine.Direction dir) {
    return m_sysId.quasistatic(dir);
}
public Command sysIdDynamic(SysIdRoutine.Direction dir) {
    return m_sysId.dynamic(dir);
}
```

### Required imports
```java
import static edu.wpi.first.units.Units.Volts;
import edu.wpi.first.wpilibj.sysid.SysIdRoutine;
import com.ctre.phoenix6.SignalLogger;
```

### RobotContainer wiring
```java
// Start/stop signal logger with robot enable/disable
new Trigger(RobotController::getUserButton)
    .onTrue(Commands.runOnce(SignalLogger::start))
    .onFalse(Commands.runOnce(SignalLogger::stop));

// Four test routines — bind to four controller buttons
m_driverController.a().whileTrue(m_elevator.sysIdQuasistatic(SysIdRoutine.Direction.kForward));
m_driverController.b().whileTrue(m_elevator.sysIdQuasistatic(SysIdRoutine.Direction.kReverse));
m_driverController.x().whileTrue(m_elevator.sysIdDynamic(SysIdRoutine.Direction.kForward));
m_driverController.y().whileTrue(m_elevator.sysIdDynamic(SysIdRoutine.Direction.kReverse));
```

### Procedure
1. Enable SignalLogger (press user button or enable robot)
2. Run all four routines in sequence (quasi-forward, quasi-reverse, dyn-forward, dyn-reverse)
3. Copy `.hoot` file from robot (or use Phoenix Tuner X's log download)
4. Open in WPILib SysId Analyzer → select "Elevator" or "Simple Motor" mechanism
5. Read off kS, kV, kA from the fit

### Notes
- For **drivebase** characterization, do one side at a time (left motors, then right motors)
- For **swerve**, CTRE provides a dedicated `SwerveRequest.SysIdSwerveTranslation` request
- The `.hoot` file stores at `~/SysId` on the RoboRIO by default
- Run quasistatic first (slower, safer) before dynamic

---

## 4. SwerveDrivePoseEstimator

`SwerveDrivePoseEstimator` fuses wheel odometry + vision. CTRE's generated
`CommandSwerveDrivetrain` already wraps this internally — use `addVisionMeasurement()`
to inject external pose corrections.

```java
// In CommandSwerveDrivetrain (or a separate vision subsystem that has a reference):
public void addVisionMeasurement(Pose2d visionPose, double timestampSeconds) {
    m_odometry.addVisionMeasurement(visionPose, timestampSeconds);
}

// With custom std devs (x meters, y meters, theta radians):
public void addVisionMeasurement(Pose2d visionPose, double timestampSeconds,
                                  Matrix<N3, N1> stdDevs) {
    m_odometry.addVisionMeasurement(visionPose, timestampSeconds, stdDevs);
}
```

**Typical std dev values:**

| Scenario | x/y stddev | θ stddev | Notes |
|----------|-----------|---------|-------|
| Close single tag, good conditions | 0.3 m | 0.5 rad | Trust moderately |
| Multiple tags | 0.1 m | 0.3 rad | Trust more |
| Far/single tag | 0.7 m | 9999 rad | Don't trust rotation |
| MegaTag2 (Limelight) | 0.7 m | 9999 rad | IMU handles rotation |

Use `VecBuilder.fill(x, y, theta)` for the matrix:
```java
addVisionMeasurement(pose, timestamp, VecBuilder.fill(0.3, 0.3, 9999999));
```

---

## 5. WPILib Units Library Interop

WPILib's `edu.wpi.first.units` package uses typed `Measure<>` objects.
Phoenix 6 `StatusSignal` returns doubles in SI-ish units (rotations, rot/s).

```java
// Convert Phoenix 6 signal → WPILib Measure
import static edu.wpi.first.units.Units.*;

double rotations = m_pos.getValueAsDouble();
Measure<Angle> angle = Rotations.of(rotations);
Measure<Angle> degrees = angle.in(Degrees);     // convert

double rps = m_vel.getValueAsDouble();
Measure<Velocity<Angle>> velocity = RotationsPerSecond.of(rps);
Measure<Velocity<Angle>> rpm = velocity.in(RPM);

// Convert WPILib Measure → double for Phoenix 6
Measure<Voltage> v = Volts.of(6.0);
m_motor.setControl(m_voltageReq.withOutput(v.in(Volts)));  // double
```

**Common unit conversions for FRC:**

| From | To | Formula |
|------|----|---------|
| rotations | degrees | `rot * 360` |
| rotations | radians | `rot * 2π` |
| rot/s | RPM | `rps * 60` |
| meters (linear) | rotations | `meters / (2π * wheelRadiusMeters)` |
| rotations (mechanism) | inches | `rot * gearRatio * (2π * wheelRadiusInches)` |

---

## 6. Command Composition Patterns

```java
// Sequential
Commands.sequence(
    m_elevator.moveToPosition(kScoringHeight),
    m_claw.open(),
    Commands.waitSeconds(0.5),
    m_claw.close(),
    m_elevator.moveToPosition(kStowHeight)
);

// Parallel (all must finish)
Commands.parallel(
    m_elevator.moveToPosition(kScoringHeight),
    m_arm.moveToAngle(kScoringAngle)
);

// Parallel race (first to finish cancels others)
Commands.race(
    m_intake.runUntilPieceDetected(),
    Commands.waitSeconds(3.0)  // timeout
);

// Deadline (first command sets timeout for group)
Commands.deadline(
    m_intake.runUntilPieceDetected(),  // deadline
    m_indexer.run()                     // runs until deadline finishes
);

// Conditional
Commands.either(
    m_elevator.moveToPosition(kHighGoal),
    m_elevator.moveToPosition(kLowGoal),
    () -> m_sensors.isFarFromTarget()
);
```
