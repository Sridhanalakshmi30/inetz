import { useEffect, useRef, useState } from 'react';
import { loadFaceApiModels, isFaceApiLoaded, faceapi } from './faceApiLoader.js';
import { createMultipleFaceTracker } from './multipleFaceTracker.js';

export function useFaceDetection({
  videoRef,
  isActive = false,
  onNoFaceDetected,
  onMultipleFacesDetected,
  onFaceOk,
  detectionIntervalMs = 500,
  noFaceThreshold = 16,
} = {}) {
  const [detection, setDetection] = useState({ status: 'loading', count: null, boxes: [] });
  const noFaceCountRef = useRef(0);
  const multipleTrackerRef = useRef(createMultipleFaceTracker());

  const isActiveRef = useRef(isActive);
  isActiveRef.current = isActive;

  const onNoFaceRef = useRef(onNoFaceDetected);
  onNoFaceRef.current = onNoFaceDetected;

  const onMultipleFacesRef = useRef(onMultipleFacesDetected);
  onMultipleFacesRef.current = onMultipleFacesDetected;

  const onFaceOkRef = useRef(onFaceOk);
  onFaceOkRef.current = onFaceOk;

  useEffect(() => {
    loadFaceApiModels().catch((e) => {
      console.warn('Face detection model init failed:', e);
    });
  }, []);

  useEffect(() => {
    if (!isActive) {
      setDetection({ status: 'waiting', count: null, boxes: [] });
      return;
    }

    let isCancelled = false;
    let detecting = false;
    let reported = null;
    let healthyCount = 0;
    noFaceCountRef.current = 0;
    multipleTrackerRef.current.reset();

    const intervalId = setInterval(async () => {
      if (isCancelled || !isActiveRef.current) return;

      if (detecting) return;
      const video = videoRef?.current;
      const track = video?.srcObject?.getVideoTracks()[0];
      if (
        document.hidden ||
        !track || track.readyState !== 'live' || !track.enabled || track.muted ||
        !video ||
        video.readyState < 2 ||
        video.paused ||
        video.ended ||
        video.videoWidth === 0
      ) {
        noFaceCountRef.current = 0;
        multipleTrackerRef.current.reset();
        healthyCount = 0;
        setDetection({ status: 'waiting', count: null, boxes: [] });
        return;
      }

      detecting = true;
      try {
        if (!isFaceApiLoaded()) {
          await loadFaceApiModels();
          if (!isFaceApiLoaded()) {
            setDetection({ status: 'error', count: null, boxes: [] });
            return;
          }
        }
        if (isCancelled || !isActiveRef.current) return;

        const options = new faceapi.SsdMobilenetv1Options({
          minConfidence: 0.4,
          maxResults: 10,
        });

        const detections = await faceapi.detectAllFaces(video, options);

        if (isCancelled || !isActiveRef.current) return;

        // Ignore results if the camera stopped or the tab was hidden during inference.
        if (document.hidden || track.muted || track.readyState !== 'live' || !track.enabled) {
          noFaceCountRef.current = 0;
          multipleTrackerRef.current.reset();
          healthyCount = 0;
          return;
        }
        const count = detections.length;
        setDetection({ status: 'active', count, boxes: detections.map(({ box }) => ({
          x: box.x / video.videoWidth, y: box.y / video.videoHeight,
          width: box.width / video.videoWidth, height: box.height / video.videoHeight,
        })) });
        const multipleOccurrence = multipleTrackerRef.current.sample(count, performance.now());

        if (count !== 1) healthyCount = 0;
        if (count === 0) {
          noFaceCountRef.current += 1;

          if (noFaceCountRef.current >= noFaceThreshold && reported !== 'no-face') {
            if (onNoFaceRef.current) {
              onNoFaceRef.current();
            }
            reported = 'no-face';
          }
        } else if (count > 1) {
          noFaceCountRef.current = 0;

          if (multipleOccurrence) {
            if (onMultipleFacesRef.current) {
              await onMultipleFacesRef.current({ faceCount: count });
              multipleTrackerRef.current.acknowledge(performance.now());
            }
            reported = 'multiple-faces';
          }
        } else {
          healthyCount += 1;
          if (healthyCount >= 2) reported = null;
          // Exactly 1 face
          noFaceCountRef.current = 0;
          if (onFaceOkRef.current) {
            onFaceOkRef.current();
          }
        }
      } catch (err) {
        if (isCancelled) return;
        setDetection({ status: 'error', count: null, boxes: [] });
        noFaceCountRef.current = 0;
        multipleTrackerRef.current.reset();
        healthyCount = 0;
        console.warn('Face detection execution error:', err);
      } finally {
        detecting = false;
      }
    }, detectionIntervalMs);

    return () => {
      isCancelled = true;
      clearInterval(intervalId);
    };
  }, [isActive, videoRef, detectionIntervalMs, noFaceThreshold]);
  return detection;
}
