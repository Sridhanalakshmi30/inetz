"""
Voice verification and speaker embedding service.
Extracts speaker embeddings from candidate speech and compares them against
a baseline captured during the security check to ensure voice authenticity.

Privacy & Biometric Guarantee:
- Ephemeral in-memory storage only.
- Raw audio recordings are never permanently stored and are deleted immediately.
- Embeddings are purged from memory when the interview ends.
"""
import io
import os
import wave
import struct
import numpy as np
from scipy import signal, fftpack
from typing import Optional, Dict, Any, Tuple

try:
    import soundfile as sf
except ImportError:
    sf = None

try:
    import av
except ImportError:
    av = None

# Default similarity threshold (configurable via env var for testing across mics/laptops)
DEFAULT_VOICE_THRESHOLD = float(os.getenv("VOICE_SIMILARITY_THRESHOLD", "0.68"))

# In-memory ephemeral voice embeddings: key -> { 'embedding': np.ndarray, 'created_at': ... }
# Key can be candidate_id or session_id
_EPHEMERAL_EMBEDDINGS: Dict[str, Dict[str, Any]] = {}


def _read_audio_to_mono_16k(audio_source: Any) -> Tuple[np.ndarray, int]:
    """
    Reads audio from a file path, bytes, or file-like object and returns
    a mono 16kHz float32 numpy array normalized to [-1.0, 1.0].
    Supports WAV, WebM, OGG, Opus, MP4, AAC, and standard audio formats.
    """
    target_sr = 16000
    data = None
    sr = None

    # 1. Try PyAV (av) - excellent for WebM, Opus, Ogg, MP4, AAC, and WAV
    if av is not None:
        try:
            container = None
            if isinstance(audio_source, (str, os.PathLike)) and os.path.exists(audio_source):
                container = av.open(str(audio_source))
            elif isinstance(audio_source, bytes) and len(audio_source) > 0:
                container = av.open(io.BytesIO(audio_source))

            if container is not None and len(container.streams.audio) > 0:
                resampler = av.AudioResampler(format="fltp", layout="mono", rate=target_sr)
                frames_list = []
                for frame in container.decode(audio=0):
                    for resampled in resampler.resample(frame):
                        frames_list.append(resampled.to_ndarray()[0])
                for resampled in resampler.resample(None):
                    frames_list.append(resampled.to_ndarray()[0])
                if frames_list:
                    data = np.concatenate(frames_list, axis=0).astype(np.float32)
                    sr = target_sr
        except Exception:
            data = None
            sr = None

    # 2. Try soundfile
    if data is None and sf is not None:
        try:
            if isinstance(audio_source, (str, os.PathLike)) and os.path.exists(audio_source):
                data, sr = sf.read(audio_source, dtype="float32")
            elif isinstance(audio_source, bytes) and len(audio_source) > 0:
                data, sr = sf.read(io.BytesIO(audio_source), dtype="float32")
        except Exception:
            data = None
            sr = None

    # 3. Fallback to standard wave module if soundfile failed or is a standard WAV
    if data is None:
        try:
            wav_file = None
            if isinstance(audio_source, (str, os.PathLike)) and os.path.exists(audio_source):
                wav_file = wave.open(str(audio_source), "rb")
            elif isinstance(audio_source, bytes) and len(audio_source) > 0:
                wav_file = wave.open(io.BytesIO(audio_source), "rb")

            if wav_file is not None:
                n_channels = wav_file.getnchannels()
                sampwidth = wav_file.getsampwidth()
                sr = wav_file.getframerate()
                n_frames = wav_file.getnframes()
                raw_bytes = wav_file.readframes(n_frames)
                wav_file.close()

                if sampwidth == 2:
                    raw_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                elif sampwidth == 4:
                    raw_data = np.frombuffer(raw_bytes, dtype=np.int32).astype(np.float32) / 2147483648.0
                elif sampwidth == 1:
                    raw_data = (np.frombuffer(raw_bytes, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
                else:
                    raw_data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

                if n_channels > 1:
                    raw_data = raw_data.reshape(-1, n_channels)
                data = raw_data
        except Exception:
            pass

    if data is None or len(data) == 0:
        raise ValueError("Could not decode audio input for voice verification.")

    # Convert to mono if multichannel
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # Resample to 16kHz if necessary
    if sr != target_sr and len(data) > 0:
        num_target_samples = int(len(data) * target_sr / sr)
        data = signal.resample(data, num_target_samples).astype(np.float32)
        sr = target_sr

    # Ensure finite values
    data = np.nan_to_num(data, nan=0.0, posinf=1.0, neginf=-1.0)
    return data, target_sr


def _mel_filterbank(num_filters: int = 40, n_fft: int = 512, sample_rate: int = 16000) -> np.ndarray:
    """Constructs Mel-filterbank matrix."""
    low_freq = 80.0
    high_freq = sample_rate / 2.0
    low_mel = 2595 * np.log10(1 + low_freq / 700.0)
    high_mel = 2595 * np.log10(1 + high_freq / 700.0)
    mel_points = np.linspace(low_mel, high_mel, num_filters + 2)
    hz_points = 700 * (10 ** (mel_points / 2595.0) - 1)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)

    fbank = np.zeros((num_filters, int(np.floor(n_fft / 2 + 1))))
    for m in range(1, num_filters + 1):
        f_m_minus = bin_points[m - 1]
        f_m = bin_points[m]
        f_m_plus = bin_points[m + 1]

        for k in range(f_m_minus, f_m):
            if f_m != f_m_minus:
                fbank[m - 1, k] = (k - bin_points[m - 1]) / (bin_points[m] - bin_points[m - 1])
        for k in range(f_m, f_m_plus):
            if f_m_plus != f_m:
                fbank[m - 1, k] = (bin_points[m + 1] - k) / (bin_points[m + 1] - bin_points[m])

    return fbank


def extract_voice_embedding(audio_source: Any) -> np.ndarray:
    """
    Extracts a dense, L2-normalized 192-dimensional acoustic speaker embedding vector
    from speech audio using spectral filterbanks, MFCCs, deltas, and statistical pooling.
    """
    y, sr = _read_audio_to_mono_16k(audio_source)
    if len(y) < sr * 0.5:
        # Pad with subtle noise or zero if under 0.5 sec
        y = np.pad(y, (0, max(0, int(sr * 0.5) - len(y))), mode="constant")

    # Pre-emphasis filter
    y_pre = np.append(y[0], y[1:] - 0.97 * y[:-1])

    # Frame framing: 25ms frame, 10ms hop
    frame_len = int(0.025 * sr)
    frame_step = int(0.010 * sr)
    num_frames = 1 + int(np.floor((len(y_pre) - frame_len) / frame_step))
    if num_frames <= 0:
        num_frames = 1
        frames = np.pad(y_pre, (0, max(0, frame_len - len(y_pre))), mode="constant")[np.newaxis, :]
    else:
        indices = np.tile(np.arange(0, frame_len), (num_frames, 1)) + np.tile(
            np.arange(0, num_frames * frame_step, frame_step), (frame_len, 1)
        ).T
        frames = y_pre[indices]

    # Hamming window
    window = np.hamming(frame_len)
    frames = frames * window

    # FFT & Power spectrum
    n_fft = 512
    mag_frames = np.absolute(np.fft.rfft(frames, n_fft))
    pow_frames = (1.0 / n_fft) * (mag_frames ** 2)

    # Filterbank energies
    fbank = _mel_filterbank(num_filters=40, n_fft=n_fft, sample_rate=sr)
    filter_banks = np.dot(pow_frames, fbank.T)
    filter_banks = np.where(filter_banks == 0, np.finfo(float).eps, filter_banks)
    log_filter_banks = np.log(filter_banks)

    # MFCCs (13 coefficients)
    mfcc = fftpack.dct(log_filter_banks, type=2, axis=1, norm="ortho")[:, :13]

    # Cepstral Mean and Variance Normalization (CMVN)
    mfcc_mean = np.mean(mfcc, axis=0, keepdims=True)
    mfcc_std = np.std(mfcc, axis=0, keepdims=True) + 1e-6
    mfcc_norm = (mfcc - mfcc_mean) / mfcc_std

    # Delta MFCCs
    def compute_deltas(feat, N=2):
        d = np.zeros_like(feat)
        for t in range(len(feat)):
            num = np.zeros(feat.shape[1])
            denom = 0
            for n in range(1, N + 1):
                t_plus = min(len(feat) - 1, t + n)
                t_minus = max(0, t - n)
                num += n * (feat[t_plus] - feat[t_minus])
                denom += 2 * (n ** 2)
            d[t] = num / max(denom, 1e-6)
        return d

    delta_mfcc = compute_deltas(mfcc_norm)
    delta2_mfcc = compute_deltas(delta_mfcc)

    # Spectral centroid & roll-off per frame
    freq_bins = np.linspace(0, sr / 2, mag_frames.shape[1])
    sum_mag = np.sum(mag_frames, axis=1, keepdims=True) + 1e-9
    spectral_centroid = (np.sum(mag_frames * freq_bins, axis=1, keepdims=True) / sum_mag) / (sr / 2)

    # Formant energy distribution across 4 spectral bands
    band_size = mag_frames.shape[1] // 4
    band1 = np.mean(mag_frames[:, :band_size], axis=1, keepdims=True) / sum_mag
    band2 = np.mean(mag_frames[:, band_size:2*band_size], axis=1, keepdims=True) / sum_mag
    band3 = np.mean(mag_frames[:, 2*band_size:3*band_size], axis=1, keepdims=True) / sum_mag
    band4 = np.mean(mag_frames[:, 3*band_size:], axis=1, keepdims=True) / sum_mag

    combined_features = np.hstack([
        mfcc_norm,
        delta_mfcc,
        delta2_mfcc,
        log_filter_banks[:, :8],
        spectral_centroid,
        band1,
        band2,
        band3,
        band4,
    ])

    # Temporal statistical pooling across all frames (Mean, Std, 10th-perc, 90th-perc)
    mean_vec = np.mean(combined_features, axis=0)
    std_vec = np.std(combined_features, axis=0)
    p10_vec = np.percentile(combined_features, 10, axis=0)
    p90_vec = np.percentile(combined_features, 90, axis=0)

    raw_embedding = np.concatenate([mean_vec, std_vec, p10_vec, p90_vec])

    # Truncate / pad to exactly 192 dimensions
    if len(raw_embedding) > 192:
        embedding = raw_embedding[:192]
    else:
        embedding = np.pad(raw_embedding, (0, 192 - len(raw_embedding)), mode="constant")

    # L2 normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm

    return embedding.astype(np.float32)



def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """Computes cosine similarity between two 1D vectors."""
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(vec_a, vec_b) / (norm_a * norm_b))


def register_baseline_embedding(
    key: str,
    audio_source: Any,
    candidate_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Registers the baseline voice embedding from the security check audio.
    Immediately converts audio to embedding and discards raw audio.
    Accepts raw audio or an existing 1D numpy embedding vector.
    """
    if isinstance(audio_source, np.ndarray) and audio_source.ndim == 1 and len(audio_source) >= 50:
        embedding = audio_source.astype(np.float32)
    else:
        embedding = extract_voice_embedding(audio_source)

    str_key = str(key).strip()

    _EPHEMERAL_EMBEDDINGS[str_key] = {
        "embedding": embedding,
        "candidate_id": candidate_id,
        "dimensions": len(embedding),
    }

    if candidate_id is not None:
        _EPHEMERAL_EMBEDDINGS[f"cand_{candidate_id}"] = _EPHEMERAL_EMBEDDINGS[str_key]

    return {
        "success": True,
        "key": str_key,
        "dimensions": len(embedding),
        "message": "Voice baseline captured successfully. Raw audio discarded.",
    }


def link_session_embedding(session_id: Any, candidate_id: Any) -> bool:
    """Links an existing candidate's voice embedding to a new session ID."""
    if candidate_id is None or session_id is None:
        return False
    baseline = get_baseline_embedding(str(candidate_id))
    if baseline is not None:
        str_key = str(session_id).strip()
        _EPHEMERAL_EMBEDDINGS[str_key] = {
            "embedding": baseline,
            "candidate_id": candidate_id,
            "dimensions": len(baseline),
        }
        return True
    return False


def get_baseline_embedding(key: str) -> Optional[np.ndarray]:
    """Retrieves ephemeral baseline embedding for a session or candidate."""
    str_key = str(key).strip()
    entry = _EPHEMERAL_EMBEDDINGS.get(str_key)
    if entry:
        return entry["embedding"]
    cand_entry = _EPHEMERAL_EMBEDDINGS.get(f"cand_{str_key}")
    if cand_entry:
        return cand_entry["embedding"]
    return None


def verify_voice(
    key: str,
    audio_source: Any,
    threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Compares the voice in `audio_source` against the baseline embedding for `key`.
    Returns match boolean, similarity score, and evaluation status.
    """
    baseline = get_baseline_embedding(key)
    thresh = threshold if threshold is not None else DEFAULT_VOICE_THRESHOLD

    if baseline is None:
        # If baseline wasn't captured or already cleared, log warning and pass gracefully
        return {
            "match": True,
            "similarity": 1.0,
            "threshold": thresh,
            "status": "NO_BASELINE",
            "message": "No baseline voice embedding registered for this session.",
        }

    current_embedding = extract_voice_embedding(audio_source)
    sim = cosine_similarity(baseline, current_embedding)
    is_match = sim >= thresh

    return {
        "match": is_match,
        "similarity": round(float(sim), 4),
        "threshold": round(float(thresh), 4),
        "status": "MATCH" if is_match else "MISMATCH",
        "message": "Voice verification passed." if is_match else "Voice mismatch detected.",
    }


def clear_voice_embeddings(key: Optional[str] = None, candidate_id: Optional[int] = None):
    """Purges biometric voice embeddings from ephemeral memory."""
    keys_to_remove = []
    if key is not None:
        keys_to_remove.append(str(key).strip())
        keys_to_remove.append(f"cand_{str(key).strip()}")
    if candidate_id is not None:
        keys_to_remove.append(f"cand_{candidate_id}")
        keys_to_remove.append(str(candidate_id))

    for k in keys_to_remove:
        if k in _EPHEMERAL_EMBEDDINGS:
            del _EPHEMERAL_EMBEDDINGS[k]
