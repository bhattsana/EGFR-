import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const elementColors = {
  H: "#dce8f4",
  C: "#8194a8",
  N: "#478bff",
  O: "#ff6479",
  F: "#54d68b",
  P: "#ff9d49",
  S: "#f5cc55",
  Cl: "#55d68b",
  Br: "#bd7a55",
  I: "#a77bda",
};

const elementRadii = {
  H: 0.13,
  C: 0.24,
  N: 0.23,
  O: 0.22,
  F: 0.2,
  P: 0.27,
  S: 0.27,
  Cl: 0.24,
  Br: 0.26,
  I: 0.28,
};

function createAtomLabel(atom) {
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 64;
  const context = canvas.getContext("2d");
  if (!context) return null;

  context.fillStyle = "rgba(3, 10, 25, 0.88)";
  context.strokeStyle = elementColors[atom.element] || "#43e8ff";
  context.lineWidth = 3;
  context.beginPath();
  context.roundRect(3, 3, 122, 58, 18);
  context.fill();
  context.stroke();
  context.fillStyle = "#eaf5ff";
  context.font = "600 30px Inter, Arial, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(`${atom.element}${atom.index + 1}`, 64, 32);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({
    map: texture,
    transparent: true,
    depthWrite: false,
  }));
  sprite.scale.set(0.58, 0.29, 1);
  return sprite;
}

function createBondCylinders(group, begin, end, bond) {
  const direction = new THREE.Vector3().subVectors(end, begin);
  const length = direction.length();
  if (!Number.isFinite(length) || length < 0.01) return;

  direction.normalize();
  const reference = Math.abs(direction.dot(new THREE.Vector3(0, 0, 1))) > 0.92
    ? new THREE.Vector3(0, 1, 0)
    : new THREE.Vector3(0, 0, 1);
  const offsetDirection = new THREE.Vector3().crossVectors(direction, reference).normalize();
  const bondCount = bond.aromatic ? 1 : Math.min(3, Math.max(1, Math.round(bond.order)));
  const spacing = 0.1;
  const material = new THREE.MeshStandardMaterial({
    color: bond.aromatic ? "#66d9e8" : "#b3c2d5",
    roughness: 0.38,
    metalness: 0.12,
  });

  for (let index = 0; index < bondCount; index += 1) {
    const offset = (index - (bondCount - 1) / 2) * spacing;
    const midpoint = new THREE.Vector3().addVectors(begin, end).multiplyScalar(0.5)
      .addScaledVector(offsetDirection, offset);
    const cylinder = new THREE.Mesh(
      new THREE.CylinderGeometry(0.045, 0.045, length, 8),
      material.clone()
    );
    cylinder.position.copy(midpoint);
    cylinder.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
    group.add(cylinder);
  }
  material.dispose();
}

const Molecule3DCanvas = forwardRef(function Molecule3DCanvas(
  { structure, showAtomLabels, onAtomHover, onRenderError },
  ref
) {
  const hostRef = useRef(null);
  const controlsRef = useRef(null);
  const hoverCallbackRef = useRef(onAtomHover);
  const renderErrorCallbackRef = useRef(onRenderError);
  const [renderError, setRenderError] = useState("");

  hoverCallbackRef.current = onAtomHover;
  renderErrorCallbackRef.current = onRenderError;

  useImperativeHandle(ref, () => ({
    reset() {
      controlsRef.current?.reset();
    },
  }), []);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return undefined;
    let renderer;
    let controls;
    let frameId;
    let disposed = false;
    const disposables = [];
    const atomMeshes = [];

    try {
      const { atoms, bonds } = structure || {};
      if (!Array.isArray(atoms) || atoms.length === 0 || !Array.isArray(bonds)) {
        throw new Error("The 3D response did not contain atoms and bonds.");
      }

      const atomPositions = new Map();
      for (const atom of atoms) {
        const { x, y, z } = atom.coordinates || {};
        if (
          !Number.isInteger(atom.index)
          || atomPositions.has(atom.index)
          || typeof atom.element !== "string"
          || ![x, y, z].every(Number.isFinite)
        ) {
          throw new Error("The 3D response contains invalid atom coordinates.");
        }
        atomPositions.set(atom.index, new THREE.Vector3(x, y, z));
      }
      if (atomPositions.size !== atoms.length) {
        throw new Error("The 3D response contains duplicate atom indices.");
      }
      for (const bond of bonds) {
        if (!atomPositions.has(bond.begin) || !atomPositions.has(bond.end) || bond.begin === bond.end) {
          throw new Error("The 3D response contains a bond with an invalid atom index.");
        }
      }

      setRenderError("");
      const scene = new THREE.Scene();
      scene.background = new THREE.Color("#030611");
      scene.fog = new THREE.Fog("#030611", 18, 55);
      scene.add(new THREE.AmbientLight("#a9c8e8", 1.65));

      const cyanLight = new THREE.PointLight("#43e8ff", 65, 36);
      cyanLight.position.set(5, 7, 11);
      scene.add(cyanLight);
      const violetLight = new THREE.PointLight("#9b72ff", 48, 34);
      violetLight.position.set(-7, -3, -8);
      scene.add(violetLight);

      const bounds = new THREE.Box3().setFromPoints([...atomPositions.values()]);
      const center = bounds.getCenter(new THREE.Vector3());
      const centeredPositions = new Map(
        [...atomPositions.entries()].map(([index, position]) => [
          index,
          position.clone().sub(center),
        ])
      );
      const moleculeGroup = new THREE.Group();

      for (const bond of bonds) {
        createBondCylinders(
          moleculeGroup,
          centeredPositions.get(bond.begin),
          centeredPositions.get(bond.end),
          bond
        );
      }

      const atomGeometry = new THREE.SphereGeometry(1, 24, 18);
      disposables.push(atomGeometry);
      for (const atom of atoms) {
        const radius = elementRadii[atom.element] || 0.23;
        const atomMaterial = new THREE.MeshStandardMaterial({
          color: elementColors[atom.element] || "#9b72ff",
          roughness: 0.3,
          metalness: 0.08,
          emissive: elementColors[atom.element] || "#9b72ff",
          emissiveIntensity: atom.element === "H" ? 0.025 : 0.1,
        });
        const mesh = new THREE.Mesh(atomGeometry, atomMaterial);
        mesh.position.copy(centeredPositions.get(atom.index));
        mesh.scale.setScalar(radius);
        mesh.userData.atom = atom;
        atomMeshes.push(mesh);
        moleculeGroup.add(mesh);

        if (showAtomLabels) {
          const label = createAtomLabel(atom);
          if (label) {
            label.position.copy(mesh.position).add(new THREE.Vector3(0, radius + 0.16, 0));
            moleculeGroup.add(label);
            disposables.push(label.material.map);
            disposables.push(label.material);
          }
        }
      }
      scene.add(moleculeGroup);
      const sphere = bounds.getBoundingSphere(new THREE.Sphere());
      const viewRadius = Math.max(sphere.radius, 1.5);

      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.setSize(host.clientWidth, host.clientHeight);
      host.replaceChildren(renderer.domElement);

      const camera = new THREE.PerspectiveCamera(
        42,
        host.clientWidth / Math.max(host.clientHeight, 1),
        0.1,
        Math.max(100, viewRadius * 12)
      );
      camera.position.set(viewRadius * 1.5, viewRadius * 1.15, viewRadius * 2.45);
      camera.lookAt(0, 0, 0);

      controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      controls.dampingFactor = 0.08;
      controls.minDistance = viewRadius * 1.1;
      controls.maxDistance = viewRadius * 8;
      controls.target.set(0, 0, 0);
      controls.saveState();
      controlsRef.current = controls;

      const render = () => {
        if (!disposed) renderer.render(scene, camera);
      };
      controls.addEventListener("change", render);

      const resizeObserver = new ResizeObserver(() => {
        if (disposed || !host.clientWidth || !host.clientHeight) return;
        camera.aspect = host.clientWidth / host.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(host.clientWidth, host.clientHeight);
        render();
      });
      resizeObserver.observe(host);

      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      let hoveredAtomIndex = null;
      const handlePointerMove = (event) => {
        const rect = renderer.domElement.getBoundingClientRect();
        pointer.set(
          ((event.clientX - rect.left) / rect.width) * 2 - 1,
          -((event.clientY - rect.top) / rect.height) * 2 + 1
        );
        raycaster.setFromCamera(pointer, camera);
        const hit = raycaster.intersectObjects(atomMeshes, false)[0];
        const atom = hit?.object.userData.atom;
        renderer.domElement.style.cursor = atom ? "help" : "grab";
        const nextIndex = atom?.index ?? null;
        if (nextIndex !== hoveredAtomIndex) {
          hoveredAtomIndex = nextIndex;
          hoverCallbackRef.current?.(atom || null);
        }
      };
      const handlePointerLeave = () => {
        renderer.domElement.style.cursor = "grab";
        hoveredAtomIndex = null;
        hoverCallbackRef.current?.(null);
      };
      renderer.domElement.style.cursor = "grab";
      renderer.domElement.addEventListener("pointermove", handlePointerMove);
      renderer.domElement.addEventListener("pointerleave", handlePointerLeave);

      render();
      if (controls.enableDamping) {
        const animate = () => {
          if (disposed) return;
          frameId = window.requestAnimationFrame(animate);
          controls.update();
        };
        animate();
      }

      disposables.push(
        ...moleculeGroup.children.map((child) => child.geometry).filter(Boolean),
        ...moleculeGroup.children.map((child) => child.material).filter(Boolean)
      );

      return () => {
        disposed = true;
        if (frameId) window.cancelAnimationFrame(frameId);
        resizeObserver.disconnect();
        controls.removeEventListener("change", render);
        controls.dispose();
        controlsRef.current = null;
        renderer.domElement.removeEventListener("pointermove", handlePointerMove);
        renderer.domElement.removeEventListener("pointerleave", handlePointerLeave);
        for (const resource of new Set(disposables)) resource.dispose();
        renderer.dispose();
        renderer.domElement.remove();
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "The 3D molecular view could not be initialized.";
      setRenderError(message);
      renderErrorCallbackRef.current?.(message);
      renderer?.dispose();
      controls?.dispose();
      return undefined;
    }
  }, [structure, showAtomLabels]);

  return (
    <div className="molecule-3d-stage" aria-label="Interactive 3D molecule">
      <div className="molecule-3d-host" ref={hostRef} />
      {renderError && (
        <div className="molecule-3d-error" role="alert">
          {renderError} The 2D depiction remains available.
        </div>
      )}
      <span className="sr-only" aria-live="polite">
        {renderError ? `3D viewer error: ${renderError}` : ""}
      </span>
    </div>
  );
});

export default Molecule3DCanvas;
