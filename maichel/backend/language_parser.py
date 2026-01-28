"""
Advanced Multi-Language Command Parser for Michael AI
Supports English, Hindi, and Hinglish with informal speech patterns
"""
import re
from typing import Dict, List, Optional, Tuple

class LanguageParser:
    """Advanced command parser with multi-language support"""
    
    def __init__(self):
        # Initialize command mappings
        self._init_command_mappings()
    
    def _init_command_mappings(self):
        """Initialize comprehensive command mappings"""
        
        # File operations keywords
        self.file_delete_keywords = [
            # English
            'delete', 'remove', 'erase', 'del', 'rm',
            # Hindi (Devanagari)
            'मिटा', 'हटा', 'डिलीट', 'मिटाओ', 'हटाओ', 'हटा दो', 'मिटा दो',
            # Hindi (Roman/Hinglish)
            'mita', 'hata', 'delete kar', 'mita do', 'hata do', 'udd ja', 'hatao', 'mitao'
        ]
        
        self.file_create_keywords = [
            'create', 'make', 'new',
            'बना', 'बनाओ', 'नया',
            'bana', 'banao', 'create kar'
        ]
        
        self.file_rename_keywords = [
            'rename', 'change name',
            'नाम बदल', 'रीनेम',
            'naam badal', 'rename kar'
        ]
        
        # System control keywords
        self.shutdown_keywords = [
            'shutdown', 'shut down', 'power off', 'turn off',
            'बंद कर', 'बंद करो', 'शटडाउन', 'बंद कर दे', 'off kar',
            'band kar', 'band karo', 'band kar de', 'off kar de', 'shutdown kar'
        ]
        
        self.restart_keywords = [
            'restart', 'reboot', 'reset',
            'रीस्टार्ट', 'फिर से चालू', 'दुबारा चालू',
            'restart kar', 'reboot kar', 'dubara chalu kar'
        ]
        
        self.lock_keywords = [
            'lock', 'lock screen', 'lock computer',
            'लॉक', 'लॉक करो', 'ताला लगा',
            'lock kar', 'lock karo', 'taala laga'
        ]
        
        self.sleep_keywords = [
            'sleep', 'hibernate', 'suspend',
            'सो जा', 'सुला', 'स्लीप',
            'so ja', 'sula', 'sleep kar', 'sleep mode'
        ]
        
        # Application control keywords
        self.open_keywords = [
            'open', 'start', 'launch', 'run',
            'खोल', 'खोलो', 'चालू', 'चलाओ', 'ओपन', 'स्टार्ट',
            'khol', 'kholo', 'chalao', 'chalu kar', 'chalu', 'start kar', 'open kar'
        ]
        
        self.close_keywords = [
            'close', 'exit', 'quit', 'kill',
            'बंद', 'बंद करो', 'क्लोज',
            'band kar', 'close kar', 'band karo', 'exit kar'
        ]
        
        # Common application name mappings
        self.app_mappings = {
            # Browsers
            'chrome': ['chrome', 'google', 'browser', 'ब्राउज़र', 'ब्राउजर', 'क्रोम', 'गूगल', 'internet'],
            'firefox': ['firefox', 'फायरफॉक्स'],
            'edge': ['edge', 'एज', 'microsoft edge'],
            
            # Editors
            'notepad': ['notepad', 'नोटपैड', 'copy', 'likhne waala'],
            'vscode': ['vscode', 'vs code', 'code', 'visual studio code', 'कोड', 'coding'],
            
            # System
            'explorer': ['explorer', 'file explorer', 'folder', 'files', 'फोल्डर', 'फाइल', 'pc', 'this pc'],
            'cmd': ['cmd', 'command prompt', 'terminal', 'कमांड', 'टर्मिनल', 'kala dabba', 'kaale dabba'],
            'calculator': ['calculator', 'calc', 'कैलकुलेटर', 'hisaab'],
            'settings': ['settings', 'सेटिंग्स', 'control panel'],
            
            # Common apps
            'spotify': ['spotify', 'music', 'संगीत', 'म्यूजिक', 'gaana', 'gaane'],
            'discord': ['discord', 'डिस्कॉर्ड'],
            'whatsapp': ['whatsapp', 'व्हाट्सएप'],
        }

        # New System Keywords
        self.volume_keywords = ['volume', 'awaz', 'sound', 'awaaz', 'shor', 'aawaz', 'आवाज']
        self.brightness_keywords = ['brightness', 'roshni', 'light', 'chamak', 'screen', 'ब्राइटनेस']
        self.settings_keywords = ['settings', 'seting', 'vikalp', 'seeting', 'सेटिंग्स']
    
    def parse_command(self, text: str) -> Dict:
        """
        Parse natural language command into structured intent
        
        Returns:
            {
                'intent': str,  # e.g., 'file_delete', 'system_shutdown', 'app_open'
                'entities': dict,  # extracted parameters
                'confidence': float,  # 0-1
                'original_text': str
            }
        """
        text_lower = text.lower().strip()
        
        # Remove wake words
        text_clean = self._remove_wake_words(text_lower)
        
        # Try to match intent
        intent_result = self._detect_intent(text_clean)
        
        return intent_result
    
    def _remove_wake_words(self, text: str) -> str:
        """Remove wake words from command"""
        wake_words = ['michael', 'mike', 'माइकल', 'माइक', 'lisa', 'leesa', 'लिसा', 'लीसा']
        for word in wake_words:
            text = text.replace(word, '')
        return text.strip()
    
    def _detect_intent(self, text: str) -> Dict:
        """Detect user intent from cleaned text"""
        
        # Conversational / Identity
        if self._contains_any(text, ['kaun ho', 'who are you', 'naam kya', 'identity', 'about you']):
            return {'intent': 'about_me', 'entities': {}, 'confidence': 0.9, 'original_text': text}
        
        if self._contains_any(text, ['kya kar sakti', 'features', 'help', 'madad', 'capabilities']):
            return {'intent': 'capabilities', 'entities': {}, 'confidence': 0.9, 'original_text': text}

        # System shutdown
        if self._contains_any(text, self.shutdown_keywords):
            return {'intent': 'system_shutdown', 'entities': {}, 'confidence': 0.95, 'original_text': text}
        
        # ... (rest of the intents) ...
        # System restart
        if self._contains_any(text, self.restart_keywords):
            return {'intent': 'system_restart', 'entities': {}, 'confidence': 0.95, 'original_text': text}
        
        # Lock screen
        if self._contains_any(text, self.lock_keywords):
            return {'intent': 'system_lock', 'entities': {}, 'confidence': 0.95, 'original_text': text}
        
        # Sleep/hibernate
        if self._contains_any(text, self.sleep_keywords):
            return {'intent': 'system_sleep', 'entities': {}, 'confidence': 0.9, 'original_text': text}
        
        # File delete
        if self._contains_any(text, self.file_delete_keywords):
            filename = self._extract_filename(text, self.file_delete_keywords)
            return {'intent': 'file_delete', 'entities': {'filename': filename}, 'confidence': 0.85, 'original_text': text}
        
        # File create
        if self._contains_any(text, self.file_create_keywords):
            filename = self._extract_filename(text, self.file_create_keywords)
            return {'intent': 'file_create', 'entities': {'filename': filename}, 'confidence': 0.85, 'original_text': text}
        
        # App open
        if self._contains_any(text, self.open_keywords):
            app_name = self._extract_app_name(text, self.open_keywords)
            return {'intent': 'app_open', 'entities': {'app': app_name}, 'confidence': 0.9, 'original_text': text}
        
        # App close
        if self._contains_any(text, self.close_keywords):
            app_name = self._extract_app_name(text, self.close_keywords)
            return {'intent': 'app_close', 'entities': {'app': app_name}, 'confidence': 0.9, 'original_text': text}

        # Volume
        if self._contains_any(text, self.volume_keywords):
            direction = 'up' if any(w in text for w in ['badhao', 'up', 'high', 'increase']) else \
                        'down' if any(w in text for w in ['kam', 'down', 'low', 'decrease']) else \
                        'mute' if any(w in text for w in ['mute', 'chup', 'band']) else 'up'
            return {'intent': 'volume', 'entities': {'direction': direction}, 'confidence': 0.9, 'original_text': text}

        # Brightness
        if self._contains_any(text, self.brightness_keywords):
            direction = 'up' if any(w in text for w in ['badhao', 'up', 'high', 'increase', 'bright']) else \
                        'down' if any(w in text for w in ['kam', 'down', 'low', 'decrease', 'dark']) else 'up'
            return {'intent': 'brightness', 'entities': {'direction': direction}, 'confidence': 0.9, 'original_text': text}

        # Settings
        if self._contains_any(text, self.settings_keywords):
            page = 'display' if 'display' in text or 'screen' in text else \
                   'apps' if 'app' in text or 'feature' in text else \
                   'wifi' if 'wifi' in text or 'net' in text else 'settings'
            return {'intent': 'settings', 'entities': {'page': page}, 'confidence': 0.9, 'original_text': text}

        # Unknown intent - return as terminal command
        return {
            'intent': 'terminal_command',
            'entities': {'command': text},
            'confidence': 0.5,
            'original_text': text
        }
    
    def _contains_any(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        for keyword in keywords:
            if keyword in text:
                return True
        return False
    
    def _extract_filename(self, text: str, remove_keywords: List[str]) -> str:
        """Extract filename from command text"""
        cleaned = text
        for keyword in remove_keywords:
            cleaned = cleaned.replace(keyword, '')
        
        # Remove common words
        common_words = ['file', 'folder', 'this', 'that', 'the', 'फाइल', 'ye', 'wo', 'yeh', 'वो']
        for word in common_words:
            cleaned = cleaned.replace(word, '')
        
        return cleaned.strip()
    
    def _extract_app_name(self, text: str, remove_keywords: List[str]) -> str:
        """Extract and normalize app name from command text"""
        cleaned = text
        for keyword in remove_keywords:
            cleaned = cleaned.replace(keyword, '')
        
        cleaned = cleaned.strip()
        
        # Try to match with known apps
        for app_name, aliases in self.app_mappings.items():
            for alias in aliases:
                if alias in cleaned:
                    return app_name
        
        # Return cleaned text if no match
        return cleaned
    
    def get_response_message(self, intent: str, entities: Dict, language: str = 'hinglish') -> str:
        """Generate appropriate response message based on intent and language"""
        import random
        
        fillers = {
            'hinglish': ['Theek hai Admin...', 'Hmm, samajh gayi...', 'Zaroor...', 'Ji, turant karti hoon...', 'Oye hoye, ye lijiye...'],
            'hindi': ['ठीक है एडमिन...', 'जी, अभी करती हूँ...', 'समझ गई...', 'ज़रूर...'],
            'english': ['Okay Admin...', 'Sure thing...', 'Processing that for you...', 'Right away...']
        }
        
        prefix = random.choice(fillers.get(language, fillers['hinglish']))

        responses = {
            'about_me': {
                'hinglish': f"{prefix} Main Lisa hoon, Michael project ki sabse advance AI. Main aapke computer ko God Mode mein control kar sakti hoon.",
                'hindi': f"{prefix} मैं लिसा हूँ, माइकल प्रोजेक्ट की सबसे उन्नत एआई।",
                'english': f"{prefix} I am Lisa, the most advanced AI of the Michael project."
            },
            'capabilities': {
                'hinglish': f"{prefix} Main apps khol sakti hoon, volume/brightness adjust kar sakti hoon, aur system settings control kar sakti hoon. Bas hukum dijiye!",
                'hindi': f"{prefix} मैं ऐप्स खोल सकती हूँ और सिस्टम सेटिंग्स नियंत्रित कर सकती हूँ।",
                'english': f"{prefix} I can open apps, adjust system controls, and manage settings. Just ask!"
            },
            'system_lock': {
                'hinglish': f"{prefix} Suraksha sabse pehle! Computer lock kar rahi hoon. Khayal rakhiyega.",
                'hindi': f"{prefix} कंप्यूटर लॉक हो रहा है।",
                'english': f"{prefix} Safety first! Locking your computer now."
            },
            'volume': {
                'hinglish': f"{prefix} Awaz adjust ho gayi hai. Kya itna kafi hai?",
                'hindi': f"{prefix} आवाज सेट कर दी गई है।",
                'english': f"{prefix} Volume adjusted. Is that better?"
            },
            'brightness': {
                'hinglish': f"{prefix} Roshni kam-zyada kar di hai. Aankhon ka dhayan rakhiye!",
                'hindi': f"{prefix} ब्राइटनेस बदल दी गई है।",
                'english': f"{prefix} Brightness updated. Watch your eyes!"
            },
            'app_open': {
                'hinglish': f"{prefix} App khul raha hai. Kuch aur chahiye?",
                'hindi': f"{prefix} ऐप खुल रहा है।",
                'english': f"{prefix} Launching the application now."
            },
            'terminal_command': {
                'hinglish': f"{prefix} Command execute ho rahi hai. Command prompt check kijiye.",
                'hindi': f"{prefix} कमांड चल रही है।",
                'english': f"{prefix} Executing system command."
            }
        }
        
        return responses.get(intent, {}).get(language, f"{prefix} Kaam ho raha hai.")

# Global instance
language_parser = LanguageParser()

# Global instance
language_parser = LanguageParser()
