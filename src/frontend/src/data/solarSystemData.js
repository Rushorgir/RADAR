// Static reference data for the basic Solar System view (SolarSystemView.jsx).
//
// This is a schematic, not-to-scale visualization -- the real solar system
// can't be rendered at a single consistent scale and still be legible (at
// true relative size Earth is a speck next to Jupiter; at true relative
// distance the inner planets collapse into the Sun). `sceneRadius` (orbit
// distance) and `sceneSize` (sphere radius) below are hand-tuned scene units
// chosen so every planet stays visibly separated and clickable, while still
// preserving the real ordering and *relative* relationships (inner planets
// closer and smaller, gas giants bigger, etc). `distanceAU`, `meanRadiusKm`,
// `orbitalPeriodDays`, and `dayLengthHours` are the real published figures,
// shown as-is in the detail panel.
//
// Moon counts are deliberately omitted -- new moons are discovered
// regularly (Saturn's confirmed count alone jumped by over 100 in 2023),
// so a fixed number here would go stale. `notableMoons` lists a couple of
// well-known named moons instead, which don't change.

export const SUN = {
  id: "sun",
  name: "Sun",
  color: "#ffd27a",
  glowColor: "#ffb347",
  sceneSize: 3.1,
  meanRadiusKm: 696000,
  description: "G-type main-sequence star. Contains ~99.8% of the Solar System's mass.",
};

export const PLANETS = [
  {
    id: "mercury",
    name: "Mercury",
    color: "#9c948f",
    sceneSize: 0.34,
    sceneRadius: 8,
    orbitalPeriodDays: 88,
    distanceAU: 0.387,
    meanRadiusKm: 2439.7,
    dayLengthHours: 1407.6,
    notableMoons: [],
    description: "Smallest planet, closest to the Sun. No moons, virtually no atmosphere.",
  },
  {
    id: "venus",
    name: "Venus",
    color: "#e0c185",
    sceneSize: 0.52,
    sceneRadius: 11,
    orbitalPeriodDays: 224.7,
    distanceAU: 0.723,
    meanRadiusKm: 6051.8,
    dayLengthHours: 5832.5,
    notableMoons: [],
    description: "Hottest planet -- a runaway greenhouse atmosphere traps heat under thick cloud.",
  },
  {
    id: "earth",
    name: "Earth",
    color: "#3fa7d6",
    sceneSize: 0.55,
    sceneRadius: 14.5,
    orbitalPeriodDays: 365.25,
    distanceAU: 1.0,
    meanRadiusKm: 6371,
    dayLengthHours: 24,
    notableMoons: ["Moon"],
    description: "The one this whole dashboard is tracking debris around.",
  },
  {
    id: "mars",
    name: "Mars",
    color: "#c1602c",
    sceneSize: 0.4,
    sceneRadius: 18,
    orbitalPeriodDays: 687,
    distanceAU: 1.524,
    meanRadiusKm: 3389.5,
    dayLengthHours: 24.6,
    notableMoons: ["Phobos", "Deimos"],
    description: "The Red Planet -- iron oxide dust gives it its color.",
  },
  {
    id: "jupiter",
    name: "Jupiter",
    color: "#d8ba8f",
    sceneSize: 1.65,
    sceneRadius: 26,
    orbitalPeriodDays: 4333,
    distanceAU: 5.203,
    meanRadiusKm: 69911,
    dayLengthHours: 9.9,
    notableMoons: ["Io", "Europa", "Ganymede", "Callisto"],
    description: "Largest planet -- more massive than everything else in orbit combined.",
  },
  {
    id: "saturn",
    name: "Saturn",
    color: "#e6cf9c",
    sceneSize: 1.4,
    sceneRadius: 33,
    orbitalPeriodDays: 10759,
    distanceAU: 9.537,
    meanRadiusKm: 58232,
    dayLengthHours: 10.7,
    notableMoons: ["Titan", "Enceladus"],
    hasRings: true,
    description: "Its ring system is mostly water ice, spanning up to ~280,000 km across.",
  },
  {
    id: "uranus",
    name: "Uranus",
    color: "#a9dde0",
    sceneSize: 0.95,
    sceneRadius: 39,
    orbitalPeriodDays: 30687,
    distanceAU: 19.191,
    meanRadiusKm: 25362,
    dayLengthHours: 17.2,
    notableMoons: ["Titania", "Oberon"],
    description: "Rotates on its side -- an axial tilt of ~98 degrees, likely from an ancient impact.",
  },
  {
    id: "neptune",
    name: "Neptune",
    color: "#3f66c4",
    sceneSize: 0.92,
    sceneRadius: 45,
    orbitalPeriodDays: 60190,
    distanceAU: 30.07,
    meanRadiusKm: 24622,
    dayLengthHours: 16.1,
    notableMoons: ["Triton"],
    description: "Fastest winds in the Solar System, reaching over 2,000 km/h.",
  },
];
