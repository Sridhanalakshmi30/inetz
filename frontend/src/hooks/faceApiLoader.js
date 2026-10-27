import * as faceapi from 'face-api.js';

let modelsLoaded = false;
let loadingPromise = null;

const MODEL_URL = '/models';

export async function loadFaceApiModels(customModelUrl) {
  if (modelsLoaded) return true;
  if (loadingPromise) return loadingPromise;

  loadingPromise = (async () => {
    try {
      const url = customModelUrl || MODEL_URL;
      await Promise.all([
        faceapi.nets.ssdMobilenetv1.loadFromUri(url),
      ]);
      modelsLoaded = true;
      return true;
    } catch (err) {
      console.warn('Failed to load face-api models:', err);
      return false;
    } finally {
      loadingPromise = null;
    }
  })();

  return loadingPromise;
}

export function isFaceApiLoaded() {
  return modelsLoaded;
}

export { faceapi };
