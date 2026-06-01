import { rarityColors } from "./wordmon.js";

export const TILE_SIZE = 48;
const REVEAL_RADIUS = 4;

export const worlds = [
  "Home Village",
  "Animal Forest",
  "Food Kingdom",
  "School City",
  "Nature Valley",
  "Transportation Island",
  "Ocean World",
  "Space Academy",
  "Magic Kingdom",
  "Dragon Castle"
];

export class World {
  constructor(wordmons, state) {
    this.width = 38;
    this.height = 26;
    this.wordmons = wordmons;
    this.state = state;
    this.treasures = [
      { id: "village-fountain", x: 7, y: 7, opened: false, reward: { xp: 15, coins: 10 } },
      { id: "hidden-garden", x: 18, y: 16, opened: false, reward: { xp: 25, coins: 12, stars: 1 } },
      { id: "river-bridge", x: 31, y: 20, opened: false, reward: { xp: 20, coins: 20 } }
    ];
    this.tiles = this.createTiles();
    this.applySavedState();
  }

  createTiles() {
    const tiles = [];
    for (let y = 0; y < this.height; y += 1) {
      const row = [];
      for (let x = 0; x < this.width; x += 1) {
        let type = "grass";
        if (x === 0 || y === 0 || x === this.width - 1 || y === this.height - 1) type = "trees";
        if ((x > 2 && x < 12 && y === 9) || (x > 22 && y === 10 && y < 12)) type = "path";
        if ((x > 4 && x < 34 && y === 20) || (y > 4 && y < 22 && x === 19)) type = "path";
        if (x > 29 && y < 8) type = "flowers";
        if (x > 1 && x < 6 && y > 18 && y < 24) type = "water";
        if ((x === 12 && y > 4 && y < 16) || (x > 24 && x < 30 && y === 15)) type = "rocks";
        row.push(type);
      }
      tiles.push(row);
    }

    this.carveHiddenPaths(tiles);
    return tiles;
  }

  carveHiddenPaths(tiles) {
    for (let y = 12; y <= 15; y += 1) tiles[y][12] = "secret";
    for (let x = 24; x < 30; x += 1) tiles[15][x] = "secret";
  }

  applySavedState() {
    const captured = new Set(this.state.captured);
    const opened = new Set(this.state.treasureOpened);
    this.wordmons.forEach((wordmon) => {
      wordmon.captured = captured.has(wordmon.id);
    });
    this.treasures.forEach((treasure) => {
      treasure.opened = opened.has(treasure.id);
    });
  }

  revealAround(player) {
    const px = Math.floor(player.x / TILE_SIZE);
    const py = Math.floor(player.y / TILE_SIZE);
    const explored = new Set(this.state.explored);

    for (let y = py - REVEAL_RADIUS; y <= py + REVEAL_RADIUS; y += 1) {
      for (let x = px - REVEAL_RADIUS; x <= px + REVEAL_RADIUS; x += 1) {
        if (!this.inBounds(x, y)) continue;
        const distance = Math.hypot(px - x, py - y);
        if (distance <= REVEAL_RADIUS) explored.add(`${x},${y}`);
      }
    }

    this.state.explored = [...explored];
  }

  isWalkablePixel(x, y) {
    const tileX = Math.floor(x / TILE_SIZE);
    const tileY = Math.floor(y / TILE_SIZE);
    if (!this.inBounds(tileX, tileY)) return false;
    return !["trees", "water", "rocks"].includes(this.tiles[tileY][tileX]);
  }

  inBounds(x, y) {
    return x >= 0 && y >= 0 && x < this.width && y < this.height;
  }

  getNearbyWordmon(player) {
    return this.wordmons.find((wordmon) => {
      if (wordmon.captured || !wordmon.visible) return false;
      const wx = wordmon.x * TILE_SIZE + TILE_SIZE / 2;
      const wy = wordmon.y * TILE_SIZE + TILE_SIZE / 2;
      return Math.hypot(player.x - wx, player.y - wy) < 48;
    });
  }

  getNearbyTreasure(player) {
    return this.treasures.find((treasure) => {
      if (treasure.opened) return false;
      const tx = treasure.x * TILE_SIZE + TILE_SIZE / 2;
      const ty = treasure.y * TILE_SIZE + TILE_SIZE / 2;
      return Math.hypot(player.x - tx, player.y - ty) < 46;
    });
  }

  getCompletion() {
    const totalTiles = this.width * this.height;
    return Math.round((this.state.explored.length / totalTiles) * 100);
  }

  draw(ctx, canvas, player) {
    const camera = this.getCamera(canvas, player);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(-camera.x, -camera.y);
    this.drawTiles(ctx);
    this.drawTreasures(ctx);
    this.drawWordmons(ctx);
    this.drawPlayer(ctx, player);
    this.drawFog(ctx);
    ctx.restore();
  }

  getCamera(canvas, player) {
    const maxX = this.width * TILE_SIZE - canvas.width;
    const maxY = this.height * TILE_SIZE - canvas.height;
    return {
      x: clamp(player.x - canvas.width / 2, 0, Math.max(0, maxX)),
      y: clamp(player.y - canvas.height / 2, 0, Math.max(0, maxY))
    };
  }

  drawTiles(ctx) {
    for (let y = 0; y < this.height; y += 1) {
      for (let x = 0; x < this.width; x += 1) {
        const tile = this.tiles[y][x];
        ctx.fillStyle = tileColor(tile);
        ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        if (tile === "flowers") this.drawIcon(ctx, "✿", x, y, "#ff78b7");
        if (tile === "trees") this.drawIcon(ctx, "♣", x, y, "#146b36");
        if (tile === "water") this.drawIcon(ctx, "≈", x, y, "#ffffff");
      }
    }
  }

  drawTreasures(ctx) {
    this.treasures.forEach((treasure) => {
      if (!this.isExplored(treasure.x, treasure.y)) return;
      this.drawBubble(ctx, treasure.x, treasure.y, treasure.opened ? "✓" : "🎁", treasure.opened ? "#d7edf1" : "#ffe08a");
    });
  }

  drawWordmons(ctx) {
    this.wordmons.forEach((wordmon) => {
      if (wordmon.captured || !this.isExplored(wordmon.x, wordmon.y)) return;
      const pulse = Math.sin(performance.now() / 380 + wordmon.bob) * 4;
      this.drawBubble(ctx, wordmon.x, wordmon.y, wordmon.image, rarityColors[wordmon.rarity] || "#fff", pulse);
    });
  }

  drawPlayer(ctx, player) {
    const x = player.x;
    const y = player.y;
    ctx.fillStyle = "#1f6fd1";
    ctx.beginPath();
    ctx.arc(x, y - 8, 15, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ffce7a";
    ctx.beginPath();
    ctx.arc(x, y - 15, 9, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.fillRect(x - 13, y - 1, 26, 18);
    ctx.fillStyle = "#2e4a72";
    ctx.fillRect(x - 10, y + 16, 7, 12);
    ctx.fillRect(x + 3, y + 16, 7, 12);
  }

  drawFog(ctx) {
    const explored = new Set(this.state.explored);
    ctx.fillStyle = "rgba(8, 25, 45, 0.78)";
    for (let y = 0; y < this.height; y += 1) {
      for (let x = 0; x < this.width; x += 1) {
        if (!explored.has(`${x},${y}`)) {
          ctx.fillRect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE);
        }
      }
    }
  }

  drawMiniMap(ctx, canvas, player) {
    const scaleX = canvas.width / this.width;
    const scaleY = canvas.height / this.height;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < this.height; y += 1) {
      for (let x = 0; x < this.width; x += 1) {
        ctx.fillStyle = this.isExplored(x, y) ? tileColor(this.tiles[y][x]) : "#6c7b91";
        ctx.fillRect(x * scaleX, y * scaleY, Math.ceil(scaleX), Math.ceil(scaleY));
      }
    }

    this.treasures.forEach((treasure) => {
      if (!this.isExplored(treasure.x, treasure.y)) return;
      ctx.fillStyle = treasure.opened ? "#ffffff" : "#ffb02e";
      ctx.fillRect(treasure.x * scaleX, treasure.y * scaleY, scaleX * 1.4, scaleY * 1.4);
    });

    this.wordmons.forEach((wordmon) => {
      if (wordmon.captured || !this.isExplored(wordmon.x, wordmon.y)) return;
      ctx.fillStyle = rarityColors[wordmon.rarity] || "#fff";
      ctx.beginPath();
      ctx.arc(wordmon.x * scaleX + scaleX / 2, wordmon.y * scaleY + scaleY / 2, 3, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.fillStyle = "#1d3150";
    ctx.beginPath();
    ctx.arc((player.x / TILE_SIZE) * scaleX, (player.y / TILE_SIZE) * scaleY, 4.5, 0, Math.PI * 2);
    ctx.fill();
  }

  drawBubble(ctx, tileX, tileY, content, color, offset = 0) {
    const x = tileX * TILE_SIZE + TILE_SIZE / 2;
    const y = tileY * TILE_SIZE + TILE_SIZE / 2 + offset;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, 20, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#fff";
    ctx.beginPath();
    ctx.arc(x - 6, y - 7, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "24px Nunito, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#1d3150";
    ctx.fillText(content, x, y + 1);
  }

  drawIcon(ctx, icon, x, y, color) {
    ctx.font = "22px Nunito, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = color;
    ctx.fillText(icon, x * TILE_SIZE + TILE_SIZE / 2, y * TILE_SIZE + TILE_SIZE / 2);
  }

  isExplored(x, y) {
    return this.state.explored.includes(`${x},${y}`);
  }
}

function tileColor(tile) {
  return {
    grass: "#80dc6b",
    path: "#eecb86",
    secret: "#a7e37e",
    trees: "#389c55",
    flowers: "#a5ec8d",
    water: "#53b9eb",
    rocks: "#9aa7b7"
  }[tile] || "#80dc6b";
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
