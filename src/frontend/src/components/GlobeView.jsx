import { useEffect, useRef, useState, useCallback } from "react";
import * as Cesium from "cesium";

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
const WHOLE_GLOBE_DESTINATION = Cesium.Cartesian3.fromDegrees(0, 10, IMAGERY_LIMIT_HEIGHT_M);

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
  const onSelectObjectRef = useRef(onSelectObject);
  // Must match the camera's actual starting height (WHOLE_GLOBE_DESTINATION,
  // defined below) -- not MAX_CAMERA_HEIGHT_M. The camera.changed listener
  // that would otherwise correct a wrong guess here isn't registered until
  // after the initial camera.setView() call, so it never fires for the
  // starting position; a wrong initial value here silently desyncs the
  // slider's percentage math from the buttons/track until the user causes
  // some *other* camera change (e.g. clicking +/- clamped at a stale 0%,
  // which is exactly the bug this comment is here to prevent regressing).
  const [zoomPct, setZoomPct] = useState(sliderPctFromHeight(IMAGERY_LIMIT_HEIGHT_M));

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
    viewer.scene.globe.enableLighting = false;
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
          // 0 = always depth-test against the globe (Cesium's own inverted
          // convention: this was POSITIVE_INFINITY, i.e. "never depth-test,
          // always render on top" -- which made every object visible even
          // on the far side of the Earth, through the globe itself.
          disableDepthTestDistance: 0,
        },
      });
      entity.radarId = obj.object_id;
      entityMapRef.current.set(String(obj.object_id), entity);
    });
  }, [objects, mode]);

  // ---- fly to selected object ----
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    viewer.camera.cancelFlight();
    if (selectedObjectId === null || selectedObjectId === undefined) {
      viewer.camera.flyTo({ destination: WHOLE_GLOBE_DESTINATION, duration: 1.1 });
      return;
    }
    const entity = entityMapRef.current.get(String(selectedObjectId));
    if (!entity) return;
    viewer.flyTo(entity, { duration: 1.1, offset: new Cesium.HeadingPitchRange(0, -0.5, 900000) });
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

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />

      <div
        className="hud-frame globe-zoom-control"
        style={{
          position: "absolute",
          // Clear of both right-side panels this could sit under: the
          // Overview stat cluster (right:18, width:242) and the wider Threat
          // Analysis risk list (right:18, width:340) -- 18+340=358, so this
          // needs a bigger margin than the narrower panel alone would need.
          right: 380,
          // Top-right, level with .intelligence-panel's own top edge
          // (top:18) rather than vertically centered on the globe.
          top: 18,
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
      </div>
    </div>
  );
}
