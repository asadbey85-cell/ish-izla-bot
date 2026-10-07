(() => {
  const overlay = document.getElementById("game-overlay");
  const title = document.getElementById("overlay-title");
  const copy = document.getElementById("overlay-copy");
  const startButton = document.getElementById("start-button");
  const scoreValue = document.getElementById("score-value");
  const distanceValue = document.getElementById("distance-value");
  const stateValue = document.getElementById("state-value");

  if (!window.Phaser) {
    title.textContent = "O‘yin yuklanmadi";
    copy.textContent = "O‘yin dvigateli uchun internet aloqasini tekshirib, sahifani yangilang.";
    startButton.disabled = true;
    return;
  }

  class NightPatrol extends Phaser.Scene {
    constructor() {
      super("NightPatrol");
      this.started = false;
      this.score = 0;
      this.rope = null;
      this.ropeAnchor = null;
      this.pickups = [];
      this.drones = [];
      this.anchors = [];
      this.canJump = false;
      this.mobileDirection = 0;
      this.finished = false;
    }

    preload() {
      this.load.image("hero", "/static/images/night-runner.svg");
      this.load.image("skyline", "/static/images/night-skyline.svg");
    }

    create() {
      this.score = 0;
      this.rope = null;
      this.ropeAnchor = null;
      this.pickups = [];
      this.drones = [];
      this.anchors = [];
      this.canJump = false;
      this.mobileDirection = 0;
      this.finished = false;
      overlay.classList.remove("is-hidden");
      title.textContent = "Tungi navbatchi";
      copy.textContent = "To‘r bilan binolar orasida tebran. 12 ta energiya belgisini yig‘ib, dronlardan qoch.";
      startButton.innerHTML = "O‘yinni boshlash <span>↗</span>";
      this.worldWidth = 4200;
      this.add.image(500, 280, "skyline").setScrollFactor(0).setDisplaySize(1000, 560);
      this.matter.world.setBounds(0, 0, this.worldWidth, 560, 64, false, false, true, false);
      this.drawCity();
      this.createAnchors();
      this.createPickups();
      this.createDrones();

      this.hero = this.matter.add.image(115, 420, "hero").setScale(0.62).setCircle(23).setFixedRotation();
      this.hero.setFrictionAir(0.012);
      this.hero.setBounce(0.05);
      this.hero.body.label = "runner";
      this.cameras.main.setBounds(0, 0, this.worldWidth, 560);
      this.cameras.main.startFollow(this.hero, true, 0.08, 0.06, -170, 60);
      this.cameras.main.setZoom(1);

      this.controls = this.input.keyboard.addKeys({
        left: Phaser.Input.Keyboard.KeyCodes.A,
        right: Phaser.Input.Keyboard.KeyCodes.D,
        leftArrow: Phaser.Input.Keyboard.KeyCodes.LEFT,
        rightArrow: Phaser.Input.Keyboard.KeyCodes.RIGHT,
        jump: Phaser.Input.Keyboard.KeyCodes.SPACE,
        web: Phaser.Input.Keyboard.KeyCodes.E,
      });
      this.input.keyboard.on("keydown-E", () => this.toggleWeb());
      this.input.keyboard.on("keydown-SPACE", () => this.jump());
      this.input.on("pointerdown", (pointer) => {
        if (pointer.leftButtonDown()) this.toggleWeb(pointer.worldX, pointer.worldY);
      });

      this.ropeGraphics = this.add.graphics().setDepth(8);
      this.matter.world.on("collisionstart", (event) => this.onCollision(event));
      this.input.setDefaultCursor("crosshair");
      this.refreshHud();
      this.scene.pause();
    }

    drawCity() {
      const roofs = [
        [130, 520, 330], [490, 465, 180], [790, 405, 190], [1110, 485, 230],
        [1450, 430, 210], [1770, 370, 180], [2070, 470, 250], [2430, 410, 200],
        [2750, 350, 190], [3070, 455, 240], [3430, 390, 210], [3780, 470, 310],
      ];
      const details = this.add.graphics();
      roofs.forEach(([x, y, width], index) => {
        this.matter.add.rectangle(x, y + 24, width, 48, { isStatic: true, label: "roof" });
        details.fillStyle(0x1b3038, 1).fillRect(x - width / 2, y, width, 56);
        details.fillStyle(index % 2 ? 0xf4a84e : 0x73d8ce, 1).fillRect(x - width / 2, y, width, 4);
        details.fillStyle(0x34505a, 1).fillRect(x - width / 2 + 12, y + 12, 38, 3);
      });
    }

    createAnchors() {
      this.anchorGraphics = this.add.graphics().setDepth(3);
      for (let x = 270, index = 0; x < this.worldWidth - 100; x += 185, index += 1) {
        const y = 75 + ((index * 47) % 105);
        const anchor = { x, y };
        this.anchors.push(anchor);
        this.anchorGraphics.lineStyle(1, 0x73d8ce, 0.16).lineBetween(x, 0, x, anchor.y);
        this.anchorGraphics.fillStyle(0x73d8ce, 0.16).fillCircle(x, anchor.y, 12);
        this.anchorGraphics.fillStyle(0xf2eee4, 0.75).fillCircle(x, anchor.y, 3);
      }
    }

    createPickups() {
      const points = [
        [330, 355], [575, 345], [700, 275], [930, 290], [1110, 355], [1310, 330],
        [1510, 295], [1690, 250], [1890, 305], [2110, 345], [2290, 285], [2490, 290],
        [2690, 250], [2890, 300], [3100, 335], [3300, 280], [3510, 275], [3710, 335],
      ];
      points.forEach(([x, y]) => {
        const token = this.add.circle(x, y, 10, 0xf4a84e).setStrokeStyle(3, 0xffe0a9, 0.85).setDepth(4);
        this.tweens.add({ targets: token, scale: 1.28, alpha: 0.68, duration: 540, yoyo: true, repeat: -1 });
        this.pickups.push(token);
      });
    }

    createDrones() {
      [670, 1260, 1940, 2580, 3250, 3660].forEach((x, index) => {
        const drone = this.add.container(x, 215 + (index % 3) * 37).setDepth(5);
        const body = this.add.ellipse(0, 0, 38, 19, 0x243b43).setStrokeStyle(2, 0xf26b58);
        const eye = this.add.circle(0, 0, 4, 0xf26b58);
        const leftRotor = this.add.line(-22, -12, -8, 0, 8, 0, 0x73d8ce, 0.8);
        const rightRotor = this.add.line(22, -12, -8, 0, 8, 0, 0x73d8ce, 0.8);
        drone.add([body, eye, leftRotor, rightRotor]);
        drone.baseX = x;
        drone.range = 72 + (index % 2) * 25;
        drone.phase = index * 1.8;
        this.drones.push(drone);
      });
    }

    begin() {
      this.started = true;
      this.scene.resume();
      overlay.classList.add("is-hidden");
      stateValue.textContent = "PATRUL";
    }

    jump() {
      if (!this.started || !this.canJump) return;
      this.hero.setVelocityY(-10.5);
      this.canJump = false;
    }

    toggleWeb(pointerX, pointerY) {
      if (!this.started) return;
      if (this.rope) {
        this.matter.world.removeConstraint(this.rope);
        this.rope = null;
        this.ropeAnchor = null;
        stateValue.textContent = "PATRUL";
        return;
      }

      const targetX = pointerX ?? this.hero.x + 220;
      const targetY = pointerY ?? this.hero.y - 220;
      const nearest = this.anchors
        .map((anchor) => ({ anchor, distance: Phaser.Math.Distance.Between(targetX, targetY, anchor.x, anchor.y) }))
        .filter(({ anchor, distance }) => anchor.x > this.hero.x - 80 && distance < 540)
        .sort((first, second) => first.distance - second.distance)[0];
      if (!nearest) return;

      const length = Phaser.Math.Distance.Between(this.hero.x, this.hero.y, nearest.anchor.x, nearest.anchor.y);
      if (length > 610) return;
      this.ropeAnchor = nearest.anchor;
      this.rope = this.matter.add.worldConstraint(
        this.hero.body,
        length,
        0.82,
        {
          pointA: { x: nearest.anchor.x, y: nearest.anchor.y },
          pointB: { x: 0, y: -13 },
          damping: 0.04,
          label: "web-line",
          render: { visible: false },
        },
      );
      stateValue.textContent = "TO‘R ULANDI";
    }

    onCollision(event) {
      for (const pair of event.pairs) {
        if (pair.bodyA === this.hero.body && pair.bodyB.label === "roof") this.canJump = true;
        if (pair.bodyB === this.hero.body && pair.bodyA.label === "roof") this.canJump = true;
      }
    }

    refreshHud() {
      scoreValue.textContent = String(this.score).padStart(2, "0");
      distanceValue.textContent = String(Math.max(0, Math.floor(this.hero.x / 10))).padStart(3, "0");
    }

    finish(won) {
      if (!this.started) return;
      this.started = false;
      this.finished = true;
      if (this.rope) this.matter.world.removeConstraint(this.rope);
      this.rope = null;
      this.scene.pause();
      overlay.classList.remove("is-hidden");
      title.textContent = won ? "Patrul bajarildi." : "Patrul yakunlandi.";
      copy.textContent = won
        ? `Ajoyib. ${this.score} ta energiya belgisini yig‘dingiz.`
        : `Siz ${this.score} ta energiya belgisini yig‘dingiz. Yana bir urinish qilasizmi?`;
      startButton.textContent = "Qayta boshlash";
      stateValue.textContent = won ? "BAJARILDI" : "YAKUNLANDI";
    }

    update(time) {
      if (!this.started) return;
      const direction = Number(this.controls.right.isDown || this.controls.rightArrow.isDown)
        - Number(this.controls.left.isDown || this.controls.leftArrow.isDown) + this.mobileDirection;
      if (direction) {
        Phaser.Physics.Matter.Matter.Body.applyForce(this.hero.body, this.hero.body.position, { x: direction * 0.0015, y: 0 });
      }

      this.drones.forEach((drone) => {
        drone.x = drone.baseX + Math.sin(time / 580 + drone.phase) * drone.range;
      });
      this.ropeGraphics.clear();
      if (this.ropeAnchor) {
        this.ropeGraphics.lineStyle(2, 0xf2eee4, 0.86);
        this.ropeGraphics.lineBetween(this.hero.x, this.hero.y - 13, this.ropeAnchor.x, this.ropeAnchor.y);
      }

      const playerPoint = new Phaser.Math.Vector2(this.hero.x, this.hero.y);
      this.pickups = this.pickups.filter((token) => {
        if (!token.active) return false;
        if (Phaser.Math.Distance.BetweenPoints(playerPoint, token) < 36) {
          token.destroy();
          this.score += 1;
          this.refreshHud();
          if (this.score >= 12) this.finish(true);
          return false;
        }
        return true;
      });
      if (this.drones.some((drone) => Phaser.Math.Distance.Between(this.hero.x, this.hero.y, drone.x, drone.y) < 34)) {
        this.finish(false);
      }
      this.refreshHud();
      if (this.hero.y > 640 || this.hero.x > this.worldWidth - 70) this.finish(false);
    }
  }

  const game = new Phaser.Game({
    type: Phaser.AUTO,
    parent: "game-mount",
    width: 1000,
    height: 560,
    backgroundColor: "#172d38",
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
    physics: { default: "matter", matter: { gravity: { y: 0.95 }, enableSleeping: true, debug: false } },
    render: { antialias: true, pixelArt: false },
    scene: [NightPatrol],
  });

  startButton.addEventListener("click", () => {
    const scene = game.scene.getScene("NightPatrol");
    if (scene.finished) scene.scene.restart();
    else scene.begin();
  });

  document.querySelectorAll("[data-control]").forEach((button) => {
    const action = button.dataset.control;
    button.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      const scene = game.scene.getScene("NightPatrol");
      if (!scene) return;
      if (action === "web") scene.toggleWeb();
      if (action === "jump") scene.jump();
      if (action === "left") scene.mobileDirection = -1;
      if (action === "right") scene.mobileDirection = 1;
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach((eventName) => {
      button.addEventListener(eventName, () => {
        const scene = game.scene.getScene("NightPatrol");
        if (action === "left" || action === "right") scene.mobileDirection = 0;
      });
    });
  });
})();