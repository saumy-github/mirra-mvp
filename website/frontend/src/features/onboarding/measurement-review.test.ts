import { describe, expect, it } from "vitest";
import {
  reviewCorrections,
  reviewDisplay,
  reviewFields,
  reviewInput,
  reviewSlider,
  toReviewUnits,
  type MeasurementEdits,
} from "./measurement-review";

const baseline = Object.freeze({
  height_cm: 175,
  waist_circumference_cm: 80.246,
  hip_circumference_cm: 96.137,
  weight_kg: 70.163,
});

describe("measurement review corrections", () => {
  it("preserves untouched baseline precision and sends only the slider correction", () => {
    expect(reviewCorrections(baseline, {}).corrections).toEqual({});
    const edits = {
      waist_circumference_cm: reviewSlider(80.7, "waist_circumference_cm", "metric"),
    };
    expect(reviewCorrections(baseline, edits).corrections).toEqual({
      waist_circumference_cm: 80.7,
    });
    expect(baseline.hip_circumference_cm).toBe(96.137);
    expect(baseline.waist_circumference_cm).toBe(80.246);
  });

  it("keeps finer manual decimals instead of rounding them to the slider step", () => {
    const edits = {
      waist_circumference_cm: reviewInput("80.27", "waist_circumference_cm", "metric"),
    };
    expect(reviewCorrections(baseline, edits).corrections).toEqual({
      waist_circumference_cm: 80.27,
    });
  });

  it("does not accumulate rounding drift through repeated unit switches", () => {
    const edits = {
      waist_circumference_cm: reviewInput("31.57", "waist_circumference_cm", "imperial"),
    };
    for (let i = 0; i < 20; i++) {
      expect(reviewDisplay(baseline, edits, "waist_circumference_cm", "metric")).toBe("80.19");
      expect(reviewDisplay(baseline, edits, "waist_circumference_cm", "imperial")).toBe("31.57");
    }
    expect(reviewCorrections(baseline, edits).corrections?.waist_circumference_cm).toBeCloseTo(
      80.1878,
      8,
    );
  });

  it("converts imperial slider positions to metric increments and pounds to kg", () => {
    const edits = {
      waist_circumference_cm: reviewSlider(
        toReviewUnits(80.7, "waist_circumference_cm", "imperial"),
        "waist_circumference_cm",
        "imperial",
      ),
      weight_kg: reviewInput("155", "weight_kg", "imperial"),
    };
    const corrections = reviewCorrections(baseline, edits).corrections!;
    expect(corrections.waist_circumference_cm).toBe(80.7);
    expect(corrections.weight_kg).toBeCloseTo(70.306817, 5);
  });

  it("resetting restores the baseline without sending an override", () => {
    const edits: MeasurementEdits = {
      height_cm: reviewInput("175", "height_cm", "metric"),
      waist_circumference_cm: reviewSlider(80.7, "waist_circumference_cm", "metric"),
    };
    delete edits.waist_circumference_cm;
    expect(reviewDisplay(baseline, edits, "waist_circumference_cm", "metric")).toBe("80.25");
    expect(reviewCorrections(baseline, edits).corrections).toEqual({});
  });

  it("leaves missing weight optional and shows only measurements the pipeline supports", () => {
    const incomplete = { height_cm: 175, waist_circumference_cm: 80 };
    expect(reviewFields(incomplete).map((field) => field.key)).toEqual([
      "height_cm",
      "weight_kg",
      "waist_circumference_cm",
    ]);
    expect(reviewFields(incomplete, false).map((field) => field.key)).toEqual([
      "height_cm",
      "waist_circumference_cm",
    ]);
    expect(
      reviewCorrections(incomplete, { weight_kg: reviewInput("", "weight_kg", "metric") })
        .corrections,
    ).toEqual({});
    expect(
      reviewFields({ ...incomplete, bust_circumference_cm: 90 }).map((field) => field.key),
    ).toContain("bust_circumference_cm");
  });

  it.each(["", "0", "231", "NaN", "Infinity"])(
    "blocks an invalid required measurement: %s",
    (text) => {
      const result = reviewCorrections(baseline, {
        height_cm: reviewInput(text, "height_cm", "metric"),
      });
      expect(result.corrections).toBeNull();
      expect(result.error).toMatch(/height/);
    },
  );
});
