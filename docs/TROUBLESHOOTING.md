# Avatar Creator Pro - Troubleshooting Guide

## Quick Fixes for Common Issues

### Error 1: "Module name 'three' does not resolve to a valid URL"

**Problem**: Three.js module import failing

**Solution**: ✅ FIXED in latest commit
- Changed CDN from jsdelivr to unpkg
- Updated: `web/avatar-preview-3d.js`

**To verify fix**:
```bash
git pull origin main
# Refresh browser with Ctrl+Shift+R (hard reload)
```

---

### Error 2: "WebSocket connection to ws://localhost:8001/eel failed"

**Problem**: Backend server not running

**Solution 1: Start the server**
```bash
# From project root
python run_onboarding.py
```

**Solution 2: Check if server is already running**
```bash
# Check ports
lsof -i :8000 -i :8001

# If something is running, kill it
kill -9 <PID>

# Then start fresh
python run_onboarding.py
```

**Solution 3: Use test server (no backend features)**
```bash
# For frontend-only testing
python test_server.py

# Then open: http://localhost:8000/test_avatar_pro.html
```

---

## Testing Steps

### 1. Test Module Loading

Open browser console (F12) and run:
```javascript
// Test if modules load
import('./web/avatar-preview-3d.js')
  .then(() => console.log('✓ Preview module loaded'))
  .catch(e => console.error('✗ Preview failed:', e));

import('./web/avatar-animations.js')
  .then(() => console.log('✓ Animation module loaded'))
  .catch(e => console.error('✗ Animation failed:', e));
```

**Expected**: Both should print ✓ messages

---

### 2. Test 3D Preview (Standalone)

```bash
# Start test server
python test_server.py

# Open test page
open http://localhost:8000/test_avatar_pro.html

# Click "Run Module Test"
# Click "Run 3D Preview Test"
```

**Expected**:
- ✓ Green checkmarks for module loading
- ✓ Black 3D canvas appears
- ⚠ Model loading may fail (no server)

---

### 3. Test Full System

```bash
# Start full server
python run_onboarding.py

# Open Avatar Creator Pro
open http://localhost:8000/avatar-creator-pro.html
```

**Expected**:
- UI loads completely
- No console errors
- Can select presets
- Can adjust sliders

---

## Common Issues & Solutions

### Issue: Port Already in Use

**Symptoms**:
```
OSError: [Errno 48] Address already in use
```

**Solutions**:
```bash
# Find process using port
lsof -i :8000

# Kill it
kill -9 <PID>

# Or use different port in kernel/onboarding_gui.py
# Change: eel.start('index.html', port=8000)
# To:     eel.start('index.html', port=8080)
```

---

### Issue: Three.js Still Not Loading

**Symptoms**:
```
Failed to load module script: Expected a JavaScript module script
```

**Solutions**:

**1. Hard refresh browser**
```
Chrome/Edge: Ctrl+Shift+R (Cmd+Shift+R on Mac)
Firefox: Ctrl+Shift+Del → Clear cache
Safari: Cmd+Option+E → Reload
```

**2. Check network in DevTools**
- Open DevTools (F12)
- Go to Network tab
- Reload page
- Check if three.module.js loads (should be 200 OK)

**3. Test CDN directly**
```
Open in browser:
https://unpkg.com/three@0.157.0/build/three.module.js

Should show JavaScript code
```

**4. Use local Three.js (offline mode)**
```bash
# Download Three.js
cd web
mkdir libs
curl -o libs/three.module.js https://unpkg.com/three@0.157.0/build/three.module.js

# Update avatar-preview-3d.js
# Change: import * as THREE from 'https://unpkg.com/...'
# To:     import * as THREE from './libs/three.module.js'
```

---

### Issue: Eel Not Defined

**Symptoms**:
```javascript
ReferenceError: eel is not defined
```

**Solutions**:

**1. Check eel.js is loaded**
```html
<!-- Should be in HTML before your script -->
<script type="text/javascript" src="./eel.js"></script>
```

**2. Start server correctly**
```bash
# Use run_onboarding.py, NOT test_server.py
python run_onboarding.py
```

**3. Check server logs**
```bash
# Should see:
[INFO] Eel started on http://localhost:8000
```

---

### Issue: Avatar Not Appearing in 3D Preview

**Symptoms**:
- Black screen in preview
- No 3D model visible

**Solutions**:

**1. Check model path**
```javascript
// In browser console
window.avatarCreatorPro.preview3D.loadAvatar('/models/avatar.glb')
  .then(() => console.log('✓ Model loaded'))
  .catch(e => console.error('✗ Load failed:', e));
```

**2. Verify model exists**
```bash
ls -lh models/avatar*.glb
# Should show files like avatar_generated.glb
```

**3. Generate a new avatar**
```
1. Click "Generate Avatar" button
2. Wait for completion
3. Model should appear automatically
```

**4. Check WebGL support**
```javascript
// In browser console
const canvas = document.createElement('canvas');
const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
console.log('WebGL supported:', !!gl);
// Should print: WebGL supported: true
```

---

### Issue: Animations Not Playing

**Symptoms**:
- Click animation buttons
- Nothing happens

**Solutions**:

**1. Check avatar is loaded**
```javascript
// In browser console
console.log('Morph meshes:', window.avatarCreatorPro.preview3D.morphMeshes.length);
// Should be > 0
```

**2. Check morph targets exist**
```javascript
const mesh = window.avatarCreatorPro.preview3D.morphMeshes[0];
console.log('Morph targets:', Object.keys(mesh.morphTargetDictionary || {}));
// Should show array of morph target names
```

**3. Test animation manually**
```javascript
const player = window.avatarCreatorPro.animationPlayer;
player.play('greet', 'expression');
```

**4. Check for errors**
```
Open DevTools → Console
Look for red error messages
```

---

### Issue: Save/Load Not Working

**Symptoms**:
```
Failed to save avatar
```

**Solutions**:

**1. Check storage directory**
```bash
ls -la ~/.aios/avatars/
# Should exist, if not:
mkdir -p ~/.aios/avatars/
chmod 755 ~/.aios/avatars/
```

**2. Check disk space**
```bash
df -h
# Ensure you have at least 10MB free
```

**3. Test backend function**
```javascript
// In browser console
eel.list_saved_avatars()()
  .then(r => console.log('✓ Storage working:', r))
  .catch(e => console.error('✗ Storage failed:', e));
```

**4. Check permissions**
```bash
# Ensure ~/.aios is writable
chmod -R 755 ~/.aios/
```

---

## Browser Compatibility

### Recommended Browsers
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Edge 90+
- ✅ Safari 14+ (may have WebGL issues)

### Known Issues
- Safari: WebGL may be disabled by default
  - Fix: Safari → Preferences → Advanced → Show Develop menu
  - Then: Develop → Experimental Features → WebGL 2.0
  
- Firefox: CORS issues with local files
  - Fix: Use `python test_server.py` instead of file://

---

## Performance Issues

### Issue: Low FPS in 3D Preview

**Solutions**:

**1. Enable hardware acceleration**
```
Chrome: chrome://settings → Advanced → System → Use hardware acceleration
Firefox: about:config → layers.acceleration.force-enabled = true
```

**2. Reduce render quality**
```javascript
// In avatar-preview-3d.js, change:
this.renderer.setPixelRatio(window.devicePixelRatio);
// To:
this.renderer.setPixelRatio(1); // Lower quality, better performance
```

**3. Disable anti-aliasing**
```javascript
// In avatar-preview-3d.js, change:
this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
// To:
this.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
```

---

## Debug Mode

### Enable Verbose Logging

```javascript
// Add to avatar-creator-pro.js (at top)
window.DEBUG_AVATAR = true;

// Then reload page and check console for detailed logs
```

### Manual Testing Commands

```javascript
// Get current state
console.log('Preview:', window.avatarCreatorPro.preview3D);
console.log('Player:', window.avatarCreatorPro.animationPlayer);
console.log('Params:', window.avatarCreatorPro.currentParams);

// Load avatar manually
await window.avatarCreatorPro.preview3D.loadAvatar('/models/avatar.glb');

// Play animation manually
window.avatarCreatorPro.animationPlayer.play('greet', 'expression');

// Update preview manually
window.avatarCreatorPro.preview3D.updateFromParams(window.avatarCreatorPro.currentParams);
```

---

## Getting Help

### 1. Check Logs
```bash
# Server logs
tail -f ~/.aios/portaios.log

# Browser console (F12)
# Look for errors in Console tab
```

### 2. Run Test Suite
```bash
# Start test server
python test_server.py

# Open test page
http://localhost:8000/test_avatar_pro.html

# Run all tests and screenshot results
```

### 3. Verify Installation
```bash
# Check dependencies
pip list | grep -E "(eel|bottle|websockets|numpy|psutil)"

# Check files
ls web/avatar-*.js web/avatar-*.html

# Check models
ls models/*.glb
```

---

## Still Having Issues?

### Collect Debug Info

```bash
# Create debug report
cat > debug_report.txt << EOF
System: $(uname -a)
Python: $(python --version)
Browser: (paste from browser's About page)
Error: (paste error message)

Test Results:
- Module test: (pass/fail)
- 3D Preview test: (pass/fail)
- Animation test: (pass/fail)
- Backend test: (pass/fail)

Console errors: (paste from browser console)
EOF
```

### Reset Everything

```bash
# Nuclear option - clean slate
rm -rf ~/.aios/avatars/*
rm -rf __pycache__
rm -rf kernel/__pycache__
pkill -f "python.*run_onboarding"

# Reinstall dependencies
pip install -r requirements_gui.txt

# Start fresh
python run_onboarding.py
```

---

## Quick Reference

### Start Server
```bash
python run_onboarding.py
```

### Access URLs
- Full App: http://localhost:8000/avatar-creator-pro.html
- Original: http://localhost:8000/avatar-creator.html
- Test Page: http://localhost:8000/test_avatar_pro.html

### Check Status
```bash
# Server running?
lsof -i :8000

# Files present?
ls web/avatar-*.{html,js}

# Storage working?
ls ~/.aios/avatars/
```

---

**Last Updated**: 2026-05-11
**Version**: Avatar Creator Pro v1.0
