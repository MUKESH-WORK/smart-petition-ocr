import { useState, useEffect } from 'react';
import { translateText, translateTexts } from '../services/apiService';

// Client-side dynamic translation cache
const CLIENT_TRANSLATION_CACHE = new Map();

/**
 * Helper to generate cache keys
 */
function getCacheKey(text, targetLang) {
  return `${targetLang}_${(text || '').trim()}`;
}

/**
 * Dynamically translate any arbitrary text via backend LLM translation endpoint
 */
export async function translateDynamic(text, targetLang = 'ta', sourceLang = 'auto') {
  if (!text || typeof text !== 'string' || !text.trim()) return text;
  const clean = text.trim();
  const tl = (targetLang === 'ta' || targetLang === 'tamil') ? 'ta' : 'en';

  const key = getCacheKey(clean, tl);
  if (CLIENT_TRANSLATION_CACHE.has(key)) {
    return CLIENT_TRANSLATION_CACHE.get(key);
  }

  try {
    const res = await translateText(clean, tl, sourceLang);
    if (res && typeof res === 'string') {
      CLIENT_TRANSLATION_CACHE.set(key, res.trim());
      return res.trim();
    }
  } catch (err) {
    console.warn('Dynamic translation warning:', err);
  }

  return clean;
}

/**
 * Dynamically translate a batch of texts
 */
export async function batchTranslateDynamic(texts = [], targetLang = 'ta', sourceLang = 'auto') {
  if (!Array.isArray(texts) || texts.length === 0) return texts;
  const tl = (targetLang === 'ta' || targetLang === 'tamil') ? 'ta' : 'en';

  const uncached = [];
  const uncachedIndices = [];
  const results = [...texts];

  texts.forEach((t, i) => {
    if (!t || typeof t !== 'string' || !t.trim()) return;
    const key = getCacheKey(t.trim(), tl);
    if (CLIENT_TRANSLATION_CACHE.has(key)) {
      results[i] = CLIENT_TRANSLATION_CACHE.get(key);
    } else {
      uncached.push(t.trim());
      uncachedIndices.push(i);
    }
  });

  if (uncached.length === 0) return results;

  try {
    const translatedBatch = await translateTexts(uncached, tl, sourceLang);
    if (Array.isArray(translatedBatch)) {
      translatedBatch.forEach((tr, idx) => {
        const origIndex = uncachedIndices[idx];
        const origText = uncached[idx];
        if (tr && typeof tr === 'string') {
          const key = getCacheKey(origText, tl);
          CLIENT_TRANSLATION_CACHE.set(key, tr.trim());
          results[origIndex] = tr.trim();
        }
      });
    }
  } catch (err) {
    console.warn('Batch dynamic translation warning:', err);
  }

  return results;
}

/**
 * Custom React Hook for dynamically translating any component text reactively
 */
export function useDynamicTranslation(text, targetLang = 'en') {
  const [translated, setTranslated] = useState(text);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!text || typeof text !== 'string' || !text.trim()) {
      setTranslated(text);
      return;
    }

    const tl = (targetLang === 'ta' || targetLang === 'tamil') ? 'ta' : 'en';
    const key = getCacheKey(text.trim(), tl);

    if (CLIENT_TRANSLATION_CACHE.has(key)) {
      setTranslated(CLIENT_TRANSLATION_CACHE.get(key));
      return;
    }

    let isMounted = true;
    setIsLoading(true);

    translateDynamic(text, tl)
      .then((res) => {
        if (isMounted && res) {
          setTranslated(res);
        }
      })
      .catch(() => {
        if (isMounted) setTranslated(text);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [text, targetLang]);

  return { translatedText: translated, isLoading };
}

/**
 * General dynamic translation lookup with background on-the-fly LLM resolution
 */
const INITIAL_DYNAMIC_STORE = {
  ta: {
    'AI Administrative Co-Pilot': 'செயற்கை நுண்ணறிவு நிர்வாக இணை-பைலட்',
    'Government Grievance Pre-Processing': 'அரசு குறை தீர்வு ஆவண முன்-செயலாக்கம்',
    'GDP Assistant': 'மனு ஆவண உதவியாளர்',
    'Grievance Processing': 'குறை தீர்வு செயலாக்கம்',
    'Audit Logs': 'தணிக்கைப் பதிவுகள்',
    'User Management': 'பயனர் மேலாண்மை',
    'Dashboard': 'டாஷ்போர்டு',
    'Backup': 'காப்புப்பிரதி',
    'My Profile': 'எனது சுயவிவரம்',
    'Profile View': 'சுயவிவரப் பார்வை',
    'Log Out': 'வெளியேறு',
    'Sign Out': 'வெளியேறு',
    'Collapse': 'சுருக்கு',
    'Expand': 'விரிவாக்கு',
    'Admin': 'நிர்வாகி',
    'User': 'பயனர்',
    'Welcome, District Administrator': 'வரவேற்பு, மாவட்ட நிர்வாகி',
    'Active Users': 'செயலில் உள்ள பயனர்கள்',
    'Total Petitions': 'மொத்த மனுக்கள்',
    'Success': 'வெற்றி',
    'Failures': 'தோல்விகள்',
    'Recent Petition Trends': 'சமீபத்திய மனு போக்குகள்',
    'Administrative Hierarchy': 'நிர்வாக படிநிலை',
    'CM Grievance Mappings': 'மு.அ குறைதீர்வு வரைபடங்கள்',
    'Manage Hierarchy': 'படிநிலையை நிர்வகி',
    'Manage Mapping': 'வரைபடங்களை நிர்வகி',
    'Recent Activity': 'சமீபத்திய செயல்பாடுகள்',
    'All Users': 'அனைத்து பயனர்கள்',
    'Add User': 'பயனரைச் சேர்',
    'Refresh': 'புதுப்பி',
    'Official Account': 'அதிகாரப்பூர்வ கணக்கு',
    'Department / Section': 'துறை / பிரிவு',
    'Status': 'நிலை',
    'Last Login': 'கடைசி உள்நுழைவு',
    'Actions': 'செயல்கள்',
    'Edit Password': 'கடவுச்சொல் திருத்து',
    'Edit Profile': 'சுயவிவரம் திருத்து',
    'Database Live': 'தரவுத்தளம் நேரலையில் உள்ளது',
    'Database Disconnected': 'தரவுத்தள இணைப்பு துண்டிக்கப்பட்டது',
    'District Administrator': 'மாவட்ட நிர்வாகி',
    'Department Officer': 'துறை அலுவலர்',
    'Department User': 'துறை பயனர்',
    'Revenue Administration': 'வருவாய் நிர்வாகம்',
    'Revenue Inspector': 'வருவாய் ஆய்வாளர்',
    'Tahsildar': 'வட்டாட்சியர்',
    'Special Tahsildar': 'சிறப்பு வட்டாட்சியர்',
    'District Collector': 'மாவட்ட ஆட்சியர்',
    'Assistant Commissioner': 'உதவி ஆணையர்',
    'Deputy Collector': 'துணை ஆட்சியர்',
    'Village Administrative Officer': 'கிராம நிர்வாக அலுவலர்',
    'Zones': 'மண்டலங்கள்',
    'Taluks': 'வட்டங்கள்',
    'Firkas': 'பிர்காக்கள்',
    'Municipalities': 'நகராட்சிகள்',
    'Villages': 'கிராமங்கள்',
    'Wards': 'வார்டுகள்',
    'Departments': 'துறைகள்',
    'Grievance Types': 'குறை வகைகள்',
    'Sub-Types': 'துணை வகைகள்',
    'Officer Mappings': 'அதிகாரி ஒதுக்கீடுகள்'
  }
};

// Seed initial memory cache
Object.entries(INITIAL_DYNAMIC_STORE.ta).forEach(([en, ta]) => {
  CLIENT_TRANSLATION_CACHE.set(getCacheKey(en, 'ta'), ta);
  CLIENT_TRANSLATION_CACHE.set(getCacheKey(ta, 'en'), en);
});

export function getTranslation(lang, key, fallback = '') {
  const text = fallback || key;
  const tl = (lang === 'ta' || lang === 'tamil') ? 'ta' : 'en';
  if (tl === 'en' && fallback) return fallback;

  const cacheKey = getCacheKey(text, tl);
  if (CLIENT_TRANSLATION_CACHE.has(cacheKey)) {
    return CLIENT_TRANSLATION_CACHE.get(cacheKey);
  }

  // Trigger background dynamic translation so next render has it
  translateDynamic(text, tl).then((res) => {
    if (res && res !== text) {
      CLIENT_TRANSLATION_CACHE.set(cacheKey, res);
    }
  });

  return fallback || key;
}

