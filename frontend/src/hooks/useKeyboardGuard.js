import { useEffect } from 'react';

// Blocks the keyboard shortcuts most commonly used to leave/replace the
// interview tab: opening a new tab, opening a new window, closing the tab,
// switching tabs with Ctrl+Tab, reloading, toggling fullscreen, and opening
// devtools / view-source (which would let someone read the DOM/answers).
//
// Honesty note: Chrome, Firefox and Edge deliberately do NOT let page
// JavaScript block a handful of these — Ctrl+T, Ctrl+N, Ctrl+W and OS-level
// Alt+Tab are reserved by the browser/OS itself as a security measure, so a
// malicious page can never trap a user inside a tab. preventDefault() on
// those keydown events is a no-op in modern browsers. This hook still
// calls preventDefault + reports them, which (a) blocks them in the older
// or embedded/kiosk-mode browsers where it does work, and (b) means every
// *attempt* is still logged as a proctoring event even when the browser
// refuses to block the action. The real backstop for a genuine tab switch
// is still useTabDetection's visibilitychange listener and
// useFocusDetection's blur listener — unchanged, and what actually enforces
// this.
const BLOCKED_COMBOS = [
  { name: 'CTRL_T', test: (e) => e.ctrlKey && !e.altKey && key(e) === 't' },
  { name: 'CTRL_N', test: (e) => e.ctrlKey && !e.altKey && key(e) === 'n' },
  { name: 'CTRL_W', test: (e) => e.ctrlKey && !e.altKey && key(e) === 'w' },
  { name: 'CTRL_SHIFT_T', test: (e) => e.ctrlKey && e.shiftKey && key(e) === 't' },
  { name: 'CTRL_SHIFT_N', test: (e) => e.ctrlKey && e.shiftKey && key(e) === 'n' },
  { name: 'CTRL_TAB', test: (e) => e.ctrlKey && !e.shiftKey && e.key === 'Tab' },
  { name: 'CTRL_SHIFT_TAB', test: (e) => e.ctrlKey && e.shiftKey && e.key === 'Tab' },
  { name: 'ALT_TAB', test: (e) => e.altKey && e.key === 'Tab' },
  { name: 'RELOAD_F5', test: (e) => e.key === 'F5' },
  { name: 'RELOAD_CTRL_R', test: (e) => e.ctrlKey && key(e) === 'r' },
  { name: 'FULLSCREEN_TOGGLE', test: (e) => e.key === 'F11' },
  { name: 'DEVTOOLS_F12', test: (e) => e.key === 'F12' },
  { name: 'DEVTOOLS_COMBO', test: (e) => e.ctrlKey && e.shiftKey && ['i', 'j', 'c'].includes(key(e)) },
  { name: 'VIEW_SOURCE', test: (e) => e.ctrlKey && key(e) === 'u' },
  { name: 'PRINT', test: (e) => e.ctrlKey && key(e) === 'p' },
];

function key(e) {
  return typeof e.key === 'string' ? e.key.toLowerCase() : '';
}

export function useKeyboardGuard({ enabled, onBlocked }) {
  useEffect(() => {
    if (!enabled) return undefined;

    function handleKeyDown(e) {
      const combo = BLOCKED_COMBOS.find((c) => c.test(e));
      if (!combo) return;
      e.preventDefault();
      e.stopPropagation();
      if (e.repeat) return;
      onBlocked && onBlocked(combo.name);
    }

    // Capture phase so we see the key before the browser's own shortcut
    // routing has a chance to act on it.
    window.addEventListener('keydown', handleKeyDown, true);
    return () => window.removeEventListener('keydown', handleKeyDown, true);
  }, [enabled, onBlocked]);
}
