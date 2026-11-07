import cv2
import mediapipe as mp
import numpy as np
import argparse
import json
import time
import sys
from collections import deque

def get_args():
    parser = argparse.ArgumentParser(description="Headless Seated Posture Monitor")
    parser.add_argument("--source", default="0", help="Camera index or video file path")
    parser.add_argument("--duration", type=int, default=60, help="Duration to monitor in seconds")
    parser.add_argument("--out", default="posture.json", help="Output JSON file path")
    parser.add_argument("--preview", action="store_true", help="Attempt to show preview (requires UI)")
    return parser.parse_args()

def calculate_3d_angle(a, b, c):
    """
    Calculates the 3D angle between ba and bc.
    Inherently scale-invariant.
    """
    ba = a - b
    bc = c - b
    
    # Handle zero vectors to avoid division by zero
    if np.linalg.norm(ba) == 0 or np.linalg.norm(bc) == 0:
        return 180.0 
        
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
    return np.degrees(angle)

def main():
    args = get_args()
    
    # Parse source (int for webcam, str for file)
    source = int(args.source) if args.source.isdigit() else args.source
    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"Error: Could not open video source '{args.source}'", file=sys.stderr)
        sys.exit(1)

    # Initialize MediaPipe Pose (CPU optimized)
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1 # 0 is faster, 1 is more accurate. 1 runs fine on modern CPUs.
    )

    start_time = time.time()
    end_time = start_time + args.duration

    # --- Stabilization & State Tracking ---
    # We use a 30-frame rolling window (~1 sec at 30fps) to smooth landmark jitter
    angle_history = deque(maxlen=30) 
    
    is_good_posture = True
    breaks = 0
    good_frames = 0
    total_valid_frames = 0
    consecutive_failures = 0
    
    # Hysteresis Thresholds (Degrees)
    T_HIGH = 155.0
    T_LOW = 145.0
    
    while time.time() < end_time:
        ret, frame = cap.read()
        
        # Handle dropped/corrupt frames gracefully
        if not ret:
            consecutive_failures += 1
            if consecutive_failures > 30:
                print("Error: Source stream lost or ended prematurely.", file=sys.stderr)
                break
            continue
            
        consecutive_failures = 0
        
        # MediaPipe requires RGB
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image.flags.writeable = False
        results = pose.process(image)
        
        if results.pose_world_landmarks:
            total_valid_frames += 1
            landmarks = results.pose_world_landmarks.landmark
            
            def get_pt(idx):
                return np.array([landmarks[idx].x, landmarks[idx].y, landmarks[idx].z])
            
            # Average L/R landmarks to find the center axis of the body
            l_ear, r_ear = get_pt(mp_pose.PoseLandmark.LEFT_EAR.value), get_pt(mp_pose.PoseLandmark.RIGHT_EAR.value)
            l_sh, r_sh = get_pt(mp_pose.PoseLandmark.LEFT_SHOULDER.value), get_pt(mp_pose.PoseLandmark.RIGHT_SHOULDER.value)
            l_hip, r_hip = get_pt(mp_pose.PoseLandmark.LEFT_HIP.value), get_pt(mp_pose.PoseLandmark.RIGHT_HIP.value)
            
            mid_ear = (l_ear + r_ear) / 2.0
            mid_sh = (l_sh + r_sh) / 2.0
            mid_hip = (l_hip + r_hip) / 2.0
            
            # Calculate the scale-invariant angle of the upper torso
            angle = calculate_3d_angle(mid_ear, mid_sh, mid_hip)
            angle_history.append(angle)
            
            # 1. Low-Pass Filter (Moving Average)
            smoothed_angle = np.mean(angle_history)
            
            # 2. Hysteresis (Schmitt Trigger) to prevent flickering
            if is_good_posture and smoothed_angle < T_LOW:
                is_good_posture = False
                breaks += 1
            elif not is_good_posture and smoothed_angle > T_HIGH:
                is_good_posture = True
            
            if is_good_posture:
                good_frames += 1

        if args.preview:
            # Revert color for OpenCV display
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            status_text = "Good" if is_good_posture else "Slouching"
            color = (0, 255, 0) if is_good_posture else (0, 0, 255)
            
            if len(angle_history) > 0:
                cv2.putText(image, f"Status: {status_text} | Angle: {np.mean(angle_history):.1f}", 
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            try:
                cv2.imshow("Posture Monitor Preview", image)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except cv2.error:
                print("Preview failed: You are likely using headless OpenCV.", file=sys.stderr)
                args.preview = False # Stop trying to show it

    cap.release()
    if args.preview:
        cv2.destroyAllWindows()
        
    # Validation constraint: Did we actually see someone?
    if total_valid_frames == 0:
        print("Error: No person detected during the session.", file=sys.stderr)
        sys.exit(2)
        
    # --- Compile Summary ---
    elapsed = time.time() - start_time
    fps = total_valid_frames / elapsed if elapsed > 0 else 0
    
    good_time = (good_frames / total_valid_frames) * elapsed
    bad_time = elapsed - good_time
    
    # Score 0-100: Base percentage, penalized by 2 points per break to punish fidgeting
    base_score = (good_frames / total_valid_frames) * 100
    final_score = max(0, int(base_score - (breaks * 2)))
    
    summary = {
        "session_duration_seconds": round(elapsed, 2),
        "analyzed_frames": total_valid_frames,
        "average_fps": round(fps, 1),
        "good_posture_duration_seconds": round(good_time, 2),
        "bad_posture_duration_seconds": round(bad_time, 2),
        "posture_breaks": breaks,
        "score_0_to_100": final_score
    }
    
    with open(args.out, 'w') as f:
        json.dump(summary, f, indent=4)
        
    # Exit 0 indicating a successful, usable observation
    sys.exit(0)

if __name__ == "__main__":
    main()