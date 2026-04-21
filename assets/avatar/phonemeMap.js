// phonemeMap.js
// Shared IPA phoneme → Oculus/ARKit viseme mapping used by both
// Avatar.jsx (blendshape driving) and useSpeechStream.js (keyframe lookup).
// Covers Piper / eSpeak IPA output.

export const PHONEME_TO_VISEME = {
  // silence / pauses
  '_': 'viseme_sil', 'sil': 'viseme_sil', '': 'viseme_sil',
  // bilabial
  'p': 'viseme_PP', 'b': 'viseme_PP', 'm': 'viseme_PP',
  // labiodental
  'f': 'viseme_FF', 'v': 'viseme_FF',
  // dental
  'T': 'viseme_TH', 'D': 'viseme_TH', 'th': 'viseme_TH', 'dh': 'viseme_TH',
  // alveolar stops
  't': 'viseme_DD', 'd': 'viseme_DD', 'n': 'viseme_nn', 'l': 'viseme_nn',
  // velar
  'k': 'viseme_kk', 'g': 'viseme_kk', 'N': 'viseme_kk', 'ng': 'viseme_kk',
  // postalveolar affricates
  'tS': 'viseme_CH', 'dZ': 'viseme_CH', 'S': 'viseme_CH', 'Z': 'viseme_CH',
  // sibilants
  's': 'viseme_SS', 'z': 'viseme_SS',
  // approximant
  'r': 'viseme_RR', '4': 'viseme_RR',
  // vowels (IPA-ish from eSpeak)
  'a': 'viseme_aa', 'A': 'viseme_aa', 'A:': 'viseme_aa',
  'E': 'viseme_E',  'e': 'viseme_E',  'eI': 'viseme_E',
  'I': 'viseme_I',  'i': 'viseme_I',  'i:': 'viseme_I',
  'O': 'viseme_O',  'o': 'viseme_O',  'oU': 'viseme_O', 'OI': 'viseme_O',
  'U': 'viseme_U',  'u': 'viseme_U',  'u:': 'viseme_U',
};
