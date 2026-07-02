const profiles = window.AIOS.userProfiles;

const newUser = profiles.createProfile({
    username: 'alice',
    displayName: 'Alice Johnson',
    email: 'alice@example.com',
    avatar: 'https://example.com/avatar.jpg',
    
    settings: {
        voice: {
            voiceSpeed: 1.2,
            voicePitch: 1.1,
            conversationMode: true
        },
        gesture: {
            sensitivity: 0.8,
            autoCalibrate: true
        }
    },
    
    customizations: {
        theme: 'neon',
        wakeWords: ['hey alice', 'alice']
    },
    
    preferences: {
        language: 'en',
        notifications: true,
        sounds: true
    }
});

// Switch to profile
profiles.switchProfile(userId);

// Switch with password
profiles.switchProfile(userId, 'password123');

// Get current user
const currentUser = profiles.getCurrentUser();
console.log(currentUser);

// Update Profile

profiles.updateProfile(userId, {
    displayName: 'Alice Smith',
    settings: {
        voice: {
            voiceSpeed: 1.5
        }
    },
    customizations: {
        theme: 'synthwave'
    }
});


// View stats
console.log(currentUser.stats);
// {
//   created: "2026-06-17T10:00:00.000Z",
//   lastLogin: "2026-06-17T17:45:00.000Z",
//   totalLogins: 42,
//   commandsExecuted: 1337,
//   gesturesUsed: 256,
//   macrosRun: 89
// }

// Update stats
profiles.updateStats(userId, {
    commandsExecuted: 1,
    gesturesUsed: 1
});