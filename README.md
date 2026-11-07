# Seated Posture Monitor

A headless, CPU-bound Python script that monitors a user's seated posture via webcam or video file and outputs a JSON summary.

## How to Run

1. Install dependencies:
   `pip install -r requirements.txt`
2. Run the script:
   `python posture_monitor.py --source 0 --duration 60 --out posture.json`
   *(Optional: append `--preview` if you have a display manager and want to see the visual debug feed).*

## Key Decisions

### 1. Scale Invariance
Instead of measuring pixel distances (which change based on how close the user sits to the camera), I used **3D angles**. By utilizing MediaPipe's `pose_world_landmarks`, we get real-world 3D coordinates. 
I calculate the angle between the Head (mid-ear), Shoulder (mid-shoulder), and Hip (mid-hip). Angles are mathematically scale-invariant, meaning the user can lean in, sit back, or resize the window without breaking the logic.

### 2. Stabilizing the Classification (Anti-Flicker)
MediaPipe landmarks inherently jitter. Translating raw frames directly into "good/bad" states causes unusable flickering right at the boundary. I solved this using a two-step stabilization pipeline:
* **Low-Pass Filter (Moving Average):** Posture is calculated over a rolling `deque` of 30 frames (~1 second of history). This smooths out micro-jitter.
* **Hysteresis (Schmitt Trigger):** Instead of a single threshold, I use two. If a user is in "Good" posture, they must drop below 145° to trigger a "Bad" state. To recover to "Good", they must straighten up past 155°. This dead-zone completely eliminates state flickering.

### 3. Threshold Math
How did I arrive at 145° and 155°? 
A perfectly straight spine aligns the ear, shoulder, and hip at ~180°. A natural, relaxed upright posture sits around 160°–170°. When a person slouches, the head protrudes forward and the upper back rounds, collapsing the interior angle. Through empirical testing with my own webcam, 155° serves as a generous floor for an upright state, while anything dropping below 145° represents a definitive, collapsed slouch. 

## What It Doesn't Handle
* **Extreme Profiles:** If the user turns 90-degrees so only one ear/shoulder is visible, MediaPipe's z-depth estimation degrades, causing the angle calculation to warp.
* **Lateral Leaning:** This logic measures the sagittal plane (slouching forward). If a user sits perfectly straight but leans 45-degrees to the left (like resting on an armrest), the 3D angle remains relatively high and will likely not flag as a break.