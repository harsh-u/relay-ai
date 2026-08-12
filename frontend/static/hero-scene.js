// Ambient 3D backdrop for the marketing homepage - a faceted icosahedron
// core inside a connected particle-node network, with mouse-parallax and
// scroll fade. Plain vanilla three.js via an ESM CDN import - no bundler,
// no React, consistent with this whole frontend having zero build step.
//
// Visually modeled on convoxio-v2's own marketing hero background
// (frontend/src/components/marketing/background-scene.tsx there), scaled
// down for a lighter, dependency-free page.

import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js";

const container = document.getElementById("hero-scene");
if (container && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  initHeroScene(container);
} else if (container) {
  container.style.opacity = "0.15";
}

function initHeroScene(container) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.z = 9;

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  const group = new THREE.Group();
  scene.add(group);

  // Faceted core: a translucent icosahedron plus its own wireframe edges.
  const coreGeometry = new THREE.IcosahedronGeometry(2.2, 1);
  const core = new THREE.Mesh(
    coreGeometry,
    new THREE.MeshStandardMaterial({
      color: 0x6366f1,
      transparent: true,
      opacity: 0.12,
      roughness: 0.4,
      metalness: 0.2,
    })
  );
  group.add(core);
  group.add(
    new THREE.LineSegments(
      new THREE.WireframeGeometry(coreGeometry),
      new THREE.LineBasicMaterial({ color: 0x818cf8, transparent: true, opacity: 0.5 })
    )
  );

  // Particle network: nodes scattered on a sphere shell, connected to
  // whichever neighbors happen to be close enough.
  const nodeCount = 60;
  const radius = 4.6;
  const positions = new Float32Array(nodeCount * 3);
  const colors = new Float32Array(nodeCount * 3);
  const palette = [
    [0.39, 0.4, 0.95], // accent
    [0.51, 0.55, 0.97], // accent-hover
    [0.65, 0.75, 0.98], // sky
  ];

  for (let i = 0; i < nodeCount; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = radius * (0.7 + Math.random() * 0.3);
    positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i * 3 + 2] = r * Math.cos(phi);

    const [cr, cg, cb] = palette[i % palette.length];
    colors[i * 3] = cr;
    colors[i * 3 + 1] = cg;
    colors[i * 3 + 2] = cb;
  }

  const pointsGeometry = new THREE.BufferGeometry();
  pointsGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  pointsGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  group.add(
    new THREE.Points(
      pointsGeometry,
      new THREE.PointsMaterial({ size: 0.09, vertexColors: true, transparent: true, opacity: 0.9 })
    )
  );

  const linePositions = [];
  const maxDistance = 2.4;
  for (let i = 0; i < nodeCount; i++) {
    for (let j = i + 1; j < nodeCount; j++) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (distance < maxDistance) {
        linePositions.push(
          positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
          positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
        );
      }
    }
  }
  const lineGeometry = new THREE.BufferGeometry();
  lineGeometry.setAttribute(
    "position",
    new THREE.BufferAttribute(new Float32Array(linePositions), 3)
  );
  group.add(
    new THREE.LineSegments(
      lineGeometry,
      new THREE.LineBasicMaterial({ color: 0x6366f1, transparent: true, opacity: 0.15 })
    )
  );

  scene.add(new THREE.AmbientLight(0xffffff, 0.4));
  const keyLight = new THREE.PointLight(0x6366f1, 60, 20);
  keyLight.position.set(4, 3, 5);
  scene.add(keyLight);
  const rimLight = new THREE.PointLight(0x38bdf8, 40, 20);
  rimLight.position.set(-5, -3, -4);
  scene.add(rimLight);

  const pointer = { x: 0, y: 0 };
  window.addEventListener("pointermove", (event) => {
    pointer.x = (event.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (event.clientY / window.innerHeight) * 2 - 1;
  });

  let scrollFade = 1;
  window.addEventListener("scroll", () => {
    const fadeDistance = window.innerHeight * 0.9;
    scrollFade = Math.max(0, 1 - window.scrollY / fadeDistance);
    container.style.opacity = String(scrollFade);
    group.position.y = -(1 - scrollFade) * 1.5;
  });

  function resize() {
    const width = container.clientWidth;
    const height = container.clientHeight;
    renderer.setSize(width, height);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize);
  resize();

  function animate() {
    requestAnimationFrame(animate);
    group.rotation.y += (pointer.x * 0.4 - group.rotation.y) * 0.02 + 0.0015;
    group.rotation.x += (pointer.y * 0.2 - group.rotation.x) * 0.02;
    renderer.render(scene, camera);
  }
  animate();
}
