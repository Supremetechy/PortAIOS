# Archived HTML Files

This directory contains HTML files that have been consolidated into the new unified screen management system.

## Archived Files

### `avatar-creator-pro.html`
**Status:** Functionality integrated into `screens/avatar-creator-screen.js`  
**Reason:** Converted to modal screen component for seamless integration  
**Access:** Now available via dock button "🤖 CREATOR" or voice command "avatar creator"

### `avatar-creator.html`
**Status:** Superseded by avatar-creator-pro  
**Reason:** Earlier version, functionality merged into pro version  

### `demo.html`
**Status:** Legacy demo  
**Reason:** Binary avatar demo, functionality now in main interface  

### `enhancement-demo.html`
**Status:** Legacy demo  
**Reason:** Enhancement showcase, features integrated into main system  

### `test-voice-gesture-ui.html`
**Status:** Functionality integrated into `screens/test-suite-screen.js`  
**Reason:** Converted to modal screen for integrated testing  
**Access:** Now available via dock button "🧪 TESTS" or voice command "test suite"

### `avatar-ws-client.html`
**Status:** Legacy WebSocket client  
**Reason:** Functionality integrated into main avatar system  

### `index-binary-avatar.html`
**Status:** Superseded by index-dynamic-avatar.html  
**Reason:** Earlier version, functionality merged into dynamic interface  

## Restoration

If you need to restore any of these files for reference or compatibility:

```bash
# From web directory
cp archive/[filename] ./
```

## Migration Date
**Archived:** 2026-06-20  
**Integration:** Web interface consolidation to unified screen management system  

## Related Files
- `../INTEGRATION_SUMMARY.md` - Complete integration documentation
- `../screen-manager.js` - Unified screen management system
- `../screens/` - New modular screen components
