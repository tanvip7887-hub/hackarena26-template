# VICSTA Hackathon – Grand Finale
**VIT College, Kondhwa Campus | 5th – 6th March**

---

## Team Details

- **Team Name: TechDrift**
- **Members: Tanavi Pandao (Team Leader), Swarai Wath (Team member)**
- **Domain: Productivity & Security**

---

## Project

**Problem: PS-01 : ThreatSense AI-DVR
Traditional CCTV requires constant human monitoring. Build an "AI-based DVR" for Ethernet cameras that filters out false positives (animals, shadows) and only alerts security for high-risk human behavior.** 

**Solution:** 

We are building a smart AI-based DVR that detects suspicious human activity in real-time.  

**Planned features to add initially:**  

- **Person Detection:** Detect humans in the frame using YOLOv8.  
- **Loitering Detection:** Track people and flag if they stay in one place for too long.  
- **Restricted Zone Monitoring:** Alert when someone enters a predefined restricted area.  
- **Day/Night Awareness:** Adjust detection logic depending on morning or night conditions.  

> These are the first features we plan to implement. More advanced capabilities will be added as we continue development during the hackathon.
---

## Rules to Remember

- All development must happen **during** the hackathon only
- Push code **regularly** — commit history is monitored
- Use only open-source libraries with compatible licenses and **credit them**
- Only **one submission** per team
- All members must be present **both days**

---

## Attribution

List any external libraries, APIs, or datasets used here.

This project uses or references the following external resources:

- [YOLOv8](https://github.com/ultralytics/ultralytics) – Person detection model for real-time object detection.
- [SORT Tracker](https://github.com/abewley/sort) – Simple Online and Realtime Tracking for tracking multiple people with unique IDs.
- Python libraries: OpenCV, NumPy, FilterPy – for video processing, numerical computations, and Kalman filters.
- Concepts and scoring logic inspired by multi-signal behavioral profiling techniques for restricted area monitoring.

---

> *"The world is not enough — but it is such a perfect place to start."* — James Bond
>
> All the best to every team. Build something great. 🚀
