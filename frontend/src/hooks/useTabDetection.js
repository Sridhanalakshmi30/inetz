import { useState, useEffect, useRef } from 'react';

export function useTabDetection({ onTabSwitch, isActive = true } = {}) {
  const [isTabVisible, setIsTabVisible] = useState(!document.hidden);
  const hiddenTimeRef = useRef(null);

  const isActiveRef = useRef(isActive);
  isActiveRef.current = isActive;

  const onTabSwitchRef = useRef(onTabSwitch);
  onTabSwitchRef.current = onTabSwitch;

  useEffect(() => {
    function handleVisibilityChange() {
      const isHidden = document.hidden;
      setIsTabVisible(!isHidden);

      if (isHidden) {
        hiddenTimeRef.current = Date.now();
        if (isActiveRef.current && onTabSwitchRef.current) {
          onTabSwitchRef.current({ action: 'hidden' });
        }
      } else {
        if (hiddenTimeRef.current) {
          const durationSeconds = (Date.now() - hiddenTimeRef.current) / 1000;
          hiddenTimeRef.current = null;
          if (isActiveRef.current && onTabSwitchRef.current) {
            onTabSwitchRef.current({ action: 'visible', durationSeconds });
          }
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return { isTabVisible };
}
