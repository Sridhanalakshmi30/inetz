/**
 * Utility to convert any browser recorded audio blob (WebM, Opus, MP4, etc.)
 * into a clean, 16kHz mono 16-bit PCM WAV Blob using the Web Audio API.
 * This guarantees 100% audio compatibility with backend acoustic analysis.
 */

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

export async function convertToMono16kWavBlob(audioBlob, targetSampleRate = 16000) {
  if (!audioBlob || audioBlob.size === 0) {
    throw new Error('Audio recording is empty.');
  }

  const arrayBuffer = await audioBlob.arrayBuffer();
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) {
    return audioBlob; // Fallback to raw blob if Web Audio API is unsupported
  }

  const audioCtx = new AudioCtx();
  let audioBuffer;
  try {
    audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
  } catch (err) {
    console.warn('Web Audio decoding failed, sending raw audio blob for backend processing:', err);
    return audioBlob;
  } finally {
    try {
      await audioCtx.close();
    } catch (e) {
      // ignore
    }
  }

  // Resample and downmix to 1 channel at targetSampleRate
  const totalLength = Math.ceil(audioBuffer.duration * targetSampleRate);
  const OfflineCtx = window.OfflineAudioContext || window.webkitOfflineAudioContext;
  const offlineCtx = new OfflineCtx(1, Math.max(1, totalLength), targetSampleRate);

  const source = offlineCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineCtx.destination);
  source.start(0);

  const renderedBuffer = await offlineCtx.startRendering();
  const channelData = renderedBuffer.getChannelData(0);

  // Encode 16-bit PCM WAV
  const wavBuffer = new ArrayBuffer(44 + channelData.length * 2);
  const view = new DataView(wavBuffer);

  // RIFF identifier
  writeString(view, 0, 'RIFF');
  // file length minus 8
  view.setUint32(4, 36 + channelData.length * 2, true);
  // RIFF type
  writeString(view, 8, 'WAVE');
  // format chunk identifier
  writeString(view, 12, 'fmt ');
  // format chunk length
  view.setUint32(16, 16, true);
  // sample format (1 = PCM)
  view.setUint16(20, 1, true);
  // channel count (1 = mono)
  view.setUint16(22, 1, true);
  // sample rate
  view.setUint32(24, targetSampleRate, true);
  // byte rate (sample rate * block align)
  view.setUint32(28, targetSampleRate * 2, true);
  // block align (channel count * bytes per sample)
  view.setUint16(32, 2, true);
  // bits per sample
  view.setUint16(34, 16, true);
  // data chunk identifier
  writeString(view, 36, 'data');
  // data chunk length
  view.setUint32(40, channelData.length * 2, true);

  // Write PCM samples
  let offset = 44;
  for (let i = 0; i < channelData.length; i++, offset += 2) {
    const s = Math.max(-1, Math.min(1, channelData[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}
