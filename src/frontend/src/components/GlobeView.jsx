import { useEffect, useRef, useState, useCallback } from "react";
import * as Cesium from "cesium";
import {
  getBaseIconScale,
  getObjectIcon,
  getSelectionRing,
  getTooltipData,
  getVisualMeta,
  getVisualRiskTier,
  getWarningRing,
  isAnimatedRisk,
} from "../utils/objectVisuals";

// Zoom slider range. NaturalEarthII (see the imagery provider below) is a
// low-resolution whole-Earth texture, not a tiled high-detail basemap -- it
// looks like an unusable blur well before 700km. 3,000km keeps the closest
// zoom still recognizably textured rather than a smear of pixels.
const MIN_CAMERA_HEIGHT_M = 3000000;
// Imagery only reliably renders up to ~17,000km (see the note below) -- past
// that the globe still works, it just falls back to its flat dark base color
// (a reasonable look for "pulled back far enough to see it as a small dark
// sphere against the starfield," not a broken state).
const IMAGERY_LIMIT_HEIGHT_M = 17000000;
const MAX_CAMERA_HEIGHT_M = 100000000;

// A single log scale from MIN to MAX would put IMAGERY_LIMIT_HEIGHT_M
// (the default starting view) at ~19% up the track -- 250km-17,000km spans
// most of the log range, leaving almost no slider travel for zooming out
// beyond it, even though there's another 83,000km of height left to give.
// Instead, split the track deliberately: the near/textured zone and the
// far/silhouette zone each get a fixed, generous share of the slider,
// log-scaled *within* their own share, so both directions from the default
// view feel like they have real room to move.
const SPLIT_PCT = 50; // the default starting view sits at exactly the midpoint

// A native horizontal <input type="range"> increases its value dragging
// left-to-right -- so for "drag right = zoom in" to hold (matching the "+"
// button sitting on the right of the track), higher pct must mean LOWER
// camera height. pct=0 -> MAX (zoomed out, left/"-" side), pct=SPLIT_PCT ->
// IMAGERY_LIMIT (default, middle), pct=100 -> MIN (zoomed in, right/"+" side).
function heightFromSliderPct(pct) {
  if (pct <= SPLIT_PCT) {
    const t = pct / SPLIT_PCT;
    return MAX_CAMERA_HEIGHT_M * Math.pow(IMAGERY_LIMIT_HEIGHT_M / MAX_CAMERA_HEIGHT_M, t);
  }
  const t = (pct - SPLIT_PCT) / (100 - SPLIT_PCT);
  return IMAGERY_LIMIT_HEIGHT_M * Math.pow(MIN_CAMERA_HEIGHT_M / IMAGERY_LIMIT_HEIGHT_M, t);
}
function sliderPctFromHeight(heightM) {
  const clamped = Math.min(MAX_CAMERA_HEIGHT_M, Math.max(MIN_CAMERA_HEIGHT_M, heightM));
  if (clamped >= IMAGERY_LIMIT_HEIGHT_M) {
    const t = Math.log(clamped / MAX_CAMERA_HEIGHT_M) / Math.log(IMAGERY_LIMIT_HEIGHT_M / MAX_CAMERA_HEIGHT_M);
    return t * SPLIT_PCT;
  }
  const t = Math.log(clamped / IMAGERY_LIMIT_HEIGHT_M) / Math.log(MIN_CAMERA_HEIGHT_M / IMAGERY_LIMIT_HEIGHT_M);
  return SPLIT_PCT + t * (100 - SPLIT_PCT);
}

// 22,000km (roughly geostationary altitude) looks like the "correct" framing
// for a whole-Earth view, but at that distance Cesium's tile-hierarchy
// loading logic silently fails to composite the base imagery (parent tiles
// never resolve), leaving the globe fully untextured even though the
// provider itself reports ready. ~17,000km is the closest round distance
// that reliably renders imagery while still comfortably fitting the entire
// globe in frame -- verified visually, not a documented Cesium constant.
const STANDARD_GLOBE_HEIGHT_M = 19000000;
const WHOLE_GLOBE_DESTINATION = Cesium.Cartesian3.fromDegrees(0, 10, STANDARD_GLOBE_HEIGHT_M);

function animationPhase(time, periodSeconds) {
  return (Cesium.JulianDate.toDate(time).getTime() / 1000 / periodSeconds) * Math.PI * 2;
}

function animatedScale(object, baseScale) {
  if (!isAnimatedRisk(object)) return baseScale;
  const tier = getVisualRiskTier(object);
  const period = tier === "critical" ? 1 : tier === "high" ? 2.1 : 3.5;
  const amplitude = tier === "critical" ? 0.12 : tier === "high" ? 0.07 : 0.035;
  return new Cesium.CallbackProperty((time) => {
    const breathe = Math.sin(animationPhase(time, period));
    return baseScale * (1 + breathe * amplitude);
  }, false);
}

function animatedRingScale(object) {
  const tier = getVisualRiskTier(object);
  const period = tier === "critical" ? 1 : 2.1;
  const amplitude = tier === "critical" ? 0.18 : 0.1;
  return new Cesium.CallbackProperty((time) => {
    const breathe = (Math.sin(animationPhase(time, period)) + 1) / 2;
    return 0.58 + breathe * amplitude;
  }, false);
}

function animatedRingColor(object, color) {
  const tier = getVisualRiskTier(object);
  const period = tier === "critical" ? 1 : 2.1;
  const base = Cesium.Color.fromCssColorString(color);
  return new Cesium.CallbackProperty((time) => {
    const pulse = (Math.sin(animationPhase(time, period)) + 1) / 2;
    const alpha = tier === "critical" ? 0.22 + pulse * 0.5 : 0.16 + pulse * 0.3;
    return base.withAlpha(alpha);
  }, false);
}

// Resolve a CSS variable to a concrete color the Cesium canvas can use
// (the canvas can't consume var(--x) directly, only the resolved value).
export default function GlobeView({ objects, mode, selectedObjectId, onSelectObject }) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const entityMapRef = useRef(new Map());
  const onSelectObjectRef = useRef(onSelectObject);
  const hoveredEntityRef = useRef(null);
  // Must match the camera's actual starting height (WHOLE_GLOBE_DESTINATION,
  // defined below) -- not MAX_CAMERA_HEIGHT_M. The camera.changed listener
  // that would otherwise correct a wrong guess here isn't registered until
  // after the initial camera.setView() call, so it never fires for the
  // starting position; a wrong initial value here silently desyncs the
  // slider's percentage math from the buttons/track until the user causes
  // some *other* camera change (e.g. clicking +/- clamped at a stale 0%,
  // which is exactly the bug this comment is here to prevent regressing).
  const [zoomPct, setZoomPct] = useState(sliderPctFromHeight(STANDARD_GLOBE_HEIGHT_M));
  const [tooltip, setTooltip] = useState(null);

  useEffect(() => {
    onSelectObjectRef.current = onSelectObject;
  }, [onSelectObject]);

  // ---- one-time viewer setup ----
  useEffect(() => {
    let destroyed = false; // guards the async imagery load below against
    // React 19 StrictMode's dev-only double-invoke of this effect: without
    // this, the promise can resolve against a viewer that a premature
    // mount->cleanup->mount cycle already destroyed, throwing inside Cesium
    // internals (Viewer.get reading .scene on an undefined _dataSourceDisplay)
    // and silently leaving the *real* (second) viewer with no imagery at all.

    const viewer = new Cesium.Viewer(containerRef.current, {
      baseLayer: false,
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

    // Cesium's own bundled Natural Earth II imagery, not a live OSM tile
    // fetch: no network dependency, no baked-in place-name labels cluttering
    // a zoomed-out tracking view (OSM's raster style bakes country/city
    // labels straight into the image -- can't be styled away), and its
    // already-muted natural palette tints cleanly toward this HUD's dark
    // theme with simple brightness/saturation adjustments below.
    Cesium.TileMapServiceImageryProvider.fromUrl(
      Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
    ).then((provider) => {
      if (destroyed) return;
      const layer = viewer.imageryLayers.addImageryProvider(provider);
      layer.brightness = 0.45;
      layer.contrast = 1.25;
      layer.saturation = 0.55;
      layer.gamma = 0.9;
    });

    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#070a12");
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#05070c");

    // Real day/night terminator driven by the actual current solar position
    // (the viewer's clock defaults to system time) -- a static fully-lit
    // globe read as flat and generic; this gives the Earth actual shape and
    // makes it obviously "live" rather than a rendered prop. The ocean
    // normal map is one of Cesium's own bundled assets (no network fetch)
    // and only matters once lighting is on -- it's what makes water catch a
    // specular highlight from the sun instead of shading like flat land.
    viewer.scene.globe.enableLighting = true;
    viewer.scene.globe.dynamicAtmosphereLighting = true;
    viewer.scene.globe.oceanNormalMapUrl = Cesium.buildModuleUrl(
      "Assets/Textures/waterNormalsSmall.jpg"
    );
    viewer.scene.skyAtmosphere.hueShift = -0.05;
    viewer.scene.skyAtmosphere.saturationShift = -0.35;
    viewer.scene.skyAtmosphere.brightnessShift = -0.3;

    // Registered *before* the initial setView below (not after) so the
    // slider's percentage state is derived from the real starting camera
    // position from the very first frame, rather than relying on a
    // separately-maintained useState initializer staying in sync with
    // WHOLE_GLOBE_DESTINATION by hand.
    const syncSliderToCamera = () => {
      setZoomPct(sliderPctFromHeight(viewer.camera.positionCartographic.height));
    };
    viewer.camera.changed.addEventListener(syncSliderToCamera);
    viewer.camera.percentageChanged = 0.01;

    viewer.camera.setView({
      destination: WHOLE_GLOBE_DESTINATION,
    });

    viewer.screenSpaceEventHandler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id?.radarId) {
        onSelectObjectRef.current?.(picked.id.radarId);
      } else {
        onSelectObjectRef.current?.(null);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewer.screenSpaceEventHandler.setInputAction((movement) => {
      const picked = viewer.scene.pick(movement.endPosition);
      const nextEntity = Cesium.defined(picked) && picked.id?.radarId ? picked.id : null;
      hoveredEntityRef.current = nextEntity;
      if (nextEntity) {
        const position = nextEntity.position.getValue(viewer.clock.currentTime);
        const screenPosition = viewer.scene.cartesianToCanvasCoordinates(position);
        if (screenPosition) {
          setTooltip({ ...getTooltipData(nextEntity.radarObject), x: screenPosition.x, y: screenPosition.y });
        }
      } else {
        setTooltip(null);
      }
      viewer.canvas.classList.toggle("is-object-hovered", Boolean(nextEntity));
    }, Cesium.ScreenSpaceEventType.MOUSE_MOVE);

    const updateTooltipPosition = () => {
      const entity = hoveredEntityRef.current;
      if (!entity) return;
      const position = entity.position.getValue(viewer.clock.currentTime);
      const screenPosition = viewer.scene.cartesianToCanvasCoordinates(position);
      if (screenPosition) {
        setTooltip((current) => current ? { ...current, x: screenPosition.x, y: screenPosition.y } : current);
      }
    };
    viewer.camera.changed.addEventListener(updateTooltipPosition);

    // Cesium's canvas gives no visual cue that dragging pans the globe --
    // toggle a grab/grabbing cursor the way any other draggable surface would.
    // mouseup is on window (not the canvas) so releasing outside the canvas
    // -- a fast drag that overshoots the globe area -- still resets the cursor.
    const canvas = viewer.canvas;
    canvas.classList.add("globe-canvas-layer");
    const startDrag = () => canvas.classList.add("is-dragging");
    const endDrag = () => canvas.classList.remove("is-dragging");
    canvas.addEventListener("mousedown", startDrag);
    window.addEventListener("mouseup", endDrag);

    // Cap scroll-wheel/pinch zoom to the same range the slider covers. Two
    // reasons: (1) without this, scrolling out past MAX_CAMERA_HEIGHT_M lands
    // back in the "imagery silently fails to render" zone documented above,
    // and (2) it keeps the slider thumb's position always a true reflection
    // of camera distance -- no clamping-induced desync between the two.
    viewer.scene.screenSpaceCameraController.minimumZoomDistance = MIN_CAMERA_HEIGHT_M;
    viewer.scene.screenSpaceCameraController.maximumZoomDistance = MAX_CAMERA_HEIGHT_M;

    viewerRef.current = viewer;
    return () => {
      destroyed = true;
      canvas.removeEventListener("mousedown", startDrag);
      window.removeEventListener("mouseup", endDrag);
      viewer.camera.changed.removeEventListener(updateTooltipPosition);
      viewer.camera.changed.removeEventListener(syncSliderToCamera);
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

      const entity = viewer.entities.add({
        position,
        billboard: {
          image: getObjectIcon(obj),
          scale: animatedScale(obj, getBaseIconScale(obj)),
          scaleByDistance: new Cesium.NearFarScalar(4000000, 1.25, 40000000, 0.72),
          translucencyByDistance: new Cesium.NearFarScalar(4000000, mode === "threat" && getVisualRiskTier(obj) === "low" ? 0.25 : 1, 40000000, 0.8),
          disableDepthTestDistance: 0,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
        },
      });
      entity.radarId = obj.object_id;
      entity.radarObject = obj;
      entityMapRef.current.set(String(obj.object_id), entity);

      const tier = getVisualRiskTier(obj);
      const meta = getVisualMeta(obj);
      if (tier === "high" || tier === "critical") {
        const warningRing = viewer.entities.add({
          position,
          billboard: {
            image: getWarningRing(obj),
            scale: animatedRingScale(obj),
            color: animatedRingColor(obj, meta.color),
            scaleByDistance: new Cesium.NearFarScalar(4000000, 1.2, 40000000, 0.65),
            disableDepthTestDistance: 0,
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
          },
        });
        warningRing.radarWarningRing = true;
        warningRing.radarId = obj.object_id;
        warningRing.radarObject = obj;
      }

      if (String(obj.object_id) === String(selectedObjectId)) {
        const selectionRing = viewer.entities.add({
          position,
          billboard: {
            image: getSelectionRing(obj),
            scale: 0.9,
            color: Cesium.Color.fromCssColorString(meta.color).withAlpha(0.9),
            disableDepthTestDistance: 0,
            verticalOrigin: Cesium.VerticalOrigin.CENTER,
          },
        });
        selectionRing.radarId = obj.object_id;
        selectionRing.radarObject = obj;
      }
    });
  }, [objects, mode, selectedObjectId]);

  // ---- fly to selected object ----
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.camera.cancelFlight();
    // Set zoomPct directly rather than waiting on the camera.changed listener
    // to derive it back from the landed height -- that event doesn't reliably
    // fire on every tick of a scripted flyTo (unlike organic scroll/drag
    // zoom), so the slider could land stale/desynced from the camera it's
    // supposed to reflect. Every flight target below has a known height, so
    // there's no reason to round-trip through the listener for it anyway.
    if (selectedObjectId === null || selectedObjectId === undefined) {
      viewer.camera.flyTo({ destination: WHOLE_GLOBE_DESTINATION, duration: 1.1 });
      setZoomPct(sliderPctFromHeight(STANDARD_GLOBE_HEIGHT_M));
      return;
    }
    const entity = entityMapRef.current.get(String(selectedObjectId));
    if (!entity) return;
    const focusHeightM = 900000;
    viewer.flyTo(entity, { duration: 1.1, offset: new Cesium.HeadingPitchRange(0, -0.5, focusHeightM) });
    setZoomPct(sliderPctFromHeight(focusHeightM));
  }, [selectedObjectId]);

  const handleSliderChange = useCallback((event) => {
    const pct = Number(event.target.value);
    setZoomPct(pct);
    const viewer = viewerRef.current;
    if (!viewer) return;
    const carto = viewer.camera.positionCartographic;
    // Deliberately omit `orientation` -- preserving the current
    // heading/pitch/roll while changing only height broke badly at the
    // close end of the range: a pitch that grazes the horizon from far
    // away can point straight past the globe into empty space once the
    // same angle is applied a few thousand km up instead. Omitting it lets
    // Cesium apply its own default (look straight down at the surface below
    // the destination point), the same default the initial WHOLE_GLOBE_DESTINATION
    // view relies on and which always points at the globe correctly.
    //
    // flyTo, not setView: an instant teleport reads as a jarring jump for a
    // deliberate zoom action (unlike scroll-wheel zoom, which is already
    // continuous). A short animated transition matches the feel of the
    // rest of the UI's motion.
    viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromRadians(carto.longitude, carto.latitude, heightFromSliderPct(pct)),
      duration: 0.35,
    });
  }, []);

  // Reset to the same centered whole-Earth framing the view opens on. Sets
  // zoomPct directly instead of trusting camera.changed to derive it back
  // from the landed height -- see the comment on the object-selection
  // effect above for why.
  const handleResetView = useCallback(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.camera.cancelFlight();
    viewer.camera.flyTo({ destination: WHOLE_GLOBE_DESTINATION, duration: 1.1 });
    setZoomPct(sliderPctFromHeight(STANDARD_GLOBE_HEIGHT_M));
  }, []);

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />

      {tooltip && (
        <div
          className="object-tooltip hud-frame"
          style={{ left: tooltip.x + 14, top: tooltip.y + 14, "--tooltip-color": tooltip.color }}
          role="status"
        >
          <strong className="tooltip-title">{tooltip.id}</strong>
          <span className="tooltip-type" style={{ color: tooltip.color }}>{tooltip.type}</span>
          <span>ALTITUDE: {tooltip.altitude}</span>
          <span>VELOCITY: {tooltip.velocity}</span>
          <span>RISK: {tooltip.label.toUpperCase()}</span>
        </div>
      )}

      <div
        className="hud-frame globe-zoom-control"
        style={{
          position: "absolute",
          // Clear of both right-side panels this could sit under: the
          // Overview stat cluster (right:18, width:242) and the wider Threat
          // Analysis risk list (right:18, width:340) -- 18+340=358, so this
          // needs a bigger margin than the narrower panel alone would need.
          left: 224,
          // Top-right, level with .intelligence-panel's own top edge
          // (top:18) rather than vertically centered on the globe.
          top: 88,
          zIndex: 25,
        }}
      >
        <span className="eyebrow">ZOOM</span>
        <button
          type="button"
          className="globe-zoom-step"
          aria-label="Zoom out"
          // Left side, lower pct = zoomed out (see heightFromSliderPct).
          onClick={() => handleSliderChange({ target: { value: Math.max(0, zoomPct - 12) } })}
        >
          −
        </button>
        <input
          type="range"
          min={0}
          max={100}
          step={0.1}
          value={zoomPct}
          onChange={handleSliderChange}
          aria-label="Globe zoom"
          className="globe-zoom-slider"
        />
        <button
          type="button"
          className="globe-zoom-step"
          aria-label="Zoom in"
          // Right side, higher pct = zoomed in -- matches dragging the thumb
          // right (a native range input's value increases left-to-right).
          onClick={() => handleSliderChange({ target: { value: Math.min(100, zoomPct + 12) } })}
        >
          +
        </button>
        <button
          type="button"
          className="globe-zoom-step globe-zoom-reset"
          aria-label="Reset view"
          title="Reset view"
          onClick={handleResetView}
        >
          ⟲
        </button>
      </div>
    </div>
  );
}
