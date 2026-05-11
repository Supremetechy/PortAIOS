# Voice Input Error Handling Improvement

## Issue
```
[Voice] Recognition error: aborted
```

Appearing in console even though it's normal behavior.

## Root Cause
- Web Speech API fires 'aborted' error when recognition is manually stopped
- This is **expected behavior**, not an actual error
- Similar with 'no-speech' when timeout occurs
- Previous code logged ALL errors as errors

## Fix Applied

**Before:**
```javascript
recognition.onerror = (event) => {
    console.error('[Voice] Recognition error:', event.error);
    // All errors logged as errors
};
```

**After:**
```javascript
recognition.onerror = (event) => {
    // Filter out expected/harmless errors
    if (event.error === 'aborted') {
        console.log('[Voice] Recognition stopped');  // Info, not error
        return;
    }
    
    if (event.error === 'no-speech') {
        console.log('[Voice] No speech detected');  // Info, not error
        return;
    }
    
    // Only log actual errors
    console.error('[Voice] Recognition error:', event.error);
};
```

## Error Types Handled

### Harmless (Now logged as info):
- ✅ `aborted` - Recognition stopped manually (normal)
- ✅ `no-speech` - No speech in timeout period (normal)

### Actual Errors (Still logged as errors):
- ❌ `audio-capture` - No microphone found
- ❌ `not-allowed` - Permission denied
- ❌ `network` - Speech API unavailable
- ❌ Other errors

## Benefits
✅ Cleaner console output  
✅ Only real errors shown as errors  
✅ Expected behavior logged as info  
✅ Better debugging experience  
✅ Less alarming for users

## Status
✅ Fixed  
✅ Tested  
✅ Production ready

---

**Fixed:** 2026-05-07  
**File:** web/voice-input.js
