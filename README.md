# arakkunnam-99
Real-Time YOLO11Ops Challenge — Arakkunnam 99 | Code Recet powered by Armada

## Problem Statement
In industrial environments such as construction sites, warehouses, and manufacturing floors, worker safety depends heavily on proper use of Personal Protective Equipment (PPE) like helmets and safety vests. Manual monitoring is difficult, inconsistent, and not scalable across multiple camera feeds.

Although modern object detection models such as YOLO11 Large offer strong accuracy for safety-critical applications, they are often too slow to run in real time on standard industrial PCs that rely only on CPUs. This creates a challenge: how can we maintain high detection accuracy while achieving real-time performance without expensive GPU hardware?

## Proposed Solution
We propose a **Real-Time PPE Compliance Monitoring System** optimized for **CPU-only edge deployment**.

The system focuses on detecting(based on Industrial hazards):
- Person
- Helmet
- Safety Vest

Using these detections, the system determines whether a worker is:
- PPE compliant
- Missing helmet
- Missing safety vest
- Missing both

To make the solution practical for industrial environments, we combine:
- a YOLO11-based PPE detection model
- optimized inference using ONNX/OpenVINO
- an asynchronous decode and inference pipeline
- frame skipping with lightweight tracking
- adaptive resolution control
- support for multiple simultaneous video streams
- a live dashboard with overlays, alerts, and performance metrics
