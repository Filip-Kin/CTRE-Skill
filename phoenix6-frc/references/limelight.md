# Limelight Integration Reference

Limelight 2+/3/3G/4 NetworkTables API and MegaTag2 pose estimation.
Assumes LimelightHelpers.java from https://docs.limelightvision.io/docs/docs-limelight/apis/limelight-lib

---

## 1. NetworkTables Quick Reference

Default table name: `"limelight"`. Multiple limelights use custom names set in the web UI.

| NT Key | Type | Description |
|--------|------|-------------|
| `tv` | double | Valid target: 1 = has target, 0 = no target |
| `tx` | double | Horizontal angle to target (degrees, ±29.8° for LL3) |
| `ty` | double | Vertical angle to target (degrees) |
| `ta` | double | Target area (0–100% of image) |
| `tid` | double | AprilTag ID of primary in-view tag (-1 if none) |
| `tl` | double | Pipeline latency contribution (ms) |
| `cl` | double | Capture latency (ms) — add to `tl` for total latency |
| `pipeline` | double | Active pipeline index (write to switch) |
| `ledMode` | double | LED: 0=pipeline, 1=off, 2=blink, 3=on |
| `camMode` | double | 0=vision, 1=driver cam |
| `botpose_wpiblue` | double[] | Robot pose in WPILib field coords, blue origin: [x,y,z,roll,pitch,yaw,latency_ms] |
| `botpose_wpired` | double[] | Same, red origin |
| `botpose_orb_wpiblue` | double[] | MegaTag2 pose, blue origin (lower latency, more stable) |
| `robot_orientation_set` | double[] | Write: [yaw, yawRate, pitch, pitchRate, roll, rollRate] |

---

## 2. LimelightHelpers — Key Methods

Add `LimelightHelpers.java` to your project (single-file, no dependencies):
```
src/main/java/frc/robot/util/LimelightHelpers.java
```

```java
// Basic targeting
double tx = LimelightHelpers.getTX("limelight");           // horizontal angle
double ty = LimelightHelpers.getTY("limelight");           // vertical angle
boolean hasTarget = LimelightHelpers.getTV("limelight");   // valid target

// Pipeline control
LimelightHelpers.setPipelineIndex("limelight", 0);         // switch pipeline

// Pose estimation (MegaTag1)
Pose2d botPose = LimelightHelpers.getBotPose2d_wpiBlue("limelight");

// Pose estimation (MegaTag2) — preferred
LimelightHelpers.PoseEstimate mt2 =
    LimelightHelpers.getBotPoseEstimate_wpiBlue_MegaTag2("limelight");

// Set robot orientation for MegaTag2 (REQUIRED before reading MT2 pose)
LimelightHelpers.SetRobotOrientation("limelight",
    yawDegrees, 0,  // yaw, yaw rate
    0, 0,           // pitch, pitch rate
    0, 0);          // roll, roll rate
```

---

## 3. MegaTag2 Pose Estimation (Full Pattern)

MegaTag2 fuses AprilTag detections with the robot's IMU yaw for a stable 2D
pose estimate. **Must update robot orientation on every periodic loop** before
reading the pose estimate.

```java
// In your vision subsystem or drivetrain periodic():
public void updateVisionPose(SwerveDrivePoseEstimator poseEstimator, double yawDegrees) {
    // Step 1: tell Limelight where the robot is pointing (required for MT2)
    LimelightHelpers.SetRobotOrientation(
        "limelight",
        yawDegrees, 0,   // yaw (from Pigeon2 or NavX), yaw rate
        0, 0,            // pitch, pitch rate (usually 0 for ground robots)
        0, 0             // roll, roll rate
    );

    // Step 2: get MT2 estimate
    LimelightHelpers.PoseEstimate mt2 =
        LimelightHelpers.getBotPoseEstimate_wpiBlue_MegaTag2("limelight");

    // Step 3: reject bad estimates
    if (mt2 == null) return;
    if (mt2.tagCount == 0) return;                  // no tags visible
    if (mt2.pose.getX() == 0 && mt2.pose.getY() == 0) return; // degenerate
    // Optional: reject if robot is spinning fast (pose is unreliable)
    // if (Math.abs(m_gyro.getRate()) > 720) return; // degrees/s threshold

    // Step 4: inject into pose estimator
    // Large theta stddev = trust IMU for rotation, not vision
    poseEstimator.addVisionMeasurement(
        mt2.pose,
        mt2.timestampSeconds,
        VecBuilder.fill(0.7, 0.7, 9999999)
    );
}
```

**With CTRE's CommandSwerveDrivetrain:**
```java
// In periodic():
LimelightHelpers.SetRobotOrientation("limelight",
    m_drivetrain.getState().Pose.getRotation().getDegrees(), 0, 0, 0, 0, 0);

LimelightHelpers.PoseEstimate mt2 =
    LimelightHelpers.getBotPoseEstimate_wpiBlue_MegaTag2("limelight");

if (mt2 != null && mt2.tagCount >= 1) {
    m_drivetrain.addVisionMeasurement(mt2.pose, mt2.timestampSeconds,
        VecBuilder.fill(0.7, 0.7, 9999999));
}
```

---

## 4. PoseEstimate Fields

```java
LimelightHelpers.PoseEstimate mt2 = ...;

mt2.pose              // Pose2d — robot position in field coords
mt2.timestampSeconds  // double — already latency-compensated (use directly)
mt2.latency           // double — total latency in ms (informational)
mt2.tagCount          // int — number of tags contributing
mt2.tagSpan           // double — distance between outermost tags (m)
mt2.avgTagDist        // double — average distance to visible tags (m)
mt2.avgTagArea        // double — average tag area (% image)
mt2.rawFiducials      // RawFiducial[] — per-tag details
```

---

## 5. Raw NetworkTables (No LimelightHelpers)

```java
import edu.wpi.first.networktables.NetworkTable;
import edu.wpi.first.networktables.NetworkTableInstance;

NetworkTable table = NetworkTableInstance.getDefault().getTable("limelight");

double tx = table.getEntry("tx").getDouble(0.0);
boolean hasTarget = table.getEntry("tv").getDouble(0.0) == 1.0;

// Switch pipeline
table.getEntry("pipeline").setNumber(1);

// Get botpose_orb_wpiblue (MT2) manually
double[] botPoseRaw = table.getEntry("botpose_orb_wpiblue").getDoubleArray(new double[7]);
// [0]=x, [1]=y, [2]=z, [3]=roll, [4]=pitch, [5]=yaw, [6]=total_latency_ms
if (botPoseRaw.length >= 6) {
    Pose2d pose = new Pose2d(botPoseRaw[0], botPoseRaw[1],
                             Rotation2d.fromDegrees(botPoseRaw[5]));
    double timestamp = Timer.getFPGATimestamp() - (botPoseRaw[6] / 1000.0);
}
```

---

## 6. Gotchas

**G-L1: SetRobotOrientation must be called every loop before MT2**
```
WRONG: Call SetRobotOrientation once in constructor
RIGHT: Call SetRobotOrientation in every periodic() before getBotPoseEstimate_wpiBlue_MegaTag2()
```
Stale orientation causes MT2 to silently return bad poses.

**G-L2: Use botpose_orb_wpiblue (MT2), not botpose**
```
WRONG: LimelightHelpers.getBotPose2d("limelight")  // field-relative to arbitrary origin
RIGHT: LimelightHelpers.getBotPoseEstimate_wpiBlue_MegaTag2("limelight")  // WPILib blue origin
```

**G-L3: Large theta stddev for MT2 — let IMU own rotation**
```
WRONG: VecBuilder.fill(0.1, 0.1, 0.1)  // trusts vision for heading (noisy)
RIGHT: VecBuilder.fill(0.7, 0.7, 9999999)  // vision only corrects x/y
```

**G-L4: timestampSeconds is already latency-compensated**
```
WRONG: Timer.getFPGATimestamp() - mt2.latency / 1000.0  // don't compute manually
RIGHT: mt2.timestampSeconds  // already correct — pass directly to addVisionMeasurement()
```
(Exception: if reading raw NT entry `botpose_orb_wpiblue`, index [6] is latency in ms and
you must compute: `Timer.getFPGATimestamp() - arr[6]/1000.0`)

**G-L5: Check tagCount before trusting the pose**
Single-tag MT2 estimates are less stable than multi-tag. Consider requiring `>= 2` tags for
high-speed autonomous, `>= 1` for teleoperated alignment.

**G-L6: Limelight coordinate system vs WPILib**
- `tx` positive = target is to the RIGHT of crosshair (camera frame)
- WPILib field: x = toward opponent wall, y = left (from blue alliance)
- For simple TX-based aiming, just negate tx for turn output (depending on camera mount)

**G-L7: Multiple limelights**
Each Limelight has its own NT table name (set in web UI). Pass the name string to every
`LimelightHelpers` call. Use a different `VecBuilder` stddev for each camera based on
distance/mount quality.

---

## 7. Simple TX-Based Aiming (Non-Pose)

For shooting/aligning without full pose estimation:

```java
// In subsystem or command:
double tx = LimelightHelpers.getTX("limelight");
boolean hasTarget = LimelightHelpers.getTV("limelight");

// P-control to aim at target
double turnOutput = hasTarget ? (kP * tx) : 0.0;  // kP ≈ 0.03–0.05 for drivebase

// Drive command integration:
m_drive.setControl(m_fieldCentric
    .withVelocityX(xSpeed)
    .withVelocityY(ySpeed)
    .withRotationalRate(-turnOutput));  // negate: positive tx → turn right → negative rate
```
