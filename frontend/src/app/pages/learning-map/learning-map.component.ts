import { Component, OnInit, OnDestroy, ElementRef, ViewChild, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';

interface SubjectNode {
  id: string;
  name: string;
  icon: string;
  color: string;
  x: number;
  y: number;
  z: number;
  description: string;
  lessonCount: number;
}

@Component({
  selector: 'app-learning-map',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './learning-map.component.html',
  styleUrls: ['./learning-map.component.css']
})
export class LearningMapComponent implements AfterViewInit, OnDestroy {
  @ViewChild('threeContainer') containerRef!: ElementRef<HTMLDivElement>;

  selectedSubject: SubjectNode | null = null;
  private renderer: any = null;
  private scene: any = null;
  private camera: any = null;
  private animFrameId: number | null = null;
  private isDragging = false;
  private previousMouse = { x: 0, y: 0 };
  private sphereGroup: any = null;

  subjects: SubjectNode[] = [
    { id: 'math', name: 'Mathematics', icon: 'calculate', color: '#7c3aed', x: 0, y: 0, z: 0, description: 'Algebra, Calculus, Statistics, Geometry', lessonCount: 48 },
    { id: 'physics', name: 'Physics', icon: 'bolt', color: '#3b82f6', x: 200, y: 50, z: -100, description: 'Mechanics, Electromagnetism, Thermodynamics', lessonCount: 36 },
    { id: 'chemistry', name: 'Chemistry', icon: 'science', color: '#10b981', x: -180, y: -60, z: 50, description: 'Organic, Inorganic, Physical Chemistry', lessonCount: 42 },
    { id: 'biology', name: 'Biology', icon: 'biotech', color: '#06b6d4', x: 100, y: -150, z: 80, description: 'Cell Biology, Genetics, Ecology', lessonCount: 40 },
    { id: 'history', name: 'History', icon: 'history_edu', color: '#f59e0b', x: -220, y: 100, z: -80, description: 'World History, Ancient Civilizations', lessonCount: 30 },
    { id: 'literature', name: 'Literature', icon: 'menu_book', color: '#ec4899', x: 150, y: 200, z: 50, description: 'Poetry, Fiction, Analysis, Writing', lessonCount: 25 },
    { id: 'geography', name: 'Geography', icon: 'public', color: '#f97316', x: -100, y: 180, z: -120, description: 'Physical, Human, Environmental Geography', lessonCount: 28 },
    { id: 'computer-science', name: 'Computer Science', icon: 'computer', color: '#8b5cf6', x: 0, y: -200, z: -50, description: 'Algorithms, Data Structures, AI', lessonCount: 55 },
  ];

  async ngAfterViewInit(): Promise<void> {
    await this.initThreeJS();
  }

  async initThreeJS(): Promise<void> {
    try {
      const THREE = await import('three');
      const container = this.containerRef.nativeElement;
      const W = container.clientWidth;
      const H = container.clientHeight;

      // Scene
      this.scene = new THREE.Scene();
      this.scene.background = new THREE.Color(0x050a14);
      this.scene.fog = new THREE.FogExp2(0x050a14, 0.002);

      // Camera
      this.camera = new THREE.PerspectiveCamera(60, W / H, 1, 5000);
      this.camera.position.set(0, 0, 600);

      // Renderer
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
      this.renderer.setSize(W, H);
      this.renderer.setPixelRatio(window.devicePixelRatio);
      container.appendChild(this.renderer.domElement);

      // Stars
      this.addStars(THREE);

      // Ambient light
      const ambient = new THREE.AmbientLight(0x334466, 1.5);
      this.scene.add(ambient);

      // Point light
      const pointLight = new THREE.PointLight(0x7c3aed, 3, 800);
      pointLight.position.set(0, 0, 0);
      this.scene.add(pointLight);

      // Subject spheres
      this.sphereGroup = new THREE.Group();
      this.subjects.forEach((s) => this.createSubjectSphere(THREE, s));
      this.scene.add(this.sphereGroup);

      // Orbital rings
      this.addOrbitalRings(THREE);

      // Events
      this.renderer.domElement.addEventListener('mousedown', (e: MouseEvent) => this.onMouseDown(e));
      this.renderer.domElement.addEventListener('mousemove', (e: MouseEvent) => this.onMouseMove(e, THREE));
      this.renderer.domElement.addEventListener('mouseup', () => this.isDragging = false);
      this.renderer.domElement.addEventListener('click', (e: MouseEvent) => this.onCanvasClick(e, THREE));
      this.renderer.domElement.addEventListener('wheel', (e: WheelEvent) => this.onWheel(e));
      window.addEventListener('resize', () => this.onResize(THREE));

      this.animate();
    } catch (err) {
      console.warn('Three.js load error:', err);
    }
  }

  createSubjectSphere(THREE: any, subject: SubjectNode): void {
    const geo = new THREE.SphereGeometry(30, 32, 32);
    const mat = new THREE.MeshPhongMaterial({
      color: new THREE.Color(subject.color),
      emissive: new THREE.Color(subject.color),
      emissiveIntensity: 0.4,
      shininess: 100,
      transparent: true,
      opacity: 0.9,
    });
    const sphere = new THREE.Mesh(geo, mat);
    sphere.position.set(subject.x, subject.y, subject.z);
    sphere.userData = { subject };
    this.sphereGroup.add(sphere);

    // Glow ring
    const ringGeo = new THREE.RingGeometry(32, 38, 32);
    const ringMat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(subject.color),
      transparent: true,
      opacity: 0.3,
      side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    ring.position.copy(sphere.position);
    ring.rotation.x = Math.PI / 2;
    this.sphereGroup.add(ring);
  }

  addStars(THREE: any): void {
    const geo = new THREE.BufferGeometry();
    const vertices = [];
    for (let i = 0; i < 5000; i++) {
      vertices.push(
        (Math.random() - 0.5) * 4000,
        (Math.random() - 0.5) * 4000,
        (Math.random() - 0.5) * 4000
      );
    }
    geo.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    const mat = new THREE.PointsMaterial({ color: 0x8899cc, size: 1.5, transparent: true, opacity: 0.7 });
    this.scene.add(new THREE.Points(geo, mat));
  }

  addOrbitalRings(THREE: any): void {
    [200, 300, 400].forEach((r) => {
      const geo = new THREE.RingGeometry(r - 1, r + 1, 128);
      const mat = new THREE.MeshBasicMaterial({
        color: 0x334466,
        transparent: true,
        opacity: 0.15,
        side: THREE.DoubleSide,
      });
      const ring = new THREE.Mesh(geo, mat);
      ring.rotation.x = Math.PI / 4 + Math.random() * 0.5;
      ring.rotation.z = Math.random() * Math.PI;
      this.scene.add(ring);
    });
  }

  animate(): void {
    this.animFrameId = requestAnimationFrame(() => this.animate());
    if (this.sphereGroup) {
      this.sphereGroup.rotation.y += 0.001;
    }
    this.renderer?.render(this.scene, this.camera);
  }

  onMouseDown(e: MouseEvent): void {
    this.isDragging = false;
    this.previousMouse = { x: e.clientX, y: e.clientY };
    setTimeout(() => { this.isDragging = true; }, 100);
  }

  onMouseMove(e: MouseEvent, THREE: any): void {
    if (!this.isDragging || !this.sphereGroup) return;
    const dx = e.clientX - this.previousMouse.x;
    const dy = e.clientY - this.previousMouse.y;
    this.sphereGroup.rotation.y += dx * 0.005;
    this.sphereGroup.rotation.x += dy * 0.005;
    this.previousMouse = { x: e.clientX, y: e.clientY };
  }

  onCanvasClick(e: MouseEvent, THREE: any): void {
    const container = this.containerRef.nativeElement;
    const rect = container.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, this.camera);
    const intersects = raycaster.intersectObjects(this.sphereGroup.children, false);

    if (intersects.length > 0) {
      const obj = intersects[0].object;
      if (obj.userData.subject) {
        this.selectedSubject = obj.userData.subject;
      }
    }
  }

  onWheel(e: WheelEvent): void {
    if (!this.camera) return;
    this.camera.position.z = Math.max(200, Math.min(1200, this.camera.position.z + e.deltaY));
  }

  onResize(THREE: any): void {
    const container = this.containerRef.nativeElement;
    const W = container.clientWidth;
    const H = container.clientHeight;
    this.camera.aspect = W / H;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(W, H);
  }

  exploreSubject(): void {
    if (this.selectedSubject) {
      // Navigate to subjects page filtered by this subject
      window.location.href = `/subjects?subject=${this.selectedSubject.id}`;
    }
  }

  ngOnDestroy(): void {
    if (this.animFrameId !== null) cancelAnimationFrame(this.animFrameId);
    if (this.renderer) {
      this.renderer.dispose();
      const canvas = this.renderer.domElement;
      if (canvas.parentNode) canvas.parentNode.removeChild(canvas);
    }
  }
}
