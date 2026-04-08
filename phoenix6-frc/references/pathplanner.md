# PathPlanner Integration Reference

PathPlanner 2025 with WPILib command-based robots and CTRE's CommandSwerveDrivetrain.
Docs: https://pathplanner.dev/home.html

---

## 1. AutoBuilder with CTRE's CommandSwerveDrivetrain

CTRE's Tuner X-generated `CommandSwerveDrivetrain` includes a `configureAutoBuilder()`
method that you call once in the constructor. If your generated file doesn't include it,
add it:

```java
// Inside CommandSwerveDrivetrain constructor, after other setup:
configureAutoBuilder();

// ---- Add this method ----
private void configureAutoBuilder() {
    try {
        RobotConfig config = RobotConfig.fromGUISettings();
        AutoBuilder.configure(
            () -> getState().Pose,                          // pose supplier
            this::resetPose,                                // pose resetter
            () -> getState().Speeds,                        // robot-relative ChassisSpeeds
            (speeds, feedforwards) -> setControl(           // output consumer
                m_pathApplyRobotSpeeds
                    .withSpeeds(speeds)
                    .withWheelForceFeedforwardsX(feedforwards.robotRelativeForcesXNewtons())
                    .withWheelForceFeedforwardsY(feedforwards.robotRelativeForcesYNewtons())
            ),
            new PPHolonomicDriveController(
                new PIDConstants(10.0, 0.0, 0.0),  // translation PID
                new PIDConstants(7.0, 0.0, 0.0)    // rotation PID
            ),
            config,
            () -> DriverStation.getAlliance().orElse(Alliance.Blue) == Alliance.Red,
            this  // subsystem requirement
        );
    } catch (Exception ex) {
        DriverStation.reportError("AutoBuilder failed: " + ex.getMessage(), ex.getStackTrace());
    }
}

// Required field in CommandSwerveDrivetrain:
private final SwerveRequest.ApplyRobotSpeeds m_pathApplyRobotSpeeds =
    new SwerveRequest.ApplyRobotSpeeds();
```

**Required imports:**
```java
import com.pathplanner.lib.auto.AutoBuilder;
import com.pathplanner.lib.config.PIDConstants;
import com.pathplanner.lib.config.RobotConfig;
import com.pathplanner.lib.controllers.PPHolonomicDriveController;
import edu.wpi.first.wpilibj.DriverStation;
import edu.wpi.first.wpilibj.DriverStation.Alliance;
```

---

## 2. RobotConfig (GUI Settings)

`RobotConfig.fromGUISettings()` reads from `deploy/pathplanner/settings.json`,
which PathPlanner GUI auto-generates when you configure your robot. It contains:
- Robot mass, MOI
- Module positions and wheel radius
- Drive/steer gear ratios (verify these match TunerConstants!)
- Max module speed

If `fromGUISettings()` throws, the GUI config file is missing — open PathPlanner
and configure your robot in the GUI first.

---

## 3. NamedCommands — Register Before AutoBuilder

Named commands let PathPlanner trigger subsystem actions at waypoints.
**Register all named commands BEFORE calling `configureAutoBuilder()`** (or before
the first auto chooser build — registration order matters).

```java
// In RobotContainer constructor, BEFORE configureAutoBuilder():
NamedCommands.registerCommand("IntakeDeploy", m_intake.deploy());
NamedCommands.registerCommand("Shoot", m_shooter.shoot().withTimeout(1.0));
NamedCommands.registerCommand("ElevatorScore",
    m_elevator.moveToPosition(ElevatorConstants.kScoringHeight));
NamedCommands.registerCommand("ElevatorStow",
    m_elevator.moveToPosition(ElevatorConstants.kStowHeight));
```

Import: `import com.pathplanner.lib.auto.NamedCommands;`

---

## 4. Auto Chooser

```java
// In RobotContainer (after AutoBuilder is configured and NamedCommands registered):
private final SendableChooser<Command> m_autoChooser = AutoBuilder.buildAutoChooser();

// In constructor:
SmartDashboard.putData("Auto Chooser", m_autoChooser);

// In Robot.java autonomousInit():
m_autonomousCommand = m_robotContainer.getAutonomousCommand();
// or just: m_autoChooser.getSelected().schedule();
```

```java
// RobotContainer.java:
public Command getAutonomousCommand() {
    return m_autoChooser.getSelected();
}
```

---

## 5. Running a Named Path as a Command

```java
// Run a path by name (path file: deploy/pathplanner/paths/ScoreThenPickup.path)
Command auto = AutoBuilder.buildAuto("ScoreThenPickup");

// Or load just the path:
PathPlannerPath path = PathPlannerPath.fromPathFile("ScoreThenPickup");
Command followPath = AutoBuilder.followPath(path);
```

---

## 6. On-the-Fly Path Generation

Generate paths at runtime without pre-planning in the GUI:

```java
// From current pose to a target pose:
Pose2d currentPose = m_drivetrain.getState().Pose;
Pose2d targetPose = new Pose2d(3.0, 2.0, Rotation2d.fromDegrees(180));

PathConstraints constraints = new PathConstraints(
    3.0,  // max velocity m/s
    3.0,  // max acceleration m/s²
    Math.PI * 2,  // max angular velocity rad/s
    Math.PI * 4   // max angular acceleration rad/s²
);

Command pathCommand = AutoBuilder.pathfindToPose(targetPose, constraints);
```

**Pathfinding to a named path's start:**
```java
// Pathfind to start of "ScorePath", then follow it
Command command = AutoBuilder.pathfindThenFollowPath(
    PathPlannerPath.fromPathFile("ScorePath"),
    constraints
);
```

---

## 7. PID Tuning for AutoBuilder

The two `PIDConstants` in `PPHolonomicDriveController` control path tracking:

| Param | Controls | Starting Value | Tune if… |
|-------|----------|---------------|----------|
| Translation kP | How aggressively robot corrects x/y error | 5–10 | Robot oscillates → lower; robot lags → raise |
| Translation kI | Steady-state position error | 0 (usually) | Robot stops slightly off → small kI |
| Translation kD | Translation damping | 0 (usually) | |
| Rotation kP | How aggressively robot corrects heading error | 5–10 | Robot oscillates on turns → lower |
| Rotation kI/kD | Heading damping | 0 | |

**Common tuning failures:**
- Robot overshoots waypoints → translation kP too high
- Robot takes wide arcs on turns → rotation kP too low
- Robot wiggles along straight paths → translation kP too high or path time too aggressive

---

## 8. Gotchas

**G-P1: Register NamedCommands before AutoBuilder.configure()**
```
WRONG: configureAutoBuilder() first, then NamedCommands.registerCommand()
RIGHT: NamedCommands.registerCommand() first, then configureAutoBuilder()
```
Commands registered after `configure()` won't be found by path executor.

**G-P2: Alliance flip must be correct**
```
WRONG: () -> false  // always use blue-side paths
RIGHT: () -> DriverStation.getAlliance().orElse(Alliance.Blue) == Alliance.Red
```
PathPlanner mirrors paths for red alliance. If flip is wrong, robot drives off field.

**G-P3: RobotConfig gear ratios must match TunerConstants**
PathPlanner's wheel speed feedforward uses motor gear ratios from `settings.json`.
If they differ from TunerConstants, wheel force feedforwards are wrong. Verify both
are set to the same drive ratio (e.g., 6.122 for MK4i L2).

**G-P4: fromGUISettings() throws if settings.json is missing**
Wrap in try/catch (shown in Section 1). Failure to configure AutoBuilder silently
prevents all autos from running.

**G-P5: PathPlannerPath.fromPathFile() must match exact filename**
Path files live in `deploy/pathplanner/paths/*.path`. The string argument is the
filename without extension. Case-sensitive on Linux (RoboRIO).

**G-P6: ApplyRobotSpeeds vs ApplyChassisSpeeds**
PathPlanner outputs robot-relative `ChassisSpeeds`. Use `SwerveRequest.ApplyRobotSpeeds`
(not `ApplyChassisSpeeds`, which is field-relative) in the output consumer.

**G-P7: Wheel force feedforwards require correct motor type in RobotConfig**
PathPlanner uses feedforward based on motor model. Set the correct motor type
(Kraken X60, NEO, etc.) in the PathPlanner GUI → Robot Config → Drive Motor.

---

## 9. Choreo (Alternative to PathPlanner)

Choreo generates time-optimized trajectories (versus PathPlanner's spline paths).
Use Choreo when you need maximum speed precision — especially for multi-piece autos.

```java
// Choreo uses same AutoBuilder interface — configure once, use either:
ChoreoAutoFactory autoFactory = new ChoreoAutoFactory(
    () -> m_drivetrain.getState().Pose,
    m_drivetrain::resetPose,
    m_choreoController,  // ChoreoHolonomicController
    () -> DriverStation.getAlliance().orElse(Alliance.Blue) == Alliance.Red,
    new ChoreoAutoBindings(),
    this
);
```

PathPlanner and Choreo can coexist — use PathPlanner for short/dynamic paths,
Choreo for optimized prebuilt auto routines.
