import { useState, useCallback, useRef, useEffect } from 'react';
import { useMediaMonitor } from './useMediaMonitor.js';
import { useFullscreen } from './useFullscreen.js';
import { useTabDetection } from './useTabDetection.js';
import { useFocusDetection } from './useFocusDetection.js';
import { useKeyboardGuard } from './useKeyboardGuard.js';
import { useFaceDetection } from './useFaceDetection.js';
import { loadFaceApiModels } from './faceApiLoader.js';

import {
  startProctoring,
  sendProctoringEvent,
} from '../services/proctoringApi.js';

const LEAVE_EVENTS = new Set(['TAB_SWITCH', 'WINDOW_BLUR', 'FULLSCREEN_EXIT']);
const LEAVE_SHORTCUTS = new Set(['CTRL_T', 'CTRL_N', 'CTRL_W', 'CTRL_SHIFT_T', 'CTRL_SHIFT_N', 'CTRL_TAB', 'CTRL_SHIFT_TAB', 'ALT_TAB', 'FULLSCREEN_TOGGLE']);

export function useProctoring({ sessionId, videoRef, maxViolations = 4 } = {}) {
  const [phase, setPhase] = useState('CHECKING'); // 'CHECKING' | 'ACTIVE' | 'WARNING' | 'TERMINATED'
  const [violationCount, setViolationCount] = useState(0);
  const [maxViolationsState, setMaxViolationsState] = useState(maxViolations);
  const [lastViolation, setLastViolation] = useState(null);
  const [terminationReason, setTerminationReason] = useState(null);
  const [detectorError, setDetectorError] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  // Instant, client-only signal used to lock the screen the moment focus is
  // lost — does NOT wait for the server round-trip that reportEvent() does,
  // because the whole point is to hide the question before the candidate
  // can read it in the background/on another app.
  const [windowFocused, setWindowFocused] = useState(typeof document !== 'undefined' ? document.hasFocus() : true);

  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  const questionNumberRef = useRef(questionNumber);
  questionNumberRef.current = questionNumber;

  const phaseRef = useRef(phase);
  phaseRef.current = phase;

  const leaveReportedRef = useRef(false);
  const eventQueueRef = useRef(Promise.resolve());
  const pendingEventsRef = useRef([]);
  const localViolationCountRef = useRef(0);

  // Handle reporting violation event to backend
  const handleViolationEvent = useCallback(
    async (eventType, { durationSeconds, metadata } = {}) => {
      // Don't report if already terminated or still in checking
      if (phaseRef.current === 'TERMINATED' || phaseRef.current === 'CHECKING') {
        return;
      }

      if (LEAVE_EVENTS.has(eventType) ||
          (eventType === 'SHORTCUT_BLOCKED' && LEAVE_SHORTCUTS.has(metadata?.combo))) {
        // One departure can emit blur, visibility and fullscreen events.
        // Count it once until the candidate returns to the interview.
        if (leaveReportedRef.current) return;
        leaveReportedRef.current = true;
      }

      const sid = sessionIdRef.current;
      if (!sid) {
        pendingEventsRef.current.push({ eventType, durationSeconds, metadata });
        // Face policy is decided by the server, including its configured threshold.
        if (eventType === 'NO_FACE_DETECTED' || eventType === 'MULTIPLE_FACES_DETECTED') return;
        // Fallback local tracking if session not yet registered
        if (eventType === 'CAMERA_DISABLED' || eventType === 'MIC_DISABLED') {
          setPhase('WARNING');
          setLastViolation({ eventType, action: 'WARN' });
          return;
        }

          const nextCount = ++localViolationCountRef.current;
          if (nextCount >= maxViolationsState) {
            phaseRef.current = 'TERMINATED';
            setPhase('TERMINATED');
          } else {
            const action = nextCount === maxViolationsState - 1 ? 'FINAL_WARN' : 'WARN';
            setPhase('WARNING');
            setLastViolation({ eventType, action });
          }
          setViolationCount(nextCount);
        return;
      }

      const report = async () => {
      if (phaseRef.current === 'TERMINATED') return;
      try {
        const response = await sendProctoringEvent(sid, eventType, {
          questionNumber: questionNumberRef.current,
          durationSeconds,
          metadata,
        });

        if (response.violation_count !== undefined) {
          setViolationCount(response.violation_count);
        }
        if (response.max_violations !== undefined) {
          setMaxViolationsState(response.max_violations);
        }

        if (response.action === 'TERMINATE') {
          setTerminationReason(response.termination_reason || response.message);
          phaseRef.current = 'TERMINATED';
          setPhase('TERMINATED');
        } else if (response.action === 'WARN' || response.action === 'FINAL_WARN') {
          setPhase('WARNING');
          setLastViolation({
            eventType,
            action: response.action,
            message: response.message,
          });
        }
      } catch (err) {
        console.warn('Failed to send proctoring event:', err);
      }
      };
      eventQueueRef.current = eventQueueRef.current.then(report);
      await eventQueueRef.current;
    },
    [maxViolationsState]
  );

  // Hook 1: Media Monitor (Camera + Microphone)
  const isMonitoringActive = phase === 'ACTIVE' || phase === 'WARNING';

  const mediaMonitor = useMediaMonitor({
    isActive: isMonitoringActive,
    onCameraDisabled: () => {
      handleViolationEvent('CAMERA_DISABLED', {
        metadata: { reason: 'CAMERA_LOST' },
      });
    },
    onMicDisabled: () => {
      handleViolationEvent('MIC_DISABLED', {
        metadata: { reason: 'MIC_LOST' },
      });
    },
  });

  // Hook 2: Fullscreen
  const fullscreen = useFullscreen({
    isActive: isMonitoringActive,
    onExitFullscreen: () => {
      handleViolationEvent('FULLSCREEN_EXIT');
    },
  });

  // Hook 3: Tab switch detection
  const { isTabVisible } = useTabDetection({
    isActive: isMonitoringActive,
    onTabSwitch: ({ action, durationSeconds }) => {
      if (action === 'hidden') {
        handleViolationEvent('TAB_SWITCH');
      }
    },
  });

  // Hook 4: Window Focus detection
  useFocusDetection({
    isActive: isMonitoringActive,
    onWindowBlur: ({ action }) => {
      if (action === 'blur') {
        setWindowFocused(false);
        handleViolationEvent('WINDOW_BLUR');
      } else if (action === 'focus') {
        setWindowFocused(true);
      }
    },
  });

  useEffect(() => {
    if (windowFocused && isTabVisible && fullscreen.isFullscreen) {
      leaveReportedRef.current = false;
    }
  }, [windowFocused, isTabVisible, fullscreen.isFullscreen]);

  // Hook 5: Keyboard Guard (blocks reload, devtools, shortcut combos)
  useKeyboardGuard({
    enabled: isMonitoringActive,
    onBlocked: (combo) => handleViolationEvent('SHORTCUT_BLOCKED', { metadata: { combo } }),
  });

  // Hook 6: Face Detection
  const faceDetection = useFaceDetection({
    videoRef,
    isActive: isMonitoringActive && Boolean(sessionId),
    onNoFaceDetected: () => {
      handleViolationEvent('NO_FACE_DETECTED');
    },
    onMultipleFacesDetected: ({ faceCount }) => {
      return handleViolationEvent('MULTIPLE_FACES_DETECTED', {
        metadata: { faceCount },
      });
    },
  });

  // Sync state if sessionId changes
  useEffect(() => {
    if (sessionId) {
      const initialize = async () => {
          let data = await startProctoring(sessionId);
          // Preserve violations that happened while the first AI question loaded.
          for (const event of pendingEventsRef.current.splice(0)) {
            const result = await sendProctoringEvent(sessionId, event.eventType, event);
            if (result.action === 'WARN' || result.action === 'FINAL_WARN') {
              setPhase('WARNING');
              setLastViolation({ eventType: event.eventType, action: result.action, message: result.message });
            }
            data = { ...data, ...result, status: result.action === 'TERMINATE' ? 'TERMINATED' : data.status };
          }
          if (data.status === 'TERMINATED') {
            setTerminationReason(data.termination_reason || data.paused_reason || data.message);
            phaseRef.current = 'TERMINATED';
            setPhase(data.status);
          }
          if (data.violation_count !== undefined) {
            setViolationCount(data.violation_count);
          }
          if (data.max_violations !== undefined) {
            setMaxViolationsState(data.max_violations);
          }
      };
      eventQueueRef.current = eventQueueRef.current.then(initialize).catch((err) => {
        console.warn('Failed to initialize proctoring:', err);
      });
    }
  }, [sessionId]);

  const runSecurityCheck = useCallback(async () => {
    try {
      setDetectorError(null);
      await mediaMonitor.requestMedia();
      if (!await fullscreen.enterFullscreen()) return false;
      if (!await loadFaceApiModels()) {
        setDetectorError('Face detection could not load. Check your connection and retry before starting the interview.');
        return false;
      }

      if (sessionIdRef.current) {
        await startProctoring(sessionIdRef.current);
      }

      setPhase('ACTIVE');
      return true;
    } catch (err) {
      console.warn('Security check failed:', err);
      return false;
    }
  }, [mediaMonitor, fullscreen]);

  const dismissWarning = useCallback(async () => {
    if (phaseRef.current === 'TERMINATED') return;
    if (!fullscreen.isFullscreen && !await fullscreen.enterFullscreen()) return;
    if (document.hidden || !document.hasFocus()) return;
    leaveReportedRef.current = false;
    setLastViolation(null);
    if (phaseRef.current === 'WARNING') {
      setPhase('ACTIVE');
    }
  }, [fullscreen]);

  // Instant screen lock: true the moment the window loses OS focus OR
  // fullscreen is exited, before any server round-trip. ProctoringGuard
  // renders an opaque overlay whenever this is true so the question/answer
  // are hidden while the candidate is looking at the Start Menu, another
  // app, or a second monitor — we can't stop them opening it, but we can
  // make sure the interview content isn't visible while they do.
  // Fullscreen loss only counts toward the lock when the Fullscreen API is
  // actually supported — otherwise fullscreen.isFullscreen is permanently
  // false and this would softlock the interview on browsers that don't
  // support it (a handful of mobile browsers).
  const locked =
    (phase === 'ACTIVE' || phase === 'WARNING') &&
    (!windowFocused || !isTabVisible || (fullscreen.isSupported && !fullscreen.isFullscreen));
  const lockedReason = !locked ? null : !windowFocused ? 'BLUR' : 'FULLSCREEN_EXIT';

  return {
    phase,
    violationCount,
    maxViolations: maxViolationsState,
    lastViolation,
    terminationReason,
    faceDetection,
    mediaStream: mediaMonitor.mediaStream,
    mediaError: detectorError || mediaMonitor.mediaError,
    setQuestionNumber,
    runSecurityCheck,
    dismissWarning,
    reportViolation: handleViolationEvent,
    locked,
    lockedReason,
    enterFullscreen: fullscreen.enterFullscreen,
  };
}
