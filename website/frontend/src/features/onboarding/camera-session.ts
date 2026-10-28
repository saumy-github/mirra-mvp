export type CameraFacing = "user" | "environment";

/** Owns the stream, including permission requests that resolve after a screen closes. */
export class CameraSession {
  private revision = 0;
  private stream: MediaStream | null = null;

  async open(devices: Pick<MediaDevices, "getUserMedia">, facing: CameraFacing) {
    this.stop();
    const revision = this.revision;
    let stream: MediaStream;
    try {
      stream = await devices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: facing },
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
      });
    } catch (error) {
      if (revision !== this.revision) return null;
      throw error;
    }
    if (revision !== this.revision) {
      stream.getTracks().forEach((track) => track.stop());
      return null;
    }
    this.stream = stream;
    return stream;
  }

  isActive(stream: MediaStream) {
    return this.stream === stream;
  }

  stop() {
    this.revision += 1;
    this.stream?.getTracks().forEach((track) => track.stop());
    this.stream = null;
  }
}

export function cameraError(error: unknown): string {
  const name = error instanceof Error ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Camera access is off. Allow Mirra to use your camera in your browser’s site settings, then try again.";
  if (name === "NotFoundError" || name === "OverconstrainedError")
    return "No camera was found. Connect a webcam, or open this link on your phone.";
  if (name === "NotReadableError")
    return "Your camera is in use. Close the other camera app, then try again.";
  return "The camera couldn’t start. Check its permissions and try again.";
}

/** The only photo source in the shopper UI is a frame from the active camera. */
export async function captureCameraFrame(video: HTMLVideoElement, name: string): Promise<File> {
  if (video.readyState < 2 || !video.videoWidth || !video.videoHeight)
    throw new Error("Your camera is still getting ready. Try again in a moment.");
  if (Math.min(video.videoWidth, video.videoHeight) < 480)
    throw new Error(
      "This camera’s resolution is too low. Use a camera with at least 480 pixels on each side.",
    );
  const canvas = document.createElement("canvas");
  const scale = Math.min(1, 2048 / Math.max(video.videoWidth, video.videoHeight));
  canvas.width = Math.round(video.videoWidth * scale);
  canvas.height = Math.round(video.videoHeight * scale);
  const context = canvas.getContext("2d");
  if (!context) throw new Error("We couldn’t capture that frame. Please try again.");
  // Keep the entire sensor frame. A mirrored selfie preview must not mirror model input.
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (result) => (result ? resolve(result) : reject(new Error("Please retake this photo."))),
      "image/jpeg",
      0.93,
    );
  });
  return new File([blob], `${name}-${Date.now()}.jpg`, { type: "image/jpeg" });
}
