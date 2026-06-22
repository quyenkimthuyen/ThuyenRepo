/**
 * Gzip compression/decompression using native CompressionStream API.
 * @module data/Compression
 */

/**
 * Compress a string or Uint8Array to gzip bytes.
 * @param {string|Uint8Array} input
 * @returns {Promise<Uint8Array>}
 */
export async function compress(input) {
  const data = typeof input === 'string'
    ? new TextEncoder().encode(input)
    : input;

  const stream = new Blob([data]).stream().pipeThrough(new CompressionStream('gzip'));
  const buffer = await new Response(stream).arrayBuffer();
  return new Uint8Array(buffer);
}

/**
 * Decompress gzip bytes to a UTF-8 string.
 * @param {Uint8Array} data
 * @returns {Promise<string>}
 */
export async function decompress(data) {
  const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream('gzip'));
  const buffer = await new Response(stream).arrayBuffer();
  return new TextDecoder().decode(buffer);
}

/**
 * Check if the browser supports native compression.
 * @returns {boolean}
 */
export function isCompressionSupported() {
  return typeof CompressionStream !== 'undefined';
}
