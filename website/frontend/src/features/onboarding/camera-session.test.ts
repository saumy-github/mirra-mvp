import { describe, expect, it, vi } from "vitest";
import { CameraSession, cameraError, captureCameraFrame } from "./camera-session";

function stream() {
  const stop = vi.fn();
  return { value: { getTracks: () => [{ stop }] } as unknown as MediaStream, stop };
}

describe("live camera lifecycle", () => {
  it("closes the previous camera before switching and releases all tracks on exit", async () => {
    const a = stream(),
      b = stream();
    const devices = {
      getUserMedia: vi.fn().mockResolvedValueOnce(a.value).mockResolvedValueOnce(b.value),
    };
    const camera = new CameraSession();
    await camera.open(devices, "environment");
    await camera.open(devices, "user");
    expect(a.stop).toHaveBeenCalledOnce();
    expect(camera.isActive(b.value)).toBe(true);
    camera.stop();
    expect(b.stop).toHaveBeenCalledOnce();
    expect(devices.getUserMedia).toHaveBeenLastCalledWith(
      expect.objectContaining({
        audio: false,
        video: expect.objectContaining({ facingMode: { ideal: "user" } }),
      }),
    );
  });
  it("immediately releases permission granted after leaving the capture screen", async () => {
    const a = stream();
    let grant!: (stream: MediaStream) => void;
    const devices = {
      getUserMedia: () =>
        new Promise<MediaStream>((resolve) => {
          grant = resolve;
        }),
    };
    const camera = new CameraSession();
    const pending = camera.open(devices, "environment");
    camera.stop();
    grant(a.value);
    expect(await pending).toBeNull();
    expect(a.stop).toHaveBeenCalledOnce();
  });
  it("ignores an old permission rejection without stopping a resumed camera", async () => {
    let deny!: (error: Error) => void;
    const old = new Promise<MediaStream>((_, reject) => {
      deny = reject;
    });
    const a = stream();
    const devices = {
      getUserMedia: vi.fn().mockReturnValueOnce(old).mockResolvedValueOnce(a.value),
    };
    const camera = new CameraSession();
    const pending = camera.open(devices, "environment");
    await camera.open(devices, "user");
    deny(new Error("Old request denied"));
    expect(await pending).toBeNull();
    expect(camera.isActive(a.value)).toBe(true);
    expect(a.stop).not.toHaveBeenCalled();
    camera.stop();
  });
  it("refuses unloaded or undersized frames instead of sending empty/invalid photos", async () => {
    await expect(
      captureCameraFrame({ readyState: 0 } as HTMLVideoElement, "front"),
    ).rejects.toThrow("getting ready");
    await expect(
      captureCameraFrame(
        { readyState: 4, videoWidth: 320, videoHeight: 240 } as HTMLVideoElement,
        "front",
      ),
    ).rejects.toThrow("resolution");
  });
  it("exports the whole unmirrored sensor frame as a bounded JPEG", async () => {
    const drawImage = vi.fn();
    const canvas = {
      width: 0,
      height: 0,
      getContext: () => ({ drawImage }),
      toBlob: (done: (blob: Blob) => void, type: string) => done(new Blob(["frame"], { type })),
    };
    vi.stubGlobal("document", { createElement: () => canvas });
    try {
      const video = { readyState: 4, videoWidth: 3840, videoHeight: 2160 } as HTMLVideoElement;
      const file = await captureCameraFrame(video, "front");
      expect([canvas.width, canvas.height]).toEqual([2048, 1152]);
      expect(drawImage).toHaveBeenCalledWith(video, 0, 0, 2048, 1152);
      expect(file.type).toBe("image/jpeg");
      expect(file.name).toMatch(/^front-\d+\.jpg$/);
    } finally {
      vi.unstubAllGlobals();
    }
  });
  it("gives a recovery path for denied, missing, and occupied cameras", () => {
    expect(cameraError(new DOMException("", "NotAllowedError"))).toContain("site settings");
    expect(cameraError(new DOMException("", "NotFoundError"))).toContain("webcam");
    expect(cameraError(new DOMException("", "NotReadableError"))).toContain("other camera app");
  });
});
