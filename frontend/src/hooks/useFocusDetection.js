import { useState, useEffect, useRef } from 'react';

export function useFocusDetection({ onWindowBlur, isActive = true } = {}) {
  const [isWindowFocused, setIsWindowFocused] = useState(document.hasFocus());
  const blurTimeRef = useRef(null);

  const isActiveRef = useRef(isActive);
  isActiveRef.current = isActive;

  const onBlurRef = useRef(onWindowBlur);
  onBlurRef.current = onWindowBlur;

  useEffect(() => {
    function handleBlur() {
      setIsWindowFocused(false);
      blurTimeRef.current = Date.now();
      if (isActiveRef.current && onBlurRef.current) {
        onBlurRef.current({ action: 'blur' });
      }
    }

    function handleFocus() {
      setIsWindowFocused(true);
      if (blurTimeRef.current) {
        const durationSeconds = (Date.now() - blurTimeRef.current) / 1000;
        blurTimeRef.current = null;
        if (isActiveRef.current && onBlurRef.current) {
          onBlurRef.current({ action: 'focus', durationSeconds });
        }
      }
    }

    window.addEventListener('blur', handleBlur);
    window.addEventListener('focus', handleFocus);

    return () => {
      window.removeEventListener('blur', handleBlur);
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  return { isWindowFocused };
}
