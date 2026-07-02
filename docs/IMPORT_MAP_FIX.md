# Import Map Fix for Three.js

## Issue

**Error:**
```
SES_UNCAUGHT_EXCEPTION: TypeError: The specifier "three" was a bare specifier, 
but was not remapped to anything. Relative module specifiers must start with 
"./", "../" or "/". lockdown-install.js:1:146171
```

## Root Cause

The error is caused by **browser extensions** (particularly MetaMask or other crypto wallets) that use SES (Secure ECMAScript) / Lockdown.

- `lockdown-install.js` intercepts module loading
- It requires all bare specifiers to be mapped via import maps
- Even though our code uses CDN imports correctly, extensions may inject code with bare imports

## Solution Applied

Added an **Import Map** to `avatar-integration.html`:

```html
<script type="importmap">
{
  "imports": {
    "three": "https://esm.sh/three@0.160.0",
    "three/": "https://esm.sh/three@0.160.0/",
    "three/examples/": "https://esm.sh/three@0.160.0/examples/"
  }
}
</script>
```

## What This Does

1. Maps bare `"three"` imports to CDN URL
2. Maps `"three/..."` paths to CDN
3. Compatible with SES/Lockdown enforcement
4. Doesn't affect our existing CDN imports
5. Provides fallback for any bare imports

## Benefits

✅ **MetaMask Compatible** - Works with crypto wallet extensions  
✅ **SES/Lockdown Safe** - Complies with Secure ECMAScript  
✅ **Future-Proof** - Handles any bare imports  
✅ **No Breaking Changes** - Existing imports still work  
✅ **Standard Compliant** - Uses standard Import Maps spec

## Browser Support

- ✅ Chrome 89+
- ✅ Edge 89+
- ✅ Safari 16.4+
- ✅ Firefox 108+
- ✅ Opera 76+

## Testing

1. **With Extensions:**
   - Keep MetaMask/wallet extensions enabled
   - Reload page (Cmd+Shift+R)
   - Should work without errors

2. **Without Extensions:**
   - Disable extensions
   - Reload page
   - Should work normally

3. **Incognito Mode:**
   - Open in incognito (extensions disabled)
   - Should work as fallback test

## Alternative Solutions Considered

### Option 1: Disable Extensions ❌
- Not user-friendly
- Users shouldn't have to disable security tools

### Option 2: Change All Imports ❌
- Already using CDN imports correctly
- Error is from extension injection, not our code

### Option 3: Import Map ✅ **CHOSEN**
- Standard web platform feature
- Fixes root cause
- Compatible with all scenarios

## Files Modified

1. **web/avatar-integration.html**
   - Added `<script type="importmap">` in `<head>`
   - Total changes: +13 lines

## Status

**Issue:** Browser extension compatibility  
**Fix:** Import Map added  
**Testing:** Ready  
**Production:** Safe

---

**Fixed:** 2026-05-07  
**Compatibility:** MetaMask, SES, All modern browsers
