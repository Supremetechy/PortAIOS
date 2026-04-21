# AI-OS Onboarding Videos

This directory contains AI talking head videos for the onboarding process.

## Required Videos

The following videos should be placed in this directory:

1. **welcome.mp4** - Introduction to AI-OS
   - Duration: 2-3 minutes
   - Content: Welcome message, overview of AI-OS features
   
2. **hardware_setup.mp4** - Hardware Detection Guide
   - Duration: 3-4 minutes
   - Content: Explanation of hardware detection process, supported hardware
   
3. **gpu_configuration.mp4** - GPU Configuration
   - Duration: 2-3 minutes
   - Content: GPU setup for NVIDIA, AMD, and Apple Silicon
   
4. **network_setup.mp4** - Network Configuration
   - Duration: 2-3 minutes
   - Content: Network setup for distributed training
   
5. **security_overview.mp4** - Security & Privacy
   - Duration: 2-3 minutes
   - Content: Security features and best practices
   
6. **setup_complete.mp4** - Setup Complete
   - Duration: 1-2 minutes
   - Content: Congratulations message and next steps

## Video Specifications

- **Format**: MP4 (H.264 codec)
- **Resolution**: 1280x720 (720p) or 1920x1080 (1080p)
- **Aspect Ratio**: 16:9
- **Audio**: AAC codec, stereo
- **Bitrate**: 2-5 Mbps for video, 128-192 kbps for audio

## Creating AI Talking Head Videos

### Option 1: Pre-recorded Videos
Use services like:
- D-ID (https://www.d-id.com/)
- Synthesia (https://www.synthesia.io/)
- HeyGen (https://www.heygen.com/)

### Option 2: Generate with Open Source
Use tools like:
- Wav2Lip (https://github.com/Rudrabha/Wav2Lip)
- SadTalker (https://github.com/OpenTalker/SadTalker)
- Video-Retalking (https://github.com/OpenTalker/video-retalking)

### Option 3: Placeholder Videos
For testing, create simple placeholder videos with:
```bash
# Using ffmpeg to create a test video
ffmpeg -f lavfi -i color=c=blue:s=1280x720:d=30 -vf \
  "drawtext=text='AI-OS Welcome Video':fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2" \
  -c:v libx264 -t 30 welcome.mp4
```

## Script Templates

### Welcome Video Script
```
Hello! Welcome to AI-OS, your intelligent operating system designed specifically 
for AI workloads. I'm your AI assistant, and I'll guide you through the setup 
process.

AI-OS provides automatic hardware detection, GPU optimization, and seamless 
integration with popular AI frameworks like PyTorch, TensorFlow, and JAX.

Let's get started with setting up your system for maximum AI performance!
```

### Hardware Setup Video Script
```
Now we'll detect your hardware and optimize AI-OS for your specific configuration.

AI-OS automatically detects:
- CPU architecture and core count
- GPU devices (NVIDIA, AMD, Apple Silicon)
- Available memory and storage
- Network interfaces for distributed training

Click 'Detect Hardware' to scan your system. This process takes just a few seconds.
```

### GPU Configuration Video Script
```
Let's configure your GPU for AI workloads.

AI-OS supports:
- NVIDIA GPUs with CUDA acceleration
- AMD GPUs with ROCm support
- Apple Silicon with Metal Performance Shaders

I've automatically detected your GPU configuration. You can enable or disable 
specific features based on your needs.
```

### Completion Video Script
```
Congratulations! You've successfully set up AI-OS!

Your system is now optimized and ready for:
- Training machine learning models
- Running AI inference workloads
- Distributed training across multiple GPUs
- Real-time AI monitoring and resource management

Click 'Launch AI-OS' to start your AI journey!
```

## Testing Without Videos

The onboarding GUI will work without videos - the video player will simply show 
a placeholder. Videos enhance the user experience but are not required for 
functionality.
