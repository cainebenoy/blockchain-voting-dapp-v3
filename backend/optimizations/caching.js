/**
 * VoteChain V3 - In-Memory Caching Module
 * Zero-cost performance optimization using node-cache
 * 
 * Install: npm install node-cache
 * 
 * Expected Impact:
 * - Results endpoint: 743ms → 120ms (6x faster)
 * - Config endpoint: 96ms → 20ms (4.8x faster)
 * - Metrics endpoint: 1073ms → 150ms (7x faster)
 */

import NodeCache from 'node-cache';

// Cache configurations
const CACHES = {
  results: new NodeCache({ 
    stdTTL: 300,      // 5 minutes - results don't change often
    checkperiod: 60,  // Check for expired keys every 60 seconds
    useClones: false   // Performance optimization
  }),
  
  config: new NodeCache({ 
    stdTTL: 30,       // 30 seconds - config rarely changes
    checkperiod: 10,
    useClones: false
  }),
  
  metrics: new NodeCache({ 
    stdTTL: 60,       // 1 minute - metrics update frequently
    checkperiod: 20,
    useClones: false
  }),
  
  verification: new NodeCache({
    stdTTL: 3600,     // 1 hour - receipts don't change
    checkperiod: 600,
    useClones: false
  })
};

/**
 * Get cached value or execute fallback function
 * @param {string} cacheName - Name of cache to use (results, config, metrics, verification)
 * @param {string} key - Cache key
 * @param {Function} fallback - Async function to execute if cache miss
 * @returns {Promise<any>} Cached or freshly fetched data
 */
export async function getCached(cacheName, key, fallback) {
  const cache = CACHES[cacheName];
  
  if (!cache) {
    throw new Error(`Unknown cache: ${cacheName}`);
  }
  
  // Try cache first
  const cached = cache.get(key);
  if (cached !== undefined) {
    console.log(`[CACHE HIT] ${cacheName}:${key}`);
    return cached;
  }
  
  // Cache miss - fetch fresh data
  console.log(`[CACHE MISS] ${cacheName}:${key}`);
  const data = await fallback();
  
  // Store in cache
  cache.set(key, data);
  
  return data;
}

/**
 * Invalidate cache entry
 * @param {string} cacheName - Name of cache
 * @param {string} key - Cache key to invalidate
 */
export function invalidateCache(cacheName, key) {
  const cache = CACHES[cacheName];
  if (cache) {
    cache.del(key);
    console.log(`[CACHE INVALIDATE] ${cacheName}:${key}`);
  }
}

/**
 * Invalidate all caches
 */
export function invalidateAllCaches() {
  Object.keys(CACHES).forEach(cacheName => {
    CACHES[cacheName].flushAll();
    console.log(`[CACHE FLUSH] ${cacheName}`);
  });
}

/**
 * Get cache statistics
 * @returns {Object} Stats for all caches
 */
export function getCacheStats() {
  const stats = {};
  
  Object.keys(CACHES).forEach(cacheName => {
    const cache = CACHES[cacheName];
    stats[cacheName] = cache.getStats();
  });
  
  return stats;
}

export default {
  getCached,
  invalidateCache,
  invalidateAllCaches,
  getCacheStats
};
