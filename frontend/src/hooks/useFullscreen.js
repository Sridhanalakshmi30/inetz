import { useState, useEffect, useCallback, useRef } from 'react';

export function useFullscreen({ onExitFullscreen, isActive = true } = {}) {
  const [isFullscreen, setIsFullscreen] = useState(
    Boolean(
      document.fullscreenElement ||
      document.webkitFullscreenElement ||
      document.mozFullScreenElement ||
      document.msFullscreenElement
    )
  );

  const isActiveRef = useRef(isActive);
  isActiveRef.current = isActive;

  const onExitRef = useRef(onExitFullscreen);
  onExitRef.current = onExitFullscreen;

  const enterFullscreen = useCallback(async () => {
    try {
      const elem = document.documentElement;
      if (elem.requestFullscreen) {
        await elem.requestFullscreen();
      } else if (elem.webkitRequestFullscreen) {
        await elem.webkitRequestFullscreen();
      } else if (elem.mozRequestFullScreen) {
        await elem.mozRequestFullScreen();
      } else if (elem.msRequestFullscreen) {
        await elem.msRequestFullscreen();
      } else {
        return false;
      }
      setIsFullscreen(true);
      return true;
    } catch (err) {
      console.warn('Failed to enter fullscreen mode:', err);
      return false;
    }
  }, []);

  const exitFullscreen = useCallback(async () => {
    try {
      if (document.exitFullscreen && document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (document.webkitExitFullscreen && document.webkitFullscreenElement) {
        await document.webkitExitFullscreen();
      } else if (document.mozCancelFullScreen && document.mozFullScreenElement) {
        await document.mozCancelFullScreen();
      } else if (document.msExitFullscreen && document.msFullscreenElement) {
        await document.msExitFullscreen();
      }
      setIsFullscreen(false);
      return true;
    } catch (err) {
      console.warn('Failed to exit fullscreen mode:', err);
      return false;
    }
  }, []);

  useEffect(() => {
    function handleFullscreenChange() {
      const isFull = Boolean(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
      );

      const wasFull = isFullscreen;
      setIsFullscreen(isFull);

      if (!isFull && wasFull && isActiveRef.current && onExitRef.current) {
        onExitRef.current();
      }
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, [isFullscreen]);

  const isSupported =
    typeof document !== 'undefined' &&
    Boolean(
      document.fullscreenEnabled ||
      document.webkitFullscreenEnabled ||
      document.mozFullScreenEnabled ||
      document.msFullscreenEnabled
    );

  return {
    isFullscreen,
    isSupported,
    enterFullscreen,
    exitFullscreen,
  };
}
