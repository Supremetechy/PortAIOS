// phonemeMap.js
// Shared IPA phoneme → Oculus/ARKit viseme mapping used by both
// Avatar.jsx (blendshape driving) and useSpeechStream.js (keyframe lookup).
// Covers Piper / eSpeak IPA output.

// Enhanced phoneme map with FALLBACK support for missing morph targets
// Maps Piper/eSpeak IPA phonemes to available GLB visemes
// GLB has: Frown, Smile, Surprise, Viseme_A, Viseme_E, Viseme_M, Viseme_O, 
//          Wink_Left, Wink_Right, browInnerUp, eyeBlinkLeft, eyeBlinkRight, 
//          jawOpen, mouthSmileLeft, mouthSmileRight, viseme_E, viseme_O, viseme_PP, viseme_aa

export const PHONEME_TO_VISEME = {
  // silence / pauses - fallback to neutral
  '_': 'viseme_sil', 'sil': 'viseme_sil', '': 'viseme_sil',
  
  // bilabial (lips closed) - use viseme_PP or Viseme_M
  'p': 'viseme_PP', 'b': 'viseme_PP', 'm': 'viseme_PP',
  
  // labiodental (teeth on lip) - fallback to jawOpen
  'f': 'viseme_FF', 'v': 'viseme_FF',
  
  // dental (tongue between teeth) - fallback to jawOpen
  'T': 'viseme_TH', 'D': 'viseme_TH', 'th': 'viseme_TH', 'dh': 'viseme_TH',
  
  // alveolar stops - fallback to jawOpen or Viseme_E
  't': 'viseme_DD', 'd': 'viseme_DD', 'n': 'viseme_nn', 'l': 'viseme_nn',
  
  // velar - fallback to Viseme_A or jawOpen
  'k': 'viseme_kk', 'g': 'viseme_kk', 'N': 'viseme_kk', 'ng': 'viseme_kk',
  
  // postalveolar affricates - fallback to Viseme_O
  'tS': 'viseme_CH', 'dZ': 'viseme_CH', 'S': 'viseme_CH', 'Z': 'viseme_CH',
  
  // sibilants - fallback to Viseme_E
  's': 'viseme_SS', 'z': 'viseme_SS',
  
  // approximant - fallback to Viseme_A
  'r': 'viseme_RR', '4': 'viseme_RR',
  
  // vowels (IPA-ish from eSpeak) - use available viseme_aa, viseme_E, viseme_O
  'a': 'viseme_aa', 'A': 'viseme_aa', 'A:': 'viseme_aa',
  'E': 'viseme_E',  'e': 'viseme_E',  'eI': 'viseme_E',
  'I': 'viseme_I',  'i': 'viseme_I',  'i:': 'viseme_I',
  'O': 'viseme_O',  'o': 'viseme_O',  'oU': 'viseme_O', 'OI': 'viseme_O',
  'U': 'viseme_U',  'u': 'viseme_U',  'u:': 'viseme_U',
};

// Fallback map for missing visemes → available GLB morph targets
export const VISEME_FALLBACK_MAP = {
  // Missing visemes → best available alternative
  'viseme_sil': 'Viseme_A',      // Silence → neutral mouth
  'viseme_FF': 'jawOpen',         // F/V sounds → jaw open
  'viseme_TH': 'jawOpen',         // TH sounds → jaw open
  'viseme_DD': 'jawOpen',         // T/D sounds → jaw open
  'viseme_nn': 'Viseme_E',        // N/L sounds → E shape
  'viseme_kk': 'Viseme_A',        // K/G sounds → A shape
  'viseme_CH': 'Viseme_O',        // CH/SH sounds → O shape (rounded)
  'viseme_SS': 'Viseme_E',        // S/Z sounds → E shape
  'viseme_RR': 'Viseme_A',        // R sounds → A shape
  'viseme_I': 'Viseme_E',         // I vowel → E shape
  'viseme_U': 'Viseme_O',         // U vowel → O shape (rounded)
  
  // Normalize case variations
  'Viseme_A': 'Viseme_A',
  'Viseme_E': 'Viseme_E',
  'Viseme_M': 'Viseme_M',
  'Viseme_O': 'Viseme_O',
  'viseme_E': 'Viseme_E',
  'viseme_O': 'Viseme_O',
  'viseme_PP': 'Viseme_M',
  'viseme_aa': 'Viseme_A'
};
