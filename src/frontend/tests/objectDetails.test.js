import test from "node:test";
import assert from "node:assert/strict";
import {
  buildObjectDetail,
  formatNumber,
  formatProbability,
  getRiskMeta,
  normalizeId,
} from "../src/utils/objectDetails.js";

test("normalizes object IDs consistently", () => {
  assert.equal(normalizeId(2101), "2101");
  assert.equal(normalizeId("2101"), "2101");
  assert.equal(normalizeId(null), "");
});

test("selects the highest-risk conjunction for an object", () => {
  const detail = buildObjectDetail(
    { object_id: 2101, name: "DEB-2101", type: "debris", risk_tier: "critical", regime: "LEO" },
    [
      { event_id: "LOW", primary_id: 2101, secondary_id: 9, risk_score: 0.2, pc: 1e-6, miss_distance_km: 9, relative_velocity_kms: 2 },
      { event_id: "HIGH", primary_id: 7, secondary_id: "2101", risk_score: 0.94, pc: 3.2e-3, miss_distance_km: 0.42, relative_velocity_kms: 11.7 },
    ],
  );
  assert.equal(detail.eventId, "HIGH");
  assert.equal(detail.collisionProbability, 3.2e-3);
  assert.equal(detail.velocity, 11.7);
  assert.equal(detail.risk.label, "Critical");
});

test("handles objects without a conjunction safely", () => {
  const detail = buildObjectDetail({ object_id: 99, type: "satellite", risk_tier: "nominal" }, []);
  assert.equal(detail.collisionProbability, undefined);
  assert.equal(detail.missDistance, undefined);
  assert.equal(detail.risk.label, "Low");
  assert.equal(formatNumber(detail.missDistance), "—");
  assert.equal(formatProbability(detail.collisionProbability), "—");
});

test("maps presentation risk labels", () => {
  assert.equal(getRiskMeta("critical").label, "Critical");
  assert.equal(getRiskMeta("elevated").label, "High");
  assert.equal(getRiskMeta("medium").label, "Medium");
  assert.equal(getRiskMeta("nominal").label, "Low");
});
