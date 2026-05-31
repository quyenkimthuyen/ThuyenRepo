# Image Assets

To ensure high-performance, responsive layout adjustments, and zero loading times, all sprites (battleships, normal submarines, giant boss submarines, depth charge bombs, rockets, crates, and particle systems) are drawn dynamically on the HTML5 Canvas using vector paths and mathematical calculations in `game.js`.

If you wish to replace dynamic graphics with static images, you can place your PNG/SVG files in this directory and modify the draw functions in `game.js` to draw static image elements.
