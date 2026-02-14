/**
 * VoteChain V3 - Simple Vote Queue
 * Zero-cost optimization to smooth blockchain submissions
 * 
 * Expected Impact:
 * - Prevents blockchain congestion
 * - Smoother transaction processing
 * - Better rate limiting compliance
 * 
 * How it works:
 * - Votes are queued in memory
 * - Processed one at a time every 15 seconds
 * - Prevents transaction nonce conflicts
 */

import { supabase } from '../services/db.js';

class SimpleVoteQueue {
  constructor(contract, processInterval = 15000) {
    this.contract = contract;
    this.queue = [];
    this.processInterval = processInterval; // 15 seconds
    this.processing = false;
    this.stats = {
      queued: 0,
      processed: 0,
      failed: 0,
      avgProcessTime: 0
    };

    // Start processing timer
    this.startProcessing();
  }

  /**
   * Add vote to queue
   * @param {number} candidateId - Candidate to vote for
   * @param {string} voterHash - Hashed voter identifier
   * @param {string} kioskNonce - Unique nonce (Bytes32 or Hex) for Contract
   * @param {string} originalNonce - Original nonce string for DB lookup
   * @returns {Promise} Resolves when vote is queued (NOT when processed)
   */
  async queueVote(candidateId, voterHash, kioskNonce, originalNonce) {
    return new Promise((resolve, reject) => {
      this.queue.push({
        candidateId,
        voterHash,
        kioskNonce,
        originalNonce: originalNonce || kioskNonce, // Fallback if not provided
        timestamp: Date.now(),
        resolve,
        reject
      });

      this.stats.queued++;
      console.log(`[VOTE QUEUE] Added vote for ${voterHash}. Queue size: ${this.queue.length}`);

      // Immediately resolve (vote is queued, will be processed soon)
      resolve({
        success: true,
        queued: true,
        queuePosition: this.queue.length,
        estimatedProcessTime: this.queue.length * (this.processInterval / 1000) // seconds
      });
    });
  }

  /**
   * Start processing queue at regular intervals
   */
  startProcessing() {
    setInterval(async () => {
      if (!this.processing && this.queue.length > 0) {
        await this.processNext();
      }
    }, this.processInterval);

    console.log(`[VOTE QUEUE] Started processing (interval: ${this.processInterval}ms)`);
  }

  /**
   * Process next vote in queue
   */
  async processNext() {
    if (this.processing || this.queue.length === 0) {
      return;
    }

    this.processing = true;
    const vote = this.queue.shift();
    const startTime = Date.now();

    try {
      console.log(`[VOTE QUEUE] Processing vote for hash ${vote.voterHash} (${this.queue.length} remaining)`);

      // Submit to blockchain
      const tx = await this.contract.vote(vote.candidateId, vote.voterHash, vote.kioskNonce);
      const receipt = await tx.wait(1);

      // RECONCILIATION: Update receipt table with real TX hash
      try {
        // Use originalNonce if available, otherwise fallback to kioskNonce
        const lookupNonce = vote.originalNonce || vote.kioskNonce;

        await supabase
          .from('receipts')
          .update({
            tx_hash: receipt.hash
            // is_confirmed removed
          })
          .eq('tx_hash', `PENDING_${lookupNonce}`);
      } catch (dbErr) {
        console.error(`[VOTE QUEUE] ⚠️ Reconcile failed for ${vote.voterHash}:`, dbErr);
      }

      const processTime = Date.now() - startTime;
      this.stats.processed++;
      this.updateAvgProcessTime(processTime);

      console.log(`[VOTE QUEUE] ✅ Vote processed in ${processTime}ms. TX: ${receipt.hash}`);

    } catch (error) {
      this.stats.failed++;
      console.error(`[VOTE QUEUE] ❌ Failed to process vote for hash ${vote.voterHash}:`, error.message);

      // Re-queue failed votes (max 3 retries)
      if (!vote.retries || vote.retries < 3) {
        vote.retries = (vote.retries || 0) + 1;
        this.queue.push(vote);
        console.log(`[VOTE QUEUE] Re-queued vote (retry ${vote.retries}/3)`);
      }
    } finally {
      this.processing = false;
    }
  }

  /**
   * Update average processing time (exponential moving average)
   */
  updateAvgProcessTime(newTime) {
    if (this.stats.avgProcessTime === 0) {
      this.stats.avgProcessTime = newTime;
    } else {
      // EMA with alpha = 0.2
      this.stats.avgProcessTime = (0.2 * newTime) + (0.8 * this.stats.avgProcessTime);
    }
  }

  /**
   * Get queue statistics
   */
  getStats() {
    return {
      ...this.stats,
      queueLength: this.queue.length,
      processing: this.processing,
      successRate: this.stats.processed / (this.stats.processed + this.stats.failed) * 100,
      estimatedWaitTime: this.queue.length * (this.processInterval / 1000)
    };
  }

  /**
   * Get queue status
   */
  getStatus() {
    return {
      queueLength: this.queue.length,
      processing: this.processing,
      nextProcessIn: this.processInterval / 1000, // seconds
      stats: this.getStats()
    };
  }
}

export default SimpleVoteQueue;
