export class Player {
  constructor(world) {
    this.world = world;
    this.x = 3.5 * 48;
    this.y = 5.5 * 48;
    this.speed = 190;
    this.input = { x: 0, y: 0 };
    this.keys = new Set();
    this.joystick = { active: false, x: 0, y: 0 };
    this.bindKeyboard();
    this.bindJoystick();
  }

  bindKeyboard() {
    window.addEventListener("keydown", (event) => {
      if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "w", "a", "s", "d", "W", "A", "S", "D"].includes(event.key)) {
        event.preventDefault();
        this.keys.add(event.key.toLowerCase());
      }
    });

    window.addEventListener("keyup", (event) => {
      this.keys.delete(event.key.toLowerCase());
    });
  }

  bindJoystick() {
    const pad = document.querySelector("#joystick");
    const knob = document.querySelector("#joystickKnob");
    if (!pad || !knob) return;

    const reset = () => {
      this.joystick = { active: false, x: 0, y: 0 };
      knob.style.transform = "translate(-50%, -50%)";
    };

    const move = (clientX, clientY) => {
      const rect = pad.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const dx = clientX - centerX;
      const dy = clientY - centerY;
      const distance = Math.min(Math.hypot(dx, dy), rect.width * 0.32);
      const angle = Math.atan2(dy, dx);
      const x = Math.cos(angle) * distance;
      const y = Math.sin(angle) * distance;
      this.joystick = { active: true, x: x / (rect.width * 0.32), y: y / (rect.height * 0.32) };
      knob.style.transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`;
    };

    pad.addEventListener("pointerdown", (event) => {
      pad.setPointerCapture(event.pointerId);
      move(event.clientX, event.clientY);
    });
    pad.addEventListener("pointermove", (event) => {
      if (this.joystick.active) move(event.clientX, event.clientY);
    });
    pad.addEventListener("pointerup", reset);
    pad.addEventListener("pointercancel", reset);
  }

  update(delta) {
    const input = this.readInput();
    if (!input.x && !input.y) return false;

    const length = Math.hypot(input.x, input.y) || 1;
    const nx = input.x / length;
    const ny = input.y / length;
    const step = this.speed * delta;
    let moved = false;

    const nextX = this.x + nx * step;
    if (this.canStand(nextX, this.y)) {
      this.x = nextX;
      moved = true;
    }

    const nextY = this.y + ny * step;
    if (this.canStand(this.x, nextY)) {
      this.y = nextY;
      moved = true;
    }

    return moved;
  }

  readInput() {
    if (this.joystick.active) return { x: this.joystick.x, y: this.joystick.y };

    const left = this.keys.has("arrowleft") || this.keys.has("a");
    const right = this.keys.has("arrowright") || this.keys.has("d");
    const up = this.keys.has("arrowup") || this.keys.has("w");
    const down = this.keys.has("arrowdown") || this.keys.has("s");
    return {
      x: Number(right) - Number(left),
      y: Number(down) - Number(up)
    };
  }

  canStand(x, y) {
    const radius = 12;
    return (
      this.world.isWalkablePixel(x - radius, y) &&
      this.world.isWalkablePixel(x + radius, y) &&
      this.world.isWalkablePixel(x, y - radius) &&
      this.world.isWalkablePixel(x, y + radius)
    );
  }
}
