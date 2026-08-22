import { useEffect, useRef } from "react";
import * as Cesium from "cesium";

// Resolve a CSS variable to a concrete color the Cesium canvas can use
// (the canvas can't consume var(--x) directly, only the resolved value).
function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function riskCssVarName(tier) {
  if (tier === "critical") return "--risk-critical";
  if (tier === "elevated") return "--risk-elevated";
  return "--risk-nominal";
}

export default function GlobeView({ objects, mode, selectedObjectId, onSelectObject }) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const entityMapRef = useRef(new Map());

  // ---- one-time viewer setup ----
  useEffect(() => {
    const viewer = new Cesium.Viewer(containerRef.current, {
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        new Cesium.OpenStreetMapImageryProvider({ url: "https://a.tile.openstreetmap.org/" })
      ),
      baseLayerPicker: false,
      timeline: false,
      animation: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      creditContainer: document.createElement("div"), // hide credits from the HUD
    });

    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#070a12");
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#05070c");
    viewer.scene.globe.enableLighting = false;
    viewer.scene.skyAtmosphere.hueShift = -0.05;
    viewer.scene.skyAtmosphere.saturationShift = -0.35;
    viewer.scene.skyAtmosphere.brightnessShift = -0.3;

    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(0, 10, 22000000),
    });

    viewer.screenSpaceEventHandler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id?.radarId) {
        onSelectObject?.(picked.id.radarId);
      } else {
        onSelectObject?.(null);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;
    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- sync entities whenever the object list changes ----
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    viewer.entities.removeAll();
    entityMapRef.current.clear();

    objects.forEach((obj) => {
      const position = Cesium.Cartesian3.fromDegrees(
        obj.longitude,
        obj.latitude,
        obj.altitude_km * 1000
      );

      const isDebris = obj.type === "debris";
      const baseColor = isDebris ? cssVar("--debris-dot") : cssVar("--signal");
      const riskColor = cssVar(riskCssVarName(obj.risk_tier));

      const isFlagged = obj.risk_tier === "critical" || obj.risk_tier === "elevated";
      const color = isFlagged ? riskColor : baseColor;
      const pixelSize = isFlagged ? (isDebris ? 8 : 11) : isDebris ? 4 : 7;

      const entity = viewer.entities.add({
        position,
        point: {
          pixelSize,
          color: Cesium.Color.fromCssColorString(color).withAlpha(
            mode === "threat" && !isFlagged ? 0.18 : 0.95
          ),
          outlineColor: Cesium.Color.fromCssColorString(color),
          outlineWidth: isFlagged ? 1.5 : 0,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
      entity.radarId = obj.object_id;
      entityMapRef.current.set(obj.object_id, entity);
    });
  }, [objects, mode]);

  // ---- fly to selected object ----
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !selectedObjectId) return;
    const entity = entityMapRef.current.get(selectedObjectId);
    if (!entity) return;
    viewer.flyTo(entity, { duration: 1.1, offset: new Cesium.HeadingPitchRange(0, -0.5, 900000) });
  }, [selectedObjectId]);

  return <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />;
}
