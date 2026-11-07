# Seated Posture Monitor

A lightweight, headless, CPU-optimized Python application that monitors a user's seated posture in real time using a webcam or a pre-recorded video. It uses **MediaPipe Pose** for 3D body landmark detection and OpenCV for video processing.

The application analyzes the alignment of the head, shoulders, and hips to identify potential forward-slouching behavior. It tracks posture changes over a configurable monitoring session and generates a structured JSON report containing posture statistics and an overall posture score.

## 1. Features

- **Real-time Posture Monitoring:** Processes webcam streams or pre-recorded video files.
- **3D Pose Estimation:** Uses MediaPipe Pose World Landmarks to extract 3D body coordinates.
- **Scale-Invariant Angle Calculation:** Calculates posture using geometric angles instead of pixel distances.
- **Noise Reduction:** Applies a moving average filter to reduce landmark jitter.
- **Anti-Flicker Classification:** Uses hysteresis thresholds to prevent frequent switching between good and bad posture.
- **Posture Break Tracking:** Counts transitions from good posture to slouching.
- **Session Analytics:** Calculates posture duration, processing FPS, and an overall posture score.
- **JSON Reporting:** Exports session statistics in a structured JSON format.
- **Headless Execution:** Runs without requiring a graphical interface and is optimized for CPU execution.

## 2. Project Structure

```text
BharathAAP_Technologies_Assessment/
│
├── posture_monitor.py    # Main posture monitoring application
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
└── .gitignore            # Files excluded from Git
```

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| MediaPipe Pose | Human pose estimation and 3D landmark detection |
| OpenCV | Video capture and frame processing |
| NumPy | Vector operations and angle calculations |
| Collections (deque) | Rolling window for posture smoothing |
| JSON | Exporting session analytics |

## 4. Installation and Setup

### Prerequisites

- Python 3.12
- Webcam or a pre-recorded video file
- Git (optional, for cloning the repository)

### Step 1: Clone the repository

```bash
git clone https://github.com/Shitalpoonam123/BharathAAP_Technologies_Assessment.git

cd BharathAAP_Technologies_Assessment
```

### Step 2: Create a virtual environment (Recommended)

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### Step 3: Install dependencies

```bash
python -m pip install -r requirements.txt
```

### Requirements

The application uses pinned dependency versions to maintain compatibility with the MediaPipe Solutions API.

```text
mediapipe==0.10.21
opencv-python-headless==4.10.0.84
numpy==1.26.4
```

## 5. How to Run

### Option A: Monitor using a webcam

Run the following command:

```bash
python posture_monitor.py --source 0 --duration 60 --out posture.json
```

This starts a 60-second monitoring session using the default webcam.

### Option B: Monitor using a video file

```bash
python posture_monitor.py --source "sample.mp4" --duration 60 --out posture.json
```

Replace `sample.mp4` with the path to your video file.

### Option C: Enable visual preview

If you have a graphical display and are using a GUI-enabled OpenCV installation:

```bash
python posture_monitor.py --source 0 --duration 60 --out posture.json --preview
```

Note: The default headless OpenCV installation does not support displaying windows. Use a GUI-enabled OpenCV installation if preview functionality is required.

## 6. Command-Line Arguments

| Argument | Default | Description |
|---|---|---|
| `--source` | `0` | Webcam index or video file path |
| `--duration` | `60` | Monitoring duration in seconds |
| `--out` | `posture.json` | Output JSON file path |
| `--preview` | Disabled | Enables visual debugging preview when GUI support is available |

## 7. How the Algorithm Works

The application follows a frame-by-frame processing pipeline.

### Step 1: Video Acquisition

OpenCV captures frames from the webcam or video file using `cv2.VideoCapture()`.

Each frame is converted from BGR to RGB because MediaPipe expects RGB input.

### Step 2: 3D Pose Estimation

MediaPipe Pose processes each frame and identifies body landmarks.

The application uses the following landmarks:

- Left Ear
- Right Ear
- Left Shoulder
- Right Shoulder
- Left Hip
- Right Hip

The left and right landmarks are averaged to calculate the central body alignment.

### Step 3: Scale-Invariant Angle Calculation

Instead of relying on pixel distances, the application uses 3D world coordinates from MediaPipe.

It calculates the angle formed by three points:

- A: Mid-ear
- B: Mid-shoulder
- C: Mid-hip

The angle is calculated using vector geometry:

```python
angle = calculate_3d_angle(mid_ear, mid_sh, mid_hip)
```

The angle between the two vectors is calculated using the dot product:

\[
\theta = \cos^{-1}\left(
\frac{BA \cdot BC}{|BA||BC|}
\right)
\]

This makes the measurement independent of uniform coordinate scaling.

### Step 4: Posture Stabilization

Raw pose landmarks can fluctuate slightly between consecutive frames. To avoid unstable classifications, two techniques are applied.

**A. Moving Average Filter**

A rolling window of 30 frames is maintained using Python's `deque`.

```python
angle_history = deque(maxlen=30)
smoothed_angle = np.mean(angle_history)
```

This reduces short-term fluctuations in the calculated posture angle.

**B. Hysteresis (Schmitt Trigger)**

Two separate thresholds are used:

| Threshold | Value | Purpose |
|---|---:|---|
| Upper threshold | 155° | Recovery to good posture |
| Lower threshold | 145° | Transition to bad posture |

Classification logic:

- Good → Bad: When the smoothed angle falls below 145°.
- Bad → Good: When the smoothed angle rises above 155°.
- Between 145° and 155°: Retain the previous posture state.

This dead zone prevents rapid switching between posture states near the threshold.

### Step 5: Session Statistics

During monitoring, the application tracks:

- Total valid frames
- Good posture frames
- Number of posture breaks
- Total session duration

At the end of the session, it calculates the posture score and exports the results.

## 8. Expected Output

After successful execution, the application generates a JSON file named `posture.json` in the current working directory.

### Sample JSON Output

The following is an illustrative example:

```json
{
    "session_duration_seconds": 60.25,
    "analyzed_frames": 1713,
    "average_fps": 28.4,
    "good_posture_duration_seconds": 60.25,
    "bad_posture_duration_seconds": 0.0,
    "posture_breaks": 0,
    "score_0_to_100": 100
}
```

### Understanding the Output

| Field | Description |
|---|---|
| `session_duration_seconds` | Actual elapsed time of the monitoring session. |
| `analyzed_frames` | Number of frames in which a valid person pose was detected. |
| `average_fps` | Average processing throughput, calculated as valid frames divided by elapsed time. |
| `good_posture_duration_seconds` | Estimated time classified as good posture. |
| `bad_posture_duration_seconds` | Estimated time classified as bad posture. |
| `posture_breaks` | Number of transitions from good posture to bad posture. |
| `score_0_to_100` | Final posture score after applying the break penalty. |

### Understanding the Posture Score

The application calculates the score using:

\[
\text{Base Score} =
\frac{\text{Good Frames}}{\text{Valid Frames}}
\times 100
\]

A penalty of 2 points is applied for every posture break:

\[
\text{Final Score} =
\max(0,\text{Base Score}-(2\times\text{Breaks}))
\]

For example:

Suppose a session has:
- 1,000 valid frames
- 800 good posture frames
- 200 bad posture frames
- 3 posture breaks

Then:

\[
\text{Base Score} = \frac{800}{1000}\times100=80
\]

\[
\text{Final Score}=80-(3\times2)=74
\]

The final posture score is **74/100**.

Note: The score is a heuristic based on the application's classification logic. It is not a medical assessment or a clinically validated posture measurement.

## 9. Key Technical Decisions

### 1. Scale Invariance

Pixel-based measurements are sensitive to camera distance and image resizing. Using 3D landmark coordinates and angular geometry makes the calculation independent of uniform scaling.

### 2. Temporal Smoothing

A 30-frame moving average reduces noise and makes posture classification more stable.

### 3. Hysteresis-Based Classification

Separate entry and recovery thresholds avoid flickering when the posture angle fluctuates around a single boundary.

### 4. CPU Optimization

The application uses MediaPipe's CPU inference capabilities and the TensorFlow Lite XNNPACK delegate where available. This avoids requiring a dedicated GPU for inference.

### 5. Headless Processing

`opencv-python-headless` allows video processing without requiring a graphical interface, making the application suitable for background execution and environments without display support.

## 10. Limitations and Assumptions

- **Extreme Camera Angles:** Turning approximately 90 degrees away from the camera can reduce landmark accuracy and affect depth estimation.
- **Lateral Leaning:** The current angle-based logic primarily targets forward slouching and may not reliably detect side leaning.
- **Camera Position:** Consistent camera positioning and visibility of the upper body are important for reliable results.
- **Landmark Visibility:** Occlusion or poor lighting can affect pose estimation.
- **Threshold Calibration:** The 145° and 155° thresholds are heuristic values and may need adjustment for different individuals and camera positions.
- **Frame Timing:** The duration calculations use valid-frame ratios and elapsed session time, so they are estimates rather than precise frame-level timing measurements.

## 11. Error Handling

The application includes basic error handling for:

- Unavailable webcam or invalid video source.
- Dropped or corrupted video frames.
- No person detected during the monitoring session.
- Preview failures in environments without GUI support.

The script exits with a non