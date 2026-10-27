import { useState, useEffect, useCallback, useRef } from 'react';

export function useMediaMonitor({
  onCameraDisabled,
  onMicDisabled,
  onMediaRestored,
  isActive = true,
} = {}) {
  const [mediaStream, setMediaStream] = useState(null);
  const [mediaError, setMediaError] = useState(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);

  const streamRef = useRef(null);
  const failuresRef = useRef({ video: null, audio: null });
  const reportedRef = useRef({ video: false, audio: false });
  const isActiveRef = useRef(isActive);
  isActiveRef.current = isActive;

  const onCamDisabledRef = useRef(onCameraDisabled);
  onCamDisabledRef.current = onCameraDisabled;

  const onMicDisabledRef = useRef(onMicDisabled);
  onMicDisabledRef.current = onMicDisabled;

  const onRestoredRef = useRef(onMediaRestored);
  onRestoredRef.current = onMediaRestored;

  const checkTrackStatus = useCallback(() => {
    if (!streamRef.current) return;
    const stream = streamRef.current;

    const videoTracks = stream.getVideoTracks();
    const audioTracks = stream.getAudioTracks();

    const videoLive = videoTracks.length > 0 && videoTracks[0].readyState === 'live' && videoTracks[0].enabled && !videoTracks[0].muted;
    const audioLive = audioTracks.length > 0 && audioTracks[0].readyState === 'live' && audioTracks[0].enabled && !audioTracks[0].muted;

    setIsCameraActive(videoLive);
    setIsMicActive(audioLive);

    for (const [kind, live, callback] of [
      ['video', videoLive, onCamDisabledRef.current],
      ['audio', audioLive, onMicDisabledRef.current],
    ]) {
      if (live || !isActiveRef.current) {
        failuresRef.current[kind] = null;
        reportedRef.current[kind] = false;
      } else {
        failuresRef.current[kind] ??= Date.now();
        if (Date.now() - failuresRef.current[kind] >= 5000 && !reportedRef.current[kind]) {
          reportedRef.current[kind] = true;
          callback?.();
        }
      }
    }
    if (isActiveRef.current && videoLive && audioLive) onRestoredRef.current?.();
  }, []);

  const requestMedia = useCallback(async () => {
    try {
      setMediaError(null);
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera and microphone access are not supported on this browser.');
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: true,
      });

      streamRef.current?.getTracks().forEach((track) => {
        track.onended = track.onmute = track.onunmute = null;
        track.stop();
      });
      failuresRef.current = { video: null, audio: null };
      reportedRef.current = { video: false, audio: false };
      streamRef.current = stream;
      setMediaStream(stream);
      setIsCameraActive(true);
      setIsMicActive(true);

      const videoTrack = stream.getVideoTracks()[0];
      const audioTrack = stream.getAudioTracks()[0];

      for (const track of [videoTrack, audioTrack].filter(Boolean)) {
        track.onended = checkTrackStatus;
        track.onmute = checkTrackStatus;
        track.onunmute = checkTrackStatus;
      }
      checkTrackStatus();

      return stream;
    } catch (err) {
      console.error('Error accessing camera/microphone:', err);
      let errMsg = 'Failed to access camera or microphone. Please ensure permissions are granted.';
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        errMsg = 'Camera/Microphone permission denied. Please allow camera and mic permissions in your browser settings.';
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        errMsg = 'No camera or microphone device found. Please connect your devices.';
      }
      setMediaError(errMsg);
      throw err;
    }
  }, []);

  const stopMedia = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setMediaStream(null);
      setIsCameraActive(false);
      setIsMicActive(false);
    }
  }, []);

  useEffect(() => {
    const interval = setInterval(checkTrackStatus, 1000);
    return () => {
      clearInterval(interval);
      stopMedia();
    };
  }, [checkTrackStatus, stopMedia]);

  return {
    mediaStream,
    mediaError,
    isCameraActive,
    isMicActive,
    requestMedia,
    stopMedia,
  };
}
