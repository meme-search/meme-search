/**
 * Shared constants for the Docker E2E workflow tests.
 */

// Mirrors the ImageCore status enum (app/models/image_core.rb); tests read the raw integer from the database.
export const STATUS_MAP = {
  not_started: 0,
  in_queue: 1,
  processing: 2,
  done: 3,
  removing: 4,
  failed: 5,
} as const;

export type ImageStatus = keyof typeof STATUS_MAP;

export const DEFAULT_TIMEOUTS = {
  description_generation: 60000,
} as const;

// The vector search test queries "cat wearing sunglasses"; the cat text must rank above the dog text for it.
export const TEST_DESCRIPTIONS = {
  cat: 'A cat wearing sunglasses sits on a sofa. The text says all the fucks.',
  dog: 'A dog runs across a green park chasing a red ball.',
} as const;
