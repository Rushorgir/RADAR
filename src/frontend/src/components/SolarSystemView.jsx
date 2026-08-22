import { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DRenderer, CSS2DObject } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { SUN, PLANETS } from "../data/solarSystemData";

// A basic, schematic Solar System view -- separate scene/engine from
// GlobeView (plain Three.js, not Cesium: Cesium is built around an Earth-
// centric WGS84 ellipsoid and isn't a natural fit for a multi-body scene).
// Distances and sizes are hand-tuned scene units, not physically to scale --
// see the file-level comment in solarSystemData.js for why a literally
// accurate scale can't be legible in a single view.

const CAMERA_START = new THREE.Vector3(0, 34, 62);

// Orbital angular speed, schematic: real periods span 88 days (Mercury) to
// 60,190 days (Neptune) -- animating that ratio directly would leave
// Neptune motionless for the entire time anyone is looking at this screen.
// Compressing with periodDays^0.45 keeps the correct *ordering* (inner
// planets visibly faster) while giving every planet at least some visible
// motion within a normal viewing session.
function angularSpeed(periodDays) {
  return 6 / Math.pow(periodDays, 0.45);
}

function buildStarfield() {
  const count = 2400;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    // Rejection-sample a shell so stars don't clump near the poles the way
    // naive spherical-coordinate sampling would.
    let x, y, z, lenSq;
    do {
      x = Math.random() * 2 - 1;
      y = Math.random() * 2 - 1;
      z = Math.random() * 2 - 1;
      lenSq = x * x + y * y + z * z;
    } while (lenSq > 1 || lenSq === 0);
    const len = Math.sqrt(lenSq);
    const radius = 340 + Math.random() * 260;
    positions[i * 3] = (x / len) * radius;
    positions[i * 3 + 1] = (y / len) * radius;
    positions[i * 3 + 2] = (z / len) * radius;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color: 0xaab4d6,
    size: 0.7,
    sizeAttenuation: true,
    transparent: true,
    opacity: 0.75,
  });
  return new THREE.Points(geometry, material);
}

function makeLabel(text, colorCss) {
  const div = document.createElement("div");
  div.className = "solar-label mono";
  div.textContent = text;
  div.style.color = colorCss;
  const obj = new CSS2DObject(div);
  obj.position.set(0, 0, 0);
  return obj;
}

export default function SolarSystemView({ onSelectBody, selectedBodyId }) {
  const containerRef = useRef(null);
  const stateRef = useRef(null);
  const onSelectBodyRef = useRef(onSelectBody);
  const [hoveredName, setHoveredName] = useState(null);

  useEffect(() => {
    onSelectBodyRef.current = onSelectBody;
  }, [onSelectBody]);

  useEffect(() => {
    // Unlike GlobeView's Cesium setup, everything here is synchronous (no
    // cross-mount async promise that could resolve against an already-
    // destroyed instance), so no StrictMode double-invoke guard is needed.
    const container = containerRef.current;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#05070c");

    const camera = new THREE.PerspectiveCamera(
      50,
      container.clientWidth / container.clientHeight,
      0.1,
      2000
    );
    camera.position.copy(CAMERA_START);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(container.clientWidth, container.clientHeight);
    labelRenderer.domElement.style.position = "absolute";
    labelRenderer.domElement.style.inset = "0";
    labelRenderer.domElement.style.pointerEvents = "none";
    container.appendChild(labelRenderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 10;
    controls.maxDistance = 160;
    controls.target.set(0, 0, 0);

    scene.add(buildStarfield());

    // Faint fill light so night-side hemispheres read as dim, not pure
    // black -- not physically accurate, but a fully unlit far side looks
    // like a rendering error rather than a deliberate choice at this scale.
    scene.add(new THREE.AmbientLight(0x2a3350, 0.55));

    const sunLight = new THREE.PointLight(0xfff4d6, 3.2, 0, 0.15);
    scene.add(sunLight);

    const sunGeometry = new THREE.SphereGeometry(SUN.sceneSize, 48, 48);
    const sunMaterial = new THREE.MeshBasicMaterial({ color: SUN.color });
    const sunMesh = new THREE.Mesh(sunGeometry, sunMaterial);
    sunMesh.userData.bodyId = SUN.id;
    scene.add(sunMesh);

    // Cheap glow: a larger, additive-blended, back-facing sphere behind the
    // sun rather than a full bloom post-processing pass.
    const glowGeometry = new THREE.SphereGeometry(SUN.sceneSize * 1.8, 32, 32);
    const glowMaterial = new THREE.MeshBasicMaterial({
      color: SUN.glowColor,
      transparent: true,
      opacity: 0.18,
      side: THREE.BackSide,
    });
    sunMesh.add(new THREE.Mesh(glowGeometry, glowMaterial));
    sunMesh.add(makeLabel(SUN.name, "#ffd27a"));

    const pickable = [sunMesh];
    const planetMeshes = new Map(); // id -> { pivot, mesh, angularSpeed, angle }

    PLANETS.forEach((planet, index) => {
      const pivot = new THREE.Group();
      scene.add(pivot);

      const orbitGeometry = new THREE.RingGeometry(
        planet.sceneRadius - 0.03,
        planet.sceneRadius + 0.03,
        128
      );
      const orbitMaterial = new THREE.MeshBasicMaterial({
        color: 0x4a5570,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      });
      const orbitLine = new THREE.Mesh(orbitGeometry, orbitMaterial);
      orbitLine.rotation.x = Math.PI / 2;
      scene.add(orbitLine);

      const geometry = new THREE.SphereGeometry(planet.sceneSize, 32, 32);
      const material = new THREE.MeshStandardMaterial({
        color: planet.color,
        roughness: 0.85,
        metalness: 0.05,
      });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.userData.bodyId = planet.id;
      // Spread starting angles out so planets don't all launch lined up in
      // a single radial spoke on first render.
      const angle = (index / PLANETS.length) * Math.PI * 2;
      mesh.position.set(planet.sceneRadius, 0, 0);
      pivot.rotation.y = angle;
      pivot.add(mesh);
      mesh.add(makeLabel(planet.name, planet.color));

      if (planet.hasRings) {
        const ringGeometry = new THREE.RingGeometry(
          planet.sceneSize * 1.3,
          planet.sceneSize * 2.1,
          64
        );
        const ringMaterial = new THREE.MeshBasicMaterial({
          color: planet.color,
          transparent: true,
          opacity: 0.5,
          side: THREE.DoubleSide,
        });
        const ringMesh = new THREE.Mesh(ringGeometry, ringMaterial);
        ringMesh.rotation.x = Math.PI / 2.4;
        mesh.add(ringMesh);
      }

      pickable.push(mesh);
      planetMeshes.set(planet.id, {
        pivot,
        mesh,
        angularSpeed: angularSpeed(planet.orbitalPeriodDays),
      });
    });

    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();

    function pickAt(clientX, clientY) {
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects(pickable, false);
      return hits.length > 0 ? hits[0].object.userData.bodyId : null;
    }

    function handleClick(event) {
      const id = pickAt(event.clientX, event.clientY);
      onSelectBodyRef.current?.(id);
    }

    function handlePointerMove(event) {
      const id = pickAt(event.clientX, event.clientY);
      renderer.domElement.style.cursor = id ? "pointer" : "grab";
      setHoveredName(id ? (id === SUN.id ? SUN.name : PLANETS.find((p) => p.id === id)?.name) : null);
    }

    renderer.domElement.addEventListener("click", handleClick);
    renderer.domElement.addEventListener("pointermove", handlePointerMove);
    renderer.domElement.classList.add("solar-canvas");

    const resizeObserver = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
      labelRenderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    let lastTime = performance.now();
    let frameId;
    function animate(now) {
      frameId = requestAnimationFrame(animate);
      const dt = Math.min((now - lastTime) / 1000, 0.1);
      lastTime = now;
      planetMeshes.forEach(({ pivot, angularSpeed: speed }) => {
        pivot.rotation.y += speed * dt * 0.1;
      });
      controls.update();
      renderer.render(scene, camera);
      labelRenderer.render(scene, camera);
    }
    frameId = requestAnimationFrame(animate);

    stateRef.current = { scene, camera, controls, planetMeshes, sunMesh };

    return () => {
      cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      renderer.domElement.removeEventListener("click", handleClick);
      renderer.domElement.removeEventListener("pointermove", handlePointerMove);
      controls.dispose();
      scene.traverse((obj) => {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
          if (Array.isArray(obj.material)) obj.material.forEach((m) => m.dispose());
          else obj.material.dispose();
        }
      });
      renderer.dispose();
      if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
      if (container.contains(labelRenderer.domElement)) container.removeChild(labelRenderer.domElement);
      stateRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Animates both the orbit target and camera position toward a destination
  // over `duration`ms. Shared by the selection effect below and the reset
  // button, so "close panel" and "reset view" can't drift into two
  // different tween implementations that behave subtly differently.
  function flyCamera(camera, controls, endTarget, endCamera, duration = 900) {
    const startTarget = controls.target.clone();
    const startCamera = camera.position.clone();
    const startTime = performance.now();
    function step(now) {
      const t = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      controls.target.lerpVectors(startTarget, endTarget, eased);
      camera.position.lerpVectors(startCamera, endCamera, eased);
      if (t < 1 && stateRef.current) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ---- fly camera to the selected body (or back to the overview if none) ----
  useEffect(() => {
    const state = stateRef.current;
    if (!state) return;
    const { camera, controls, planetMeshes, sunMesh } = state;

    let targetMesh = null;
    let framingDistance = 20;
    if (selectedBodyId === SUN.id) {
      targetMesh = sunMesh;
      framingDistance = 14;
    } else if (selectedBodyId) {
      const entry = planetMeshes.get(selectedBodyId);
      if (entry) {
        targetMesh = entry.mesh;
        const planet = PLANETS.find((p) => p.id === selectedBodyId);
        framingDistance = Math.max(4, (planet?.sceneSize ?? 1) * 6 + 3);
      }
    }

    if (!targetMesh) {
      flyCamera(camera, controls, new THREE.Vector3(0, 0, 0), CAMERA_START);
      return;
    }

    const targetWorldPos = new THREE.Vector3();
    targetMesh.getWorldPosition(targetWorldPos);
    const direction = camera.position.clone().sub(controls.target).normalize();
    const endCamera = targetWorldPos.clone().add(direction.multiplyScalar(framingDistance));
    flyCamera(camera, controls, targetWorldPos, endCamera);
  }, [selectedBodyId]);

  const handleReset = useCallback(() => {
    onSelectBodyRef.current?.(null);
  }, []);

  return (
    <div style={{ position: "absolute", inset: 0 }}>
      <div ref={containerRef} style={{ position: "absolute", inset: 0 }} />

      <div
        className="hud-frame globe-zoom-control"
        style={{ position: "absolute", right: 380, top: 18, zIndex: 25 }}
      >
        <span className="eyebrow">{hoveredName ?? "SOLAR SYSTEM"}</span>
        <button
          type="button"
          className="globe-zoom-step globe-zoom-reset"
          aria-label="Reset view"
          title="Reset view"
          onClick={handleReset}
        >
          ⟲
        </button>
      </div>

      <div
        className="eyebrow"
        style={{ position: "absolute", left: 226, top: 24, zIndex: 20, color: "var(--text-dim)" }}
      >
        Schematic view // not to scale
      </div>
    </div>
  );
}
