import test from "node:test";
import assert from "node:assert/strict";
import {
  getBaseIconScale,
  getObjectIcon,
  getSelectionRing,
  getVisualMeta,
  getVisualRiskTier,
  isAnimatedRisk,
} from "../src/utils/objectVisuals.js";

const object = (type, risk_tier) => ({ type, risk_tier, object_id: 1 });

test("uses satellite and four debris visualization tiers only", () => {
  assert.equal(getVisualRiskTier(object("satellite", "critical")), "satellite");
  assert.equal(getVisualRiskTier(object("debris", "nominal")), "low");
  assert.equal(getVisualRiskTier(object("debris", "medium")), "medium");
  assert.equal(getVisualRiskTier(object("debris", "elevated")), "high");
  assert.equal(getVisualRiskTier(object("debris", "critical")), "critical");
});

test("keeps icon scale ordered by visual risk", () => {
  assert.ok(getBaseIconScale(object("debris", "nominal")) < getBaseIconScale(object("debris", "medium")));
  assert.ok(getBaseIconScale(object("debris", "medium")) < getBaseIconScale(object("debris", "elevated")));
  assert.ok(getBaseIconScale(object("debris", "elevated")) < getBaseIconScale(object("debris", "critical")));
});

test("uses required visual colors and animation policy", () => {
  assert.equal(getVisualMeta(object("satellite")).color, "#35D9FF");
  assert.equal(getVisualMeta(object("debris", "nominal")).color, "#8A9BAA");
  assert.equal(getVisualMeta(object("debris", "medium")).color, "#FFB020");
  assert.equal(getVisualMeta(object("debris", "elevated")).color, "#FF6333");
  assert.equal(getVisualMeta(object("debris", "critical")).color, "#FF3030");
  assert.equal(isAnimatedRisk(object("debris", "nominal")), false);
  assert.equal(isAnimatedRisk(object("debris", "medium")), true);
});

test("generates reusable SVG data URI textures", () => {
  assert.match(getObjectIcon(object("satellite")), /^data:image\/svg\+xml/);
  assert.match(getObjectIcon(object("debris", "critical")), /^data:image\/svg\+xml/);
  assert.match(getSelectionRing(object("debris", "critical")), /^data:image\/svg\+xml/);
});
